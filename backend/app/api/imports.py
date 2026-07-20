"""Excel 导入接口。"""

from pathlib import Path

from flask import Blueprint, current_app, g, request, send_file

from app.extensions import db
from app.models.task import ImportBatch
from app.services.import_service import ImportService
from app.utils.auth_decorator import admin_required
from app.utils.response import fail, success

imports_bp = Blueprint("imports", __name__)


def _batch_to_dict(batch: ImportBatch) -> dict:
    return batch.to_dict()


@imports_bp.get("")
@admin_required
def list_imports():
    """导入批次列表。"""
    page = max(int(request.args.get("page", 1)), 1)
    page_size = min(max(int(request.args.get("page_size", 20)), 1), 100)
    query = ImportBatch.query.order_by(ImportBatch.id.desc())
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return success(
        {
            "items": [_batch_to_dict(b) for b in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@imports_bp.post("")
@admin_required
def upload_import():
    """上传 Excel 导入待分类数据。"""
    if "file" not in request.files:
        return fail("请上传 Excel 文件")

    file_storage = request.files["file"]
    if not file_storage.filename:
        return fail("文件名无效")
    if not file_storage.filename.lower().endswith((".xlsx", ".xls")):
        return fail("仅支持 .xlsx 文件")

    service = ImportService(Path(current_app.config["UPLOAD_FOLDER"]))
    try:
        batch = service.import_excel(file_storage, g.current_user.id)
    except ValueError as exc:
        return fail(str(exc))
    except Exception as exc:
        db.session.rollback()
        return fail(f"导入失败：{exc}", 500)

    return success(_batch_to_dict(batch), message="导入完成")


@imports_bp.get("/<int:batch_id>")
@admin_required
def get_import_batch(batch_id: int):
    """查询导入批次详情。"""
    batch = ImportBatch.query.get(batch_id)
    if not batch:
        return fail("批次不存在", 404)
    return success(_batch_to_dict(batch))


@imports_bp.get("/<int:batch_id>/errors")
@admin_required
def download_errors(batch_id: int):
    """下载错误明细 Excel。"""
    batch = ImportBatch.query.get(batch_id)
    if not batch:
        return fail("批次不存在", 404)
    if not batch.error_report_path:
        return fail("该批次无错误报告", 404)
    path = Path(batch.error_report_path)
    if not path.exists():
        return fail("错误报告文件不存在", 404)
    return send_file(
        path,
        as_attachment=True,
        download_name=f"errors_{batch.batch_no}.xlsx",
    )
