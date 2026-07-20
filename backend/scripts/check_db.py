"""检查数据库配置与连接（在 backend 目录、已激活 .venv 后运行）。"""

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.utils.stdio_utf8 import configure_stdio_utf8

configure_stdio_utf8()

from app.config import ENV_FILE, Config


def main():
    print("=== 数据库配置检查 ===")
    print(f".env 文件路径: {ENV_FILE}")
    print(f".env 是否存在: {ENV_FILE.exists()}")
    print(f"MYSQL_HOST: {Config.MYSQL_HOST}")
    print(f"MYSQL_PORT: {Config.MYSQL_PORT}")
    print(f"MYSQL_USER: {Config.MYSQL_USER}")
    print(f"MYSQL_PASSWORD 已设置: {'是' if Config.MYSQL_PASSWORD else '否（这会导致 1045 错误）'}")
    print(f"MYSQL_DATABASE: {Config.MYSQL_DATABASE}")

    if not ENV_FILE.exists():
        print("\n[错误] 未找到 backend/.env，请执行: copy .env.example .env")
        sys.exit(1)

    if not Config.MYSQL_PASSWORD:
        print("\n[错误] MYSQL_PASSWORD 为空，请编辑 backend/.env 填写密码")
        sys.exit(1)

    try:
        import pymysql

        conn = pymysql.connect(
            host=Config.MYSQL_HOST,
            port=int(Config.MYSQL_PORT),
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DATABASE,
            charset="utf8mb4",
        )
        conn.close()
        print("\n[成功] 数据库连接正常，可执行: python manage.py init-db")
    except Exception as exc:
        print(f"\n[失败] 连接错误: {exc}")
        print("\n请检查:")
        print("  1. MySQL 服务是否启动")
        print("  2. .env 中主机、账号、密码是否正确")
        print("  3. 数据库 product_check 是否已创建")
        print("  4. 用户是否有该库的权限")
        sys.exit(1)


if __name__ == "__main__":
    main()
