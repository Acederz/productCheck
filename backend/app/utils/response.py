"""统一 API 响应格式。"""

from flask import jsonify


def success(data=None, message="ok", code=200):
    """成功响应。"""
    payload = {"code": code, "message": message, "data": data}
    return jsonify(payload), code


def fail(message="error", code=400, data=None):
    """失败响应。"""
    payload = {"code": code, "message": message, "data": data}
    return jsonify(payload), code
