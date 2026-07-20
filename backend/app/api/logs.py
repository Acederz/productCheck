"""日志查询接口。"""

from flask import Blueprint, request

from app.services.log_service import LogService
from app.utils.auth_decorator import admin_required
from app.utils.response import success

logs_bp = Blueprint("logs", __name__)
log_service = LogService()


@logs_bp.get("/operations")
@admin_required
def list_operation_logs():
    """操作日志列表。"""
    page = max(int(request.args.get("page", 1)), 1)
    page_size = min(max(int(request.args.get("page_size", 20)), 1), 100)
    action = request.args.get("action", "").strip()
    return success(log_service.list_operation_logs(page, page_size, action))


@logs_bp.get("/changes")
@admin_required
def list_field_change_logs():
    """字段变更日志。"""
    page = max(int(request.args.get("page", 1)), 1)
    page_size = min(max(int(request.args.get("page_size", 20)), 1), 100)
    task_id = request.args.get("task_id")
    tid = int(task_id) if task_id else None
    return success(log_service.list_field_change_logs(page, page_size, tid))
