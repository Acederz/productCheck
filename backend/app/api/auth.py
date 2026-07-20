"""认证接口。"""

from flask import Blueprint, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required

from app.models.user import User
from app.utils.auth_decorator import get_current_user
from app.utils.response import fail, success

auth_bp = Blueprint("auth", __name__)


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
        {"token": token, "user": user.to_dict()},
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
    return success(user.to_dict())
