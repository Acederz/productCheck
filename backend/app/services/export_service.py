"""数据导出服务。"""

import json
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook

from app.constants import EXCEL_HEADERS
from app.extensions import db
from app.models.approved import ApprovedProduct
from app.models.task import ClassificationTask
from app.models.user import User

# 导出附加列（任务）
TASK_EXTRA_HEADERS = (
    "状态",
    "操作员",
    "审核人",
    "驳回原因",
    "分配时间",
    "提交时间",
    "审核时间",
    "创建时间",
    "更新时间",
)


class ExportService:
    """Excel 导出。"""

    def __init__(self, export_folder: Path):
        self.export_folder = export_folder
        self.export_folder.mkdir(parents=True, exist_ok=True)

    def _user_map(self) -> dict:
        """用户 ID -> 用户名映射。"""
        return {u.id: u.username for u in User.query.all()}

    def _fmt_time(self, dt) -> str:
        if not dt:
            return ""
        return dt.strftime("%Y-%m-%d %H:%M:%S") if hasattr(dt, "strftime") else str(dt)

    def _task_base_row(self, task: ClassificationTask) -> list:
        """任务 19 列业务字段。"""
        segment = "，".join(task.category_segment or []) if task.category_segment else ""
        desc = ""
        if task.desc_images:
            desc = json.dumps(task.desc_images, ensure_ascii=False)

        return [
            task.row_no or "",
            task.product_id or "",
            task.main_image or "",
            task.product_name or "",
            task.brand or "",
            task.is_operating or "",
            task.category_large or "",
            segment,
            task.category_type or "",
            task.material_main or "",
            task.material_aux or "",
            task.packaging or "",
            task.size or "",
            task.roll_count or "",
            task.total_count or "",
            task.product_attr or "",
            desc,
            task.product_url or "",
            task.platform or "",
        ]

    def _task_extra_row(self, task: ClassificationTask, users: dict) -> list:
        """任务流程附加列。"""
        return [
            task.status or "",
            users.get(task.assignee_id, ""),
            users.get(task.reviewed_by, ""),
            task.reject_reason or "",
            self._fmt_time(task.assigned_at),
            self._fmt_time(task.submitted_at),
            self._fmt_time(task.reviewed_at),
            self._fmt_time(task.created_at),
            self._fmt_time(task.updated_at),
        ]

    def _approved_base_row(self, item: ApprovedProduct) -> list:
        """正式库 19 列。"""
        segment = "，".join(item.category_segment or []) if item.category_segment else ""
        desc = ""
        if item.desc_images:
            desc = json.dumps(item.desc_images, ensure_ascii=False)
        return [
            item.row_no or "",
            item.product_id or "",
            item.main_image or "",
            item.product_name or "",
            item.brand or "",
            item.is_operating or "",
            item.category_large or "",
            segment,
            item.category_type or "",
            item.material_main or "",
            item.material_aux or "",
            item.packaging or "",
            item.size or "",
            item.roll_count or "",
            item.total_count or "",
            item.product_attr or "",
            desc,
            item.product_url or "",
            item.platform or "",
        ]

    def _save_workbook(self, wb: Workbook, prefix: str) -> str:
        """保存工作簿并返回路径。"""
        filename = f"{prefix}_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
        path = self.export_folder / filename
        wb.save(path)
        return str(path)

    def export_tasks(self, query) -> tuple[str, int]:
        """导出任务列表（按筛选条件）。"""
        tasks = query.order_by(ClassificationTask.id.asc()).all()
        users = self._user_map()

        wb = Workbook()
        ws = wb.active
        ws.title = "任务数据"
        ws.append([*EXCEL_HEADERS, *TASK_EXTRA_HEADERS])

        for task in tasks:
            ws.append([*self._task_base_row(task), *self._task_extra_row(task, users)])

        path = self._save_workbook(wb, "tasks_export")
        return path, len(tasks)

    def export_approved(self, query) -> tuple[str, int]:
        """导出正式库数据。"""
        items = query.order_by(ApprovedProduct.id.asc()).all()
        users = self._user_map()
        extra = ("版本号", "审核人", "审核时间", "更新时间")

        wb = Workbook()
        ws = wb.active
        ws.title = "正式数据"
        ws.append([*EXCEL_HEADERS, *extra])

        for item in items:
            ws.append(
                [
                    *self._approved_base_row(item),
                    item.version,
                    users.get(item.approved_by, ""),
                    self._fmt_time(item.approved_at),
                    self._fmt_time(item.updated_at),
                ]
            )

        path = self._save_workbook(wb, "approved_export")
        return path, len(items)

    def filter_tasks(
        self,
        status=None,
        platform=None,
        batch_id=None,
        keyword=None,
        category_large=None,
        category_segment=None,
    ):
        """构建任务导出查询。"""
        from app.utils.query_filters import apply_category_filters

        query = ClassificationTask.query
        if status:
            query = query.filter_by(status=status)
        if platform:
            query = query.filter_by(platform=platform)
        if batch_id:
            query = query.filter_by(batch_id=int(batch_id))
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(
                db.or_(
                    ClassificationTask.product_id.like(like),
                    ClassificationTask.product_name.like(like),
                )
            )
        return apply_category_filters(
            query, ClassificationTask, category_large, category_segment
        )

    def filter_approved(
        self, platform=None, keyword=None, category_large=None, category_segment=None
    ):
        """构建正式库导出查询。"""
        from app.utils.query_filters import apply_category_filters

        query = ApprovedProduct.query
        if platform:
            platforms = [p.strip() for p in str(platform).split(",") if p.strip()]
            if len(platforms) == 1:
                query = query.filter_by(platform=platforms[0])
            elif platforms:
                query = query.filter(ApprovedProduct.platform.in_(platforms))
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(
                db.or_(
                    ApprovedProduct.product_id.like(like),
                    ApprovedProduct.product_name.like(like),
                )
            )
        return apply_category_filters(
            query, ApprovedProduct, category_large, category_segment
        )
