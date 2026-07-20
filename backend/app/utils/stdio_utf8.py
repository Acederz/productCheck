"""Windows 控制台 / 管道下的 UTF-8 输出配置，避免中文日志乱码。"""

from __future__ import annotations

import os
import sys


def configure_stdio_utf8() -> None:
    """将标准输出/错误流及环境变量切换为 UTF-8。

    说明：
    - 中文 Windows 默认代码页常为 GBK(cp936)。
    - Flask/Werkzeug 访问日志会打印含中文的 URL（如规则字段名）。
    - 经 npm concurrently / Cursor 终端捕获时，若编码不一致会出现乱码。
    """
    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    if sys.platform == "win32":
        try:
            import ctypes

            # 控制台代码页切到 UTF-8（对直接在 cmd 运行有效）
            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
            ctypes.windll.kernel32.SetConsoleCP(65001)
        except Exception:
            pass
