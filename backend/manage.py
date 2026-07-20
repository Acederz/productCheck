"""CLI 管理命令。"""

from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.utils.stdio_utf8 import configure_stdio_utf8

configure_stdio_utf8()

import click

from app import create_app
from app.utils.init_db import init_database

app = create_app()


@app.cli.command("init-db")
def init_db_command():
    """创建数据库表并初始化默认管理员。"""
    init_database(app)


if __name__ == "__main__":
    app.cli.main()
