"""生产环境 WSGI 入口（供 Gunicorn / uWSGI 加载）。"""

import os
from pathlib import Path

# 保证 backend 目录在模块搜索路径中
BACKEND_DIR = Path(__file__).resolve().parent
os.chdir(BACKEND_DIR)

# 生产环境默认配置（可被 .env / 系统环境变量覆盖）
os.environ.setdefault("FLASK_ENV", "production")

from app.utils.stdio_utf8 import configure_stdio_utf8

configure_stdio_utf8()

from app import create_app

app = create_app(os.getenv("FLASK_ENV", "production"))
