"""健康检查接口。"""

from flask import Blueprint

from app.utils.response import success

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health_check():
    """服务存活探测。"""
    return success({"status": "ok"}, message="服务运行正常")
