"""认证相关工具。"""

from functools import wraps

from flask import g
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from app.constants import ROLE_ADMIN
from app.models.user import User
from app.utils.response import fail


def get_current_user():
    """获取当前登录用户对象。"""
    user_id = get_jwt_identity()
    if user_id is None:
        return None
    return User.query.get(int(user_id))


def login_required(fn):
    """登录校验装饰器。"""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user = get_current_user()
        if not user or not user.is_active:
            return fail("未登录或账号已停用", 401)
        g.current_user = user
        return fn(*args, **kwargs)

    return wrapper


def admin_required(fn):
    """管理员权限装饰器。"""

    @wraps(fn)
    @login_required
    def wrapper(*args, **kwargs):
        if g.current_user.role != ROLE_ADMIN:
            return fail("需要管理员权限", 403)
        return fn(*args, **kwargs)

    return wrapper
