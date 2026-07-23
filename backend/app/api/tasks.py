"""任务管理接口。"""

from flask import Blueprint, g, request

from app.constants import ROLE_ADMIN, ROLE_OPERATOR, TASK_STATUS_PENDING, TASK_STATUS_REJECTED
from app.extensions import db
from app.models.task import ClassificationTask, TaskDraft
from app.models.user import User
from app.services.task_service import TaskService
from app.utils.auth_decorator import admin_required, login_required
from app.utils.query_filters import apply_category_filters, parse_csv_arg
from app.utils.response import fail, success

tasks_bp = Blueprint("tasks", __name__)
task_service = TaskService()


def _parse_csv_arg(name: str) -> list[str]:
    """解析逗号分隔的查询参数。"""
    return parse_csv_arg(request.args.get(name, ""))


def _paginate(query):
    """简单分页，附带操作员用户名。"""
    page = max(int(request.args.get("page", 1)), 1)
    page_size = min(max(int(request.args.get("page_size", 20)), 1), 200)
    total = query.count()
    items = (
        query.order_by(ClassificationTask.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    users = {u.id: u.username for u in User.query.all()}
    result_items = []
    for item in items:
        data = item.to_dict()
        data["assignee_name"] = users.get(item.assignee_id, "") if item.assignee_id else ""
        result_items.append(data)
    return {
        "items": result_items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@tasks_bp.get("")
@admin_required
def list_tasks():
    """管理员任务列表（支持筛选）。"""
    query = ClassificationTask.query
    status = request.args.get("status")
    platform = request.args.get("platform")
    batch_id = request.args.get("batch_id")
    keyword = request.args.get("keyword", "").strip()
    category_large = request.args.get("category_large", "")
    category_segment = request.args.get("category_segment", "")

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
    query = apply_category_filters(
        query, ClassificationTask, category_large, category_segment
    )
    return success(_paginate(query))


@tasks_bp.get("/my")
@login_required
def my_tasks():
    """操作员查看分配给自己的任务（合并服务端暂存，支持筛选分页）。"""
    if g.current_user.role != ROLE_OPERATOR:
        return fail("仅操作人员可访问", 403)

    query = ClassificationTask.query.filter(
        ClassificationTask.assignee_id == g.current_user.id,
        ClassificationTask.status.in_([TASK_STATUS_PENDING, TASK_STATUS_REJECTED]),
    )

    status_list = _parse_csv_arg("status")
    platform_list = _parse_csv_arg("platform")
    keyword = request.args.get("keyword", "").strip()
    category_large = request.args.get("category_large", "")
    category_segment = request.args.get("category_segment", "")

    if status_list:
        query = query.filter(ClassificationTask.status.in_(status_list))
    if platform_list:
        query = query.filter(ClassificationTask.platform.in_(platform_list))
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            db.or_(
                ClassificationTask.product_id.like(like),
                ClassificationTask.product_name.like(like),
            )
        )
    query = apply_category_filters(
        query, ClassificationTask, category_large, category_segment
    )
    result = _paginate(query)

    # 合并暂存草稿到列表数据
    task_ids = [item["id"] for item in result["items"]]
    if task_ids:
        drafts = TaskDraft.query.filter(
            TaskDraft.task_id.in_(task_ids),
            TaskDraft.assignee_id == g.current_user.id,
        ).all()
        draft_map = {d.task_id: d.draft_json for d in drafts}
        for item in result["items"]:
            draft = draft_map.get(item["id"])
            if draft:
                for key, val in draft.items():
                    item[key] = val

    return success(result)


@tasks_bp.get("/<int:task_id>")
@login_required
def get_task(task_id: int):
    """任务详情（操作员含草稿）。"""
    task = ClassificationTask.query.get(task_id)
    if not task:
        return fail("任务不存在", 404)

    if g.current_user.role == ROLE_OPERATOR and task.assignee_id != g.current_user.id:
        return fail("无权查看该任务", 403)

    return success(task_service.get_task_with_draft(task, g.current_user))


@tasks_bp.post("/assign")
@admin_required
def assign_tasks():
    """批量分配任务给操作员。"""
    data = request.get_json(silent=True) or {}
    task_ids = data.get("task_ids") or []
    assignee_id = data.get("assignee_id")

    if not task_ids:
        return fail("请选择要分配的任务")
    if not assignee_id:
        return fail("请选择操作员")

    try:
        result = task_service.assign_tasks(task_ids, int(assignee_id), g.current_user.id)
    except ValueError as exc:
        return fail(str(exc))

    msg = f"成功分配 {len(result['success_ids'])} 条"
    if result["skipped"]:
        msg += f"，跳过 {len(result['skipped'])} 条"
    return success(result, message=msg)


@tasks_bp.post("/withdraw")
@admin_required
def withdraw_tasks():
    """待审核撤回为待处理。"""
    data = request.get_json(silent=True) or {}
    task_ids = data.get("task_ids") or []
    if not task_ids:
        return fail("请选择任务")

    result = task_service.withdraw_tasks(task_ids, g.current_user.id)
    return success(result, message=f"已撤回 {len(result['success_ids'])} 条")


@tasks_bp.put("/<int:task_id>")
@login_required
def update_task(task_id: int):
    """保存分类字段。"""
    task = ClassificationTask.query.get(task_id)
    if not task:
        return fail("任务不存在", 404)

    data = request.get_json(silent=True) or {}
    reason = data.pop("reason", "") if g.current_user.role == ROLE_ADMIN else ""

    try:
        result = task_service.update_task(task, data, g.current_user, reason=reason)
    except ValueError as exc:
        return fail(str(exc))

    return success(result, message="保存成功")


@tasks_bp.post("/<int:task_id>/draft")
@login_required
def save_draft(task_id: int):
    """暂存草稿（防刷新丢失）。"""
    data = request.get_json(silent=True) or {}
    draft_json = data.get("draft") or data

    try:
        result = task_service.save_draft(task_id, g.current_user.id, draft_json)
    except ValueError as exc:
        return fail(str(exc))

    return success(result, message="暂存成功")


@tasks_bp.post("/submit")
@login_required
def submit_tasks():
    """单条或批量提交审核。"""
    data = request.get_json(silent=True) or {}
    task_ids = data.get("task_ids") or []
    if not task_ids:
        return fail("请选择要提交的任务")

    result = task_service.submit_tasks(task_ids, g.current_user)
    msg = f"成功提交 {len(result['success_ids'])} 条"
    if result["skipped"]:
        msg += f"，跳过 {len(result['skipped'])} 条"
    return success(result, message=msg)
