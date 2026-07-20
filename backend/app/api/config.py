"""系统配置接口。"""

from flask import Blueprint, g, request

from app.extensions import db
from app.models.user import SystemConfig
from app.services.operation_log_service import write_operation_log
from app.utils.auth_decorator import admin_required
from app.utils.response import fail, success

config_bp = Blueprint("config", __name__)


@config_bp.get("")
@admin_required
def get_configs():
    """获取系统配置。"""
    items = SystemConfig.query.all()
    data = {c.config_key: c.config_value for c in items}
    return success(data)


@config_bp.put("/<key>")
@admin_required
def update_config(key: str):
    """更新系统配置项。"""
    data = request.get_json(silent=True) or {}
    value = data.get("value")
    if value is None:
        return fail("请提供 value")

    config = SystemConfig.query.filter_by(config_key=key).first()
    if not config:
        config = SystemConfig(config_key=key, config_value=str(value))
        db.session.add(config)
    else:
        config.config_value = str(value)
        config.updated_by = g.current_user.id

    write_operation_log(
        g.current_user.id,
        "update_config",
        "system_config",
        config.id,
        {"key": key, "value": value},
    )
    db.session.commit()
    return success(message="配置已更新")
