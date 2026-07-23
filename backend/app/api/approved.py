"""正式库查询接口。"""

from flask import Blueprint, request

from app.extensions import db
from app.models.approved import ApprovedProduct
from app.models.user import User
from app.utils.auth_decorator import admin_required
from app.utils.query_filters import apply_category_filters, parse_csv_arg
from app.utils.response import success

approved_bp = Blueprint("approved", __name__)


def _parse_csv_arg(name: str) -> list[str]:
    """解析逗号分隔的查询参数。"""
    return parse_csv_arg(request.args.get(name, ""))


def _approved_to_dict(item: ApprovedProduct, users: dict) -> dict:
    """正式库记录转前端列表字典（字段与审核中心对齐）。"""
    return {
        "id": item.id,
        "product_id": item.product_id,
        "row_no": item.row_no,
        "main_image": item.main_image,
        "product_name": item.product_name,
        "brand": item.brand,
        "is_operating": item.is_operating,
        "category_large": item.category_large,
        "category_segment": item.category_segment or [],
        "category_type": item.category_type,
        "material_main": item.material_main,
        "material_aux": item.material_aux,
        "packaging": item.packaging,
        "size": item.size,
        "roll_count": item.roll_count,
        "total_count": item.total_count,
        "product_attr": item.product_attr,
        "desc_images": item.desc_images or [],
        "product_url": item.product_url,
        "platform": item.platform,
        "version": item.version,
        "source_task_id": item.source_task_id,
        "approved_by": item.approved_by,
        "approved_by_name": users.get(item.approved_by, "") if item.approved_by else "",
        "approved_at": item.approved_at.isoformat() if item.approved_at else None,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
    }


@approved_bp.get("")
@admin_required
def list_approved():
    """正式库分页列表（筛选/分页与审核中心对齐）。"""
    page = max(int(request.args.get("page", 1)), 1)
    page_size = min(max(int(request.args.get("page_size", 20)), 1), 200)
    platform_list = _parse_csv_arg("platform")
    keyword = request.args.get("keyword", "").strip()
    category_large = request.args.get("category_large", "")
    category_segment = request.args.get("category_segment", "")

    query = ApprovedProduct.query
    if platform_list:
        query = query.filter(ApprovedProduct.platform.in_(platform_list))
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            db.or_(
                ApprovedProduct.product_id.like(like),
                ApprovedProduct.product_name.like(like),
            )
        )
    query = apply_category_filters(
        query, ApprovedProduct, category_large, category_segment
    )

    total = query.count()
    items = (
        query.order_by(ApprovedProduct.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    users = {u.id: u.username for u in User.query.all()}

    return success(
        {
            "items": [_approved_to_dict(i, users) for i in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )
