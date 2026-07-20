"""Flask 应用工厂。"""

import os
from pathlib import Path

from flask import Flask
from flask_cors import CORS

from app.api import register_blueprints
from app.config import config_map
from app.extensions import db, jwt, migrate


def create_app(config_name=None):
    """创建并配置 Flask 应用。"""
    app = Flask(__name__)

    env = config_name or os.getenv("FLASK_ENV", "development")
    app.config.from_object(config_map.get(env, config_map["development"]))

    # 确保存储目录存在
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["EXPORT_FOLDER"]).mkdir(parents=True, exist_ok=True)

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

    return app
