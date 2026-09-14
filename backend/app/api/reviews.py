"""审核接口。"""

from flask import Blueprint, g, request

from app.constants import TASK_STATUS_REVIEW
from app.extensions import db
from app.models.task import ClassificationTask
from app.models.user import User
from app.services.review_service import ReviewService
from app.utils.auth_decorator import admin_required
from app.utils.query_filters import (
    apply_assignee_id_filter,
    apply_batch_id_filter,
    apply_category_filters,
    parse_csv_arg,
)
from app.utils.response import fail, success

reviews_bp = Blueprint("reviews", __name__)
review_service = ReviewService()

_APPROVE_SCOPES = frozenset({"all", "filtered"})


def _filters_from_request_args() -> dict:
    """从 GET 查询参数组装与待审核列表一致的筛选条件。"""
    return {
        "platform": request.args.get("platform", ""),
        "keyword": request.args.get("keyword", "").strip(),
        "assignee_id": request.args.get("assignee_id", "").strip(),
        "batch_id": request.args.get("batch_id", ""),
        "category_large": request.args.get("category_large", ""),
        "category_segment": request.args.get("category_segment", ""),
    }


def _filters_from_body(data: dict) -> dict:
    """从 POST JSON body 的 filters 字段组装筛选条件。"""
    f = data.get("filters") or {}
    assignee_raw = f.get("assignee_id")
    return {
        "platform": f.get("platform") or "",
        "keyword": (f.get("keyword") or "").strip(),
        "assignee_id": (assignee_raw or "").strip() if assignee_raw is not None else "",
        "batch_id": f.get("batch_id") or "",
        "category_large": f.get("category_large") or "",
        "category_segment": f.get("category_segment") or "",
    }


def _build_pending_query(filters: dict | None = None, *, apply_filters: bool = True):
    """待审核任务查询；apply_filters=False 时仅按 status 过滤（全部通过）。"""
    query = ClassificationTask.query.filter_by(status=TASK_STATUS_REVIEW)
    if not apply_filters:
        return query

    filters = filters or {}
    platform_list = parse_csv_arg(filters.get("platform") or "")
    keyword = (filters.get("keyword") or "").strip()
    assignee_id = (filters.get("assignee_id") or "").strip()
    batch_id = filters.get("batch_id") or ""
    category_large = filters.get("category_large") or ""
    category_segment = filters.get("category_segment") or ""

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
    query = apply_assignee_id_filter(query, ClassificationTask, assignee_id)
    query = apply_batch_id_filter(query, ClassificationTask, batch_id)
    query = apply_category_filters(
        query, ClassificationTask, category_large, category_segment
    )
    return query


def _parse_approve_scope(raw: str | None) -> str | None:
    """校验 scope 参数，非法返回 None。"""
    scope = (raw or "").strip()
    if scope not in _APPROVE_SCOPES:
        return None
    return scope


def _batch_no_map(batch_ids: set) -> dict:
    """批次 ID -> 批次号。"""
    from app.models.task import ImportBatch

    ids = [i for i in batch_ids if i]
    if not ids:
        return {}
    return {
        b.id: b.batch_no
        for b in ImportBatch.query.filter(ImportBatch.id.in_(ids)).all()
    }


def _paginate_review_list():
    """待审核任务分页列表（筛选/分页与操作员列表对齐）。"""
    page = max(int(request.args.get("page", 1)), 1)
    page_size = min(max(int(request.args.get("page_size", 20)), 1), 200)

    query = _build_pending_query(_filters_from_request_args())

    total = query.count()
    items = (
        query.order_by(ClassificationTask.submitted_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    users = {u.id: u.username for u in User.query.all()}
    batches = _batch_no_map({item.batch_id for item in items})
    result_items = []
    for item in items:
        data = item.to_dict()
        data["assignee_name"] = users.get(item.assignee_id, "") if item.assignee_id else ""
        data["batch_no"] = batches.get(item.batch_id, "") if item.batch_id else ""
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


@reviews_bp.get("/approve-scope-count")
@admin_required
def approve_scope_count():
    """按范围统计待审核条数（scope=all 忽略筛选）。"""
    scope = _parse_approve_scope(request.args.get("scope"))
    if not scope:
        return fail("scope 参数无效，应为 all 或 filtered", 400)

    filters = _filters_from_request_args()
    query = _build_pending_query(
        filters, apply_filters=(scope == "filtered")
    )
    return success({"count": query.count()})


@reviews_bp.post("/approve-scope")
@admin_required
def approve_scope():
    """按范围批量审核通过。"""
    data = request.get_json(silent=True) or {}
    scope = _parse_approve_scope(data.get("scope"))
    if not scope:
        return fail("scope 参数无效，应为 all 或 filtered", 400)

    filters = _filters_from_body(data)
    query = _build_pending_query(
        filters, apply_filters=(scope == "filtered")
    )
    ids = [row.id for row in query.with_entities(ClassificationTask.id).all()]

    result = review_service.approve_by_scope(
        ids, g.current_user.id, scope=scope, filters=filters
    )
    msg = f"已通过 {result['success_count']} 条"
    if result["skipped_count"]:
        msg += f"，跳过 {result['skipped_count']} 条"
    return success(result, message=msg)


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
