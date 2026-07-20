"""数据导出接口。"""

from pathlib import Path

from flask import Blueprint, current_app, g, request, send_file

from app.services.export_service import ExportService
from app.services.operation_log_service import write_operation_log
from app.extensions import db
from app.utils.auth_decorator import admin_required
from app.utils.response import fail

export_bp = Blueprint("export", __name__)


@export_bp.get("/tasks")
@admin_required
def export_tasks():
    """按筛选条件导出任务数据为 Excel。"""
    service = ExportService(Path(current_app.config["EXPORT_FOLDER"]))
    query = service.filter_tasks(
        status=request.args.get("status"),
        platform=request.args.get("platform"),
        batch_id=request.args.get("batch_id"),
        keyword=request.args.get("keyword", "").strip() or None,
    )
    count = query.count()
    if count == 0:
        return fail("没有可导出的数据")

    path, exported = service.export_tasks(query)
    write_operation_log(
        g.current_user.id,
        "export_tasks",
        "export",
        None,
        {"count": exported, "filters": dict(request.args)},
    )
    db.session.commit()

    return send_file(
        path,
        as_attachment=True,
        download_name=Path(path).name,
    )


@export_bp.get("/approved")
@admin_required
def export_approved():
    """导出正式库数据为 Excel。"""
    service = ExportService(Path(current_app.config["EXPORT_FOLDER"]))
    query = service.filter_approved(
        platform=request.args.get("platform"),
        keyword=request.args.get("keyword", "").strip() or None,
    )
    count = query.count()
    if count == 0:
        return fail("没有可导出的正式数据")

    path, exported = service.export_approved(query)
    write_operation_log(
        g.current_user.id,
        "export_approved",
        "export",
        None,
        {"count": exported},
    )
    db.session.commit()

    return send_file(
        path,
        as_attachment=True,
        download_name=Path(path).name,
    )
