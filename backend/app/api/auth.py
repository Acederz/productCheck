"""认证接口。"""

from flask import Blueprint, g, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required

from app.models.user import User
from app.utils.auth_decorator import get_current_user, login_required
from app.utils.response import fail, success

auth_bp = Blueprint("auth", __name__)


def _is_operator_change_password_enabled() -> bool:
    """读取系统配置：仅当值为 'true' 时允许操作员自助改密。"""
    from app.models.user import SystemConfig

    row = SystemConfig.query.filter_by(
        config_key="operator_change_password_enabled"
    ).first()
    return bool(row and row.config_value == "true")


def _user_payload(user) -> dict:
    """用户字典 + 改密开关标志（供 login / me）。"""
    data = user.to_dict()
    data["operator_change_password_enabled"] = _is_operator_change_password_enabled()
    return data


@auth_bp.post("/login")
def login():
    """账号密码登录。"""
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return fail("请输入账号和密码")

    user = User.query.filter_by(username=username).first()
    if not user or not user.is_active or not user.check_password(password):
        return fail("账号或密码错误", 401)

    token = create_access_token(identity=str(user.id))
    return success(
        {"token": token, "user": _user_payload(user)},
        message="登录成功",
    )


@auth_bp.post("/logout")
@jwt_required()
def logout():
    """登出（前端清除 token 即可）。"""
    return success(message="已登出")


@auth_bp.get("/me")
@jwt_required()
def me():
    """获取当前用户信息。"""
    user = get_current_user()
    if not user:
        return fail("未登录", 401)
    return success(_user_payload(user))


def _password_strength_ok(password: str) -> bool:
    """新密码至少 8 位且同时含字母与数字。"""
    if len(password) < 8:
        return False
    has_letter = any(c.isalpha() for c in password)
    has_digit = any(c.isdigit() for c in password)
    return has_letter and has_digit


@auth_bp.post("/change-password")
@login_required
def change_password():
    """操作员自助修改密码。"""
    from app.constants import ROLE_OPERATOR
    from app.extensions import db
    from app.services.operation_log_service import write_operation_log

    if g.current_user.role != ROLE_OPERATOR:
        return fail("请使用用户管理重置密码", 403)

    if not _is_operator_change_password_enabled():
        return fail("管理员未开放修改密码", 403)

    data = request.get_json(silent=True) or {}
    old_password = data.get("old_password") or ""
    new_password = data.get("new_password") or ""
    confirm_password = data.get("confirm_password") or ""

    if not old_password or not new_password or not confirm_password:
        return fail("请填写原密码、新密码和确认密码")
    if new_password != confirm_password:
        return fail("两次输入的新密码不一致")
    if not _password_strength_ok(new_password):
        return fail("新密码至少 8 位，且需同时包含字母和数字")
    if not g.current_user.check_password(old_password):
        return fail("原密码错误")
    if g.current_user.check_password(new_password):
        return fail("新密码不能与原密码相同")

    g.current_user.set_password(new_password)
    write_operation_log(
        g.current_user.id,
        "change_password",
        "user",
        g.current_user.id,
        {},
    )
    db.session.commit()
    return success(message="密码修改成功")
