"""应用报错文件日志：滚动写入 storage/logs，便于对照操作定位异常。"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from flask import Flask, g, has_request_context, request

# 统一 logger 名，业务与全局处理器共用
LOGGER_NAME = "product_check"

# Query 写入日志时的最大长度，避免超长 URL 刷屏
_QUERY_MAX_LEN = 200


def setup_logging(app: Flask) -> None:
    """配置滚动文件日志，并确保日志目录存在。

    配置项（均有默认值）：
    - LOG_DIR：日志目录
    - LOG_MAX_BYTES：单文件大小上限
    - LOG_BACKUP_COUNT：滚动备份个数
    """
    log_dir = Path(app.config.get("LOG_DIR") or (Path(app.config["STORAGE_PATH"]) / "logs"))
    log_dir.mkdir(parents=True, exist_ok=True)
    app.config["LOG_DIR"] = str(log_dir)

    max_bytes = int(app.config.get("LOG_MAX_BYTES") or 10 * 1024 * 1024)
    backup_count = int(app.config.get("LOG_BACKUP_COUNT") or 10)

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    # 避免重复添加 handler（例如测试或 reloader 二次调用）
    log_path = log_dir / "app.log"
    already = any(
        isinstance(h, RotatingFileHandler) and Path(getattr(h, "baseFilename", "")) == log_path.resolve()
        for h in logger.handlers
    )
    if not already:
        handler = RotatingFileHandler(
            log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        handler.setLevel(logging.INFO)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s [%(name)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(handler)

    # 确保空文件被创建，便于运维确认路径可用
    if not log_path.exists():
        log_path.touch()


def _format_user() -> str:
    """从 flask.g 取当前用户展示串；未登录为「匿名」。"""
    user = getattr(g, "current_user", None) if has_request_context() else None
    if user is None:
        return "匿名"
    username = getattr(user, "username", None) or "?"
    user_id = getattr(user, "id", None)
    if user_id is None:
        return str(username)
    return f"{username}(id={user_id})"


def _format_request_bits() -> tuple[str, str]:
    """返回 (方法+路径, Query 摘要)。无请求上下文时用占位。"""
    if not has_request_context():
        return "-", "-"
    method_path = f"{request.method} {request.path}"
    raw = request.query_string.decode("utf-8", errors="replace") if request.query_string else ""
    if not raw:
        query = "-"
    else:
        query = raw if len(raw) <= _QUERY_MAX_LEN else raw[:_QUERY_MAX_LEN] + "…"
    return method_path, query


def log_request_exception(operation: str, exc: BaseException) -> None:
    """将请求相关异常写入文件日志（含堆栈）。

    :param operation: 中文操作名，如「导入Excel」「未捕获异常」
    :param exc: 捕获到的异常实例
    """
    method_path, query = _format_request_bits()
    # Body 仅标记有无，避免密码与上传内容入日志
    if has_request_context() and request.content_length:
        body_summary = f"有(content-type={request.content_type or '-'})"
    else:
        body_summary = "-"

    message = (
        f"操作={operation} | 用户={_format_user()} | {method_path} | "
        f"Query={query} | Body摘要={body_summary} | "
        f"异常={type(exc).__name__}: {exc}"
    )
    logging.getLogger(LOGGER_NAME).error(message, exc_info=exc)
