"""用户管理接口（管理员）。"""

from flask import Blueprint, g, request

from app.constants import ROLE_ADMIN, ROLE_OPERATOR
from app.extensions import db
from app.models.user import User
from app.utils.auth_decorator import admin_required
from app.utils.response import fail, success

users_bp = Blueprint("users", __name__)


@users_bp.get("")
@admin_required
def list_users():
    """用户列表。"""
    users = User.query.order_by(User.id.asc()).all()
    return success([u.to_dict() for u in users])


@users_bp.post("")
@admin_required
def create_user():
    """创建用户。"""
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    role = data.get("role") or ROLE_OPERATOR

    if not username or not password:
        return fail("账号和密码不能为空")
    if role not in (ROLE_ADMIN, ROLE_OPERATOR):
        return fail("角色无效")
    if User.query.filter_by(username=username).first():
        return fail("账号已存在")

    user = User(username=username, role=role, is_active=True)
    user.set_password(password)
    db.session.add(user)
    from app.services.operation_log_service import write_operation_log
    write_operation_log(g.current_user.id, "create_user", "user", None, {"username": username, "role": role})
    db.session.commit()
    return success(user.to_dict(), message="创建成功")


@users_bp.put("/<int:user_id>")
@admin_required
def update_user(user_id: int):
    """更新用户状态或重置密码。"""
    user = User.query.get(user_id)
    if not user:
        return fail("用户不存在", 404)

    data = request.get_json(silent=True) or {}
    if "is_active" in data:
        user.is_active = bool(data["is_active"])
    if data.get("password"):
        user.set_password(data["password"])

    from app.services.operation_log_service import write_operation_log
    write_operation_log(g.current_user.id, "update_user", "user", user_id, {"is_active": user.is_active})
    db.session.commit()
    return success(user.to_dict(), message="更新成功")
