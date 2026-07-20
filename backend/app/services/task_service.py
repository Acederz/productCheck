"""任务分配、填写、暂存、提交服务。"""

from datetime import datetime

from app.constants import (
    READONLY_FIELDS,
    ROLE_ADMIN,
    ROLE_OPERATOR,
    TASK_STATUS_PENDING,
    TASK_STATUS_REJECTED,
    TASK_STATUS_REVIEW,
    TASK_STATUS_UNASSIGNED,
)
from app.extensions import db
from app.models.log import AssignmentLog, FieldChangeLog
from app.models.task import ClassificationTask, TaskDraft
from app.models.user import User
from app.services.operation_log_service import write_operation_log
from app.services.rule_service import RuleService

# 可编辑业务字段
EDITABLE_FIELDS = {
    "is_operating",
    "category_large",
    "category_segment",
    "category_type",
    "material_main",
    "material_aux",
    "packaging",
    "size",
    "roll_count",
    "total_count",
}

# API 字段 -> 中文路径键（规则校验用）
FIELD_TO_PATH_KEY = {
    "category_large": "大类",
    "category_segment": "区隔",
    "category_type": "类别",
    "material_main": "主材质",
    "material_aux": "辅材质",
    "packaging": "包装方式",
    "size": "尺寸",
    "roll_count": "卷数",
    "total_count": "总入数",
}

ASSIGNABLE_STATUSES = (
    TASK_STATUS_UNASSIGNED,
    TASK_STATUS_PENDING,
    TASK_STATUS_REJECTED,
)


