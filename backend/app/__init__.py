"""Flask 应用工厂。"""

import os
from pathlib import Path

from flask import Flask
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from app.api import register_blueprints
from app.config import config_map
from app.extensions import db, jwt, migrate
from app.utils.app_logging import log_request_exception, setup_logging
from app.utils.response import fail


def create_app(config_name=None):
    """创建并配置 Flask 应用。"""
    app = Flask(__name__)

    env = config_name or os.getenv("FLASK_ENV", "development")
    app.config.from_object(config_map.get(env, config_map["development"]))

    # 确保存储目录存在
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["EXPORT_FOLDER"]).mkdir(parents=True, exist_ok=True)

    # 报错文件日志（storage/logs/app.log）
    setup_logging(app)

    # 扩展初始化
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # 允许前端跨域（开发环境）
    CORS(
        app,
        resources={r"/api/*": {"origins": "*"}},
        supports_credentials=True,
    )

    register_blueprints(app)
    _register_error_handlers(app)

    return app


def _register_error_handlers(app: Flask) -> None:
    """注册全局异常处理：未捕获异常写入文件日志并返回统一 500。"""

    @app.errorhandler(Exception)
    def handle_uncaught_exception(exc):  # noqa: ANN001
        # Werkzeug/Flask 的 HTTPException（404/401 等）原样交给框架，不写报错文件
        if isinstance(exc, HTTPException):
            return exc
        log_request_exception("未捕获异常", exc)
        return fail(f"服务器内部错误：{exc}", 500)
