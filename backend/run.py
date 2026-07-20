"""后端启动入口。"""

import sys
from pathlib import Path

# 将 backend 目录加入 Python 路径
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# 必须在创建 Flask / 打印日志之前配置，避免中文访问日志乱码
from app.utils.stdio_utf8 import configure_stdio_utf8

configure_stdio_utf8()

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
