"""应用报错文件日志单测（不依赖业务库表数据）。"""

from __future__ import annotations

import logging
import sys
import tempfile
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from flask import Flask, g

from app.utils.app_logging import (
    LOGGER_NAME,
    log_request_exception,
    setup_logging,
)
from app.utils.response import fail


class AppLoggingTests(unittest.TestCase):
    """验证滚动文件日志与请求异常落盘内容。"""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.log_dir = Path(self._tmpdir.name)
        self.app = Flask(__name__)
        self.app.config["LOG_DIR"] = str(self.log_dir)
        self.app.config["LOG_MAX_BYTES"] = 1024 * 1024
        self.app.config["LOG_BACKUP_COUNT"] = 3
        setup_logging(self.app)

        @self.app.errorhandler(Exception)
        def _handle_uncaught(exc):  # noqa: ANN001
            # 与 create_app 中全局处理器行为一致，便于集成断言
            from app.utils.app_logging import log_request_exception as _log

            _log("未捕获异常", exc)
            return fail(f"服务器内部错误：{exc}", 500)

        @self.app.post("/boom")
        def boom():
            raise RuntimeError("故意爆炸")

        @self.app.post("/caught")
        def caught():
            try:
                raise RuntimeError("捕获后记录")
            except Exception as exc:
                log_request_exception("导入Excel", exc)
                return fail(f"导入失败：{exc}", 500)

        self.client = self.app.test_client()

    def tearDown(self):
        # 关闭 handler，避免 Windows 下临时目录无法删除
        logger = logging.getLogger(LOGGER_NAME)
        for handler in list(logger.handlers):
            handler.close()
            logger.removeHandler(handler)
        self._tmpdir.cleanup()

    def _read_log(self) -> str:
        path = self.log_dir / "app.log"
        self.assertTrue(path.exists(), "应创建 app.log")
        # 刷新所有 handler
        for handler in logging.getLogger(LOGGER_NAME).handlers:
            handler.flush()
        return path.read_text(encoding="utf-8")

    def test_setup_logging_creates_app_log_file(self):
        """setup_logging 后应存在 app.log。"""
        self.assertTrue((self.log_dir / "app.log").exists())

    def test_log_request_exception_writes_operation_user_path_stack(self):
        """API 捕获异常时应写入操作名、用户、路径与堆栈。"""

        class FakeUser:
            id = 9
            username = "admin"

        with self.app.test_request_context("/api/imports", method="POST", query_string="x=1"):
            g.current_user = FakeUser()
            try:
                raise ValueError("模拟失败")
            except Exception as exc:
                log_request_exception("导入Excel", exc)

        text = self._read_log()
        self.assertIn("操作=导入Excel", text)
        self.assertIn("用户=admin(id=9)", text)
        self.assertIn("POST /api/imports", text)
        self.assertIn("Query=x=1", text)
        self.assertIn("ValueError: 模拟失败", text)
        self.assertIn("Traceback", text)

    def test_uncaught_exception_handler_writes_log(self):
        """未捕获异常经全局处理器写入「未捕获异常」。"""
        resp = self.client.post("/boom")
        self.assertEqual(resp.status_code, 500)
        text = self._read_log()
        self.assertIn("操作=未捕获异常", text)
        self.assertIn("RuntimeError: 故意爆炸", text)
        self.assertIn("Traceback", text)
        self.assertIn("POST /boom", text)

    def test_caught_route_logs_chinese_operation(self):
        """路由内捕获后调用 log_request_exception 写入中文操作名。"""
        resp = self.client.post("/caught")
        self.assertEqual(resp.status_code, 500)
        text = self._read_log()
        self.assertIn("操作=导入Excel", text)
        self.assertIn("捕获后记录", text)


if __name__ == "__main__":
    unittest.main()