class TaskService:
    """任务流程业务逻辑。"""

    def __init__(self):
        self.rule_service = RuleService()

    def _build_path(self, task: ClassificationTask) -> dict:
        """从任务构建规则路径字典。"""
        return {
            "大类": task.category_large,
            "区隔": task.category_segment or [],
            "类别": task.category_type,
            "主材质": task.material_main,
            "辅材质": task.material_aux,
            "包装方式": task.packaging,
            "尺寸": task.size,
            "卷数": task.roll_count,
        }

    def _normalize_multi_value(self, field: str, value):
        """将前端多选值规范为数据库存储格式。"""
        if value is None:
            return None
        if field == "category_segment":
            if isinstance(value, list):
                cleaned = [str(v).strip() for v in value if str(v).strip()]
                return cleaned or None
            text = str(value).strip()
            return [text] if text else None
        if isinstance(value, list):
            cleaned = [str(v).strip() for v in value if str(v).strip()]
            return ",".join(cleaned) if cleaned else None
        return value

    def _apply_editable_fields(self, task: ClassificationTask, data: dict) -> list:
        """应用可编辑字段，返回变更列表 [(field, old, new)]。"""
        changes = []
        multi_fields = {
            "category_large",
            "category_segment",
            "category_type",
            "material_main",
            "material_aux",
            "packaging",
            "size",
            "roll_count",
            "total_count",
        }
        for field in EDITABLE_FIELDS:
            if field not in data:
                continue
            old = getattr(task, field)
            new = data[field]
            if field in multi_fields:
                new = self._normalize_multi_value(field, new)
            if old != new:
                changes.append((field, old, new))
                setattr(task, field, new)
        return changes

    def assign_tasks(self, task_ids: list, assignee_id: int, operator_id: int) -> dict:
        """批量分配任务给操作员。"""
        assignee = User.query.filter_by(id=assignee_id, role=ROLE_OPERATOR, is_active=True).first()
        if not assignee:
            raise ValueError("操作员不存在或已停用")

        tasks = ClassificationTask.query.filter(ClassificationTask.id.in_(task_ids)).all()
        success, skipped = [], []

        for task in tasks:
            if task.status not in ASSIGNABLE_STATUSES:
                skipped.append({"id": task.id, "reason": f"状态「{task.status}」不可分配"})
                continue
            old_assignee = task.assignee_id
            task.assignee_id = assignee_id
            task.assigned_at = datetime.utcnow()
            if task.status == TASK_STATUS_UNASSIGNED:
                task.status = TASK_STATUS_PENDING

            db.session.add(
                AssignmentLog(
                    task_id=task.id,
                    from_user_id=old_assignee,
                    to_user_id=assignee_id,
                    operator_id=operator_id,
                )
            )
            success.append(task.id)

        write_operation_log(
            operator_id,
            "assign_tasks",
            "task",
            None,
            {"task_ids": success, "assignee_id": assignee_id},
        )
        db.session.commit()
        return {"success_ids": success, "skipped": skipped}

    def withdraw_tasks(self, task_ids: list, operator_id: int) -> dict:
        """待审核任务撤回到待处理。"""
        tasks = ClassificationTask.query.filter(ClassificationTask.id.in_(task_ids)).all()
        success, skipped = [], []

        for task in tasks:
            if task.status != TASK_STATUS_REVIEW:
                skipped.append({"id": task.id, "reason": "仅待审核状态可撤回"})
                continue
            task.status = TASK_STATUS_PENDING
            task.submitted_at = None
            success.append(task.id)

        write_operation_log(operator_id, "withdraw_tasks", "task", None, {"task_ids": success})
        db.session.commit()
        return {"success_ids": success, "skipped": skipped}

    def can_edit(self, task: ClassificationTask, user: User) -> bool:
        """判断用户是否可编辑任务分类字段。"""
        if user.role == ROLE_ADMIN:
            return task.status in (
                TASK_STATUS_UNASSIGNED,
                TASK_STATUS_PENDING,
                TASK_STATUS_REJECTED,
            )
        if user.role == ROLE_OPERATOR:
            return (
                task.assignee_id == user.id
                and task.status in (TASK_STATUS_PENDING, TASK_STATUS_REJECTED)
            )
        return False

    def update_task(self, task: ClassificationTask, data: dict, user: User, reason: str = "") -> dict:
        """保存分类字段。"""
        if not self.can_edit(task, user):
            raise ValueError("当前状态不允许编辑")

        changes = self._apply_editable_fields(task, data)
        task.updated_at = datetime.utcnow()

        for field, old, new in changes:
            db.session.add(
                FieldChangeLog(
                    task_id=task.id,
                    field_name=field,
                    old_value=str(old) if old is not None else None,
                    new_value=str(new) if new is not None else None,
                    reason=reason if user.role == ROLE_ADMIN else None,
                    operator_id=user.id,
                )
            )

        db.session.commit()
        return task.to_dict()

    def save_draft(self, task_id: int, assignee_id: int, draft_json: dict) -> dict:
        """服务端暂存草稿。"""
        task = ClassificationTask.query.get(task_id)
        if not task:
            raise ValueError("任务不存在")
        if task.assignee_id != assignee_id:
            raise ValueError("无权暂存该任务")
        if task.status not in (TASK_STATUS_PENDING, TASK_STATUS_REJECTED):
            raise ValueError("当前状态不可暂存")

        draft = TaskDraft.query.filter_by(task_id=task_id, assignee_id=assignee_id).first()
        if not draft:
            draft = TaskDraft(task_id=task_id, assignee_id=assignee_id, draft_json=draft_json)
            db.session.add(draft)
        else:
            draft.draft_json = draft_json
            draft.updated_at = datetime.utcnow()

        db.session.commit()
        return {"task_id": task_id, "updated_at": draft.updated_at.isoformat()}

    def get_task_with_draft(self, task: ClassificationTask, user: User) -> dict:
        """获取任务详情，操作员优先合并草稿。"""
        data = task.to_dict()
        if user.role == ROLE_OPERATOR and task.assignee_id == user.id:
            draft = TaskDraft.query.filter_by(
                task_id=task.id, assignee_id=user.id
            ).first()
            if draft and draft.draft_json:
                data["draft"] = draft.draft_json
        return data

    def _validate_for_submit(self, task: ClassificationTask) -> str | None:
        """提交前校验分类填写。"""
        operating = (task.is_operating or "").strip()
        if operating == "否":
            return None
        if operating != "是":
            return "请先选择「是否经营」"

        required = [
            ("category_large", "大类"),
            ("category_type", "类别"),
        ]
        for field, label in required:
            if not getattr(task, field):
                return f"请填写{label}"

        if not task.category_segment:
            return "请填写区隔"

        return None

    def submit_tasks(self, task_ids: list, user: User) -> dict:
        """批量提交待审核。"""
        tasks = ClassificationTask.query.filter(ClassificationTask.id.in_(task_ids)).all()
        success, skipped = [], []

        for task in tasks:
            if user.role == ROLE_OPERATOR:
                if task.assignee_id != user.id:
                    skipped.append({"id": task.id, "reason": "非本人任务"})
                    continue
            if task.status not in (TASK_STATUS_PENDING, TASK_STATUS_REJECTED):
                skipped.append({"id": task.id, "reason": f"状态「{task.status}」不可提交"})
                continue

            err = self._validate_for_submit(task)
            if err:
                skipped.append({"id": task.id, "reason": err})
                continue

            version = self.rule_service.get_latest_version()
            task.status = TASK_STATUS_REVIEW
            task.submitted_at = datetime.utcnow()
            task.reject_reason = None
            task.rule_snapshot_id = version.id if version else None
            success.append(task.id)

            # 提交后清除草稿
            TaskDraft.query.filter_by(task_id=task.id, assignee_id=task.assignee_id).delete()

        write_operation_log(user.id, "submit_tasks", "task", None, {"task_ids": success})
        db.session.commit()
        return {"success_ids": success, "skipped": skipped}
