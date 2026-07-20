"""审核接口。"""

from flask import Blueprint, g, request

from app.constants import TASK_STATUS_REVIEW
from app.extensions import db
from app.models.task import ClassificationTask
from app.models.user import User
from app.services.review_service import ReviewService
from app.utils.auth_decorator import admin_required
from app.utils.response import fail, success

reviews_bp = Blueprint("reviews", __name__)
review_service = ReviewService()


def _parse_csv_arg(name: str) -> list[str]:
    """解析逗号分隔的查询参数。"""
    raw = request.args.get(name, "").strip()
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def _paginate_review_list():
    """待审核任务分页列表（筛选/分页与操作员列表对齐）。"""
    page = max(int(request.args.get("page", 1)), 1)
    page_size = min(max(int(request.args.get("page_size", 20)), 1), 200)

    query = ClassificationTask.query.filter_by(status=TASK_STATUS_REVIEW)

    platform_list = _parse_csv_arg("platform")
    keyword = request.args.get("keyword", "").strip()
    assignee_id = request.args.get("assignee_id", "").strip()

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
    if assignee_id.isdigit():
        query = query.filter_by(assignee_id=int(assignee_id))

    total = query.count()
    items = (
        query.order_by(ClassificationTask.submitted_at.desc())
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


@reviews_bp.get("/pending")
@admin_required
def list_pending_reviews():
    """待审核任务列表。"""
    return success(_paginate_review_list())


@reviews_bp.post("/approve")
@admin_required
def approve_reviews():
    """批量/单条审核通过。"""
    data = request.get_json(silent=True) or {}
    task_ids = data.get("task_ids") or []
    if not task_ids:
        return fail("请选择要通过的任务")

    result = review_service.approve_tasks(task_ids, g.current_user.id)
    msg = f"已通过 {len(result['success_ids'])} 条"
    if result["skipped"]:
        msg += f"，跳过 {len(result['skipped'])} 条"
    return success(result, message=msg)


@reviews_bp.post("/reject")
@admin_required
def reject_reviews():
    """批量/单条驳回。"""
    data = request.get_json(silent=True) or {}
    task_ids = data.get("task_ids") or []
    reason = data.get("reason", "")
    if not task_ids:
        return fail("请选择要驳回的任务")

    result = review_service.reject_tasks(task_ids, g.current_user.id, reason=reason)
    msg = f"已驳回 {len(result['success_ids'])} 条"
    if result["skipped"]:
        msg += f"，跳过 {len(result['skipped'])} 条"
    return success(result, message=msg)
