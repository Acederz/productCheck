"""应用配置。"""

import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

# 加载 backend/.env（必须使用绝对路径，避免从其他目录启动时读不到）
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"
load_dotenv(ENV_FILE, override=True)


class Config:
    """基础配置。"""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-key")
    JWT_ACCESS_TOKEN_EXPIRES = False  # 内网系统，简化第一期实现

    # MySQL 连接
    MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
    MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "product_check")

    # 密码中若含 ! @ # 等特殊字符，必须 URL 编码，否则连接串会解析错误
    _user = quote_plus(MYSQL_USER)
    _password = quote_plus(MYSQL_PASSWORD)
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{_user}:{_password}"
        f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 3600,
    }

    # 文件存储
    STORAGE_PATH = (BASE_DIR / os.getenv("STORAGE_PATH", "../storage")).resolve()
    UPLOAD_FOLDER = STORAGE_PATH / "uploads"
    EXPORT_FOLDER = STORAGE_PATH / "exports"

    # 默认管理员
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 上传限制 50MB


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}
