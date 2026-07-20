"""操作日志写入。"""

from flask import request

from app.extensions import db
from app.models.log import OperationLog


def write_operation_log(user_id, action, target_type=None, target_id=None, detail=None):
    """记录一条操作日志。"""
    ip = request.remote_addr if request else None
    log = OperationLog(
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail_json=detail,
        ip=ip,
    )
    db.session.add(log)
