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
from app.utils.init_db import init_database, reset_keep_admin_and_rules

app = create_app()


@app.cli.command("init-db")
def init_db_command():
    """创建数据库表并初始化默认管理员。"""
    init_database(app)


@app.cli.command("reset-keep-admin-rules")
@click.option(
    "--yes",
    "confirm",
    is_flag=True,
    help="跳过确认，直接执行（危险操作）",
)
def reset_keep_admin_rules_command(confirm: bool):
    """清空业务数据，只保留管理员账号与分类规则。"""
    if not confirm:
        click.confirm(
            "将删除任务/导入/正式库/操作员/日志等，仅保留管理员与规则。确认继续？",
            abort=True,
        )
    reset_keep_admin_and_rules(app)


if __name__ == "__main__":
    app.cli.main()
