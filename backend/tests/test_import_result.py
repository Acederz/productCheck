"""北京时间格式化 + 导入结果（成功 / 部分失败 / 失败留痕）单测。内存 SQLite，不写共享 MySQL。"""

from __future__ import annotations

import io
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

import tests.sqlite_compat  # noqa: F401  # 必须在建表前注册

from flask_jwt_extended import create_access_token
from openpyxl import Workbook
from werkzeug.datastructures import FileStorage

from app import create_app
from app.constants import EXCEL_HEADERS, EXCEL_OPERATOR_HEADER, ROLE_ADMIN, ROLE_OPERATOR
from app.extensions import db
from app.models.task import ClassificationTask, ImportBatch
from app.models.user import User
from app.services.import_service import ImportBatchError, ImportService
from app.utils.time_utils import fmt_beijing


def _xlsx_bytes(rows: list[list], headers: list | None = None) -> bytes:
    """生成内存 Excel。"""
    wb = Workbook()
    ws = wb.active
    ws.append(list(headers if headers is not None else EXCEL_HEADERS))
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _row(product_id: str, platform: str = "淘宝", operator: str | None = None) -> list:
    """构造一行业务数据（19 列，可选操作员列）。"""
    values = {h: "" for h in EXCEL_HEADERS}
    values["宝贝ID"] = product_id
    values["宝贝名称"] = f"商品{product_id}"
    values["数据平台"] = platform
    row = [values[h] for h in EXCEL_HEADERS]
    if operator is not None:
        row.append(operator)
    return row


class FmtBeijingTests(unittest.TestCase):
    def test_naive_utc_to_beijing(self):
        self.assertEqual(fmt_beijing(datetime(2026, 11, 5, 0, 59, 10)), "2026-11-05 08:59:10")

    def test_cross_day(self):
        self.assertEqual(fmt_beijing(datetime(2026, 11, 5, 20, 0, 0)), "2026-11-06 04:00:00")

    def test_aware_datetime(self):
        dt = datetime(2026, 11, 5, 8, 0, 0, tzinfo=timezone(timedelta(hours=8)))
        self.assertEqual(fmt_beijing(dt), "2026-11-05 08:00:00")

    def test_none(self):
        self.assertIsNone(fmt_beijing(None))


class ImportResultTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.app = create_app("testing")
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.client = self.app.test_client()

        self.admin = User(username="ut_admin", role=ROLE_ADMIN, is_active=True)
        self.admin.set_password("x")
        self.op = User(username="ut_op", role=ROLE_OPERATOR, is_active=True)
        self.op.set_password("x")
        db.session.add_all([self.admin, self.op])
        db.session.commit()
        self.service = ImportService(Path(self._tmp.name))

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()
        self._tmp.cleanup()

    def _file(self, data: bytes, name: str = "测试.xlsx") -> FileStorage:
        return FileStorage(stream=io.BytesIO(data), filename=name)

    # ---------- 服务层 ----------

    def test_success_returns_summary_and_beijing_time(self):
        headers = [*EXCEL_HEADERS, EXCEL_OPERATOR_HEADER]
        data = _xlsx_bytes([_row("A1", operator="ut_op"), _row("A2", operator="nobody")], headers)
        batch, summary = self.service.import_excel(self._file(data), self.admin.id)

        self.assertEqual(batch.status, "completed")
        self.assertEqual(batch.success_rows, 2)
        self.assertEqual(batch.fail_rows, 0)
        self.assertIsNone(batch.fail_reason)
        self.assertEqual(summary, {"warning_rows": 1, "assigned_rows": 1})
        # to_dict 时间为北京时间格式（无 T）
        self.assertNotIn("T", batch.to_dict()["created_at"])
        self.assertIn("fail_reason", batch.to_dict())

    def test_partial_failure_counts_failed_rows(self):
        data = _xlsx_bytes([_row("B1"), _row("B2", platform="拼多多")])
        batch, _ = self.service.import_excel(self._file(data), self.admin.id)
        self.assertEqual(batch.status, "completed")
        self.assertEqual(batch.success_rows, 1)
        self.assertEqual(batch.fail_rows, 1)

    def test_header_error_keeps_failed_batch_with_reason(self):
        bad_headers = ["错误表头", *EXCEL_HEADERS[1:]]
        data = _xlsx_bytes([_row("C1")], bad_headers)
        with self.assertRaises(ImportBatchError) as cm:
            self.service.import_excel(self._file(data), self.admin.id)
        err = cm.exception
        self.assertFalse(err.unexpected)
        self.assertIn("表头", str(err))
        saved = ImportBatch.query.get(err.batch.id)
        self.assertEqual(saved.status, "failed")
        self.assertIn("表头", saved.fail_reason)

    def test_unreadable_file_is_expected_failure(self):
        with self.assertRaises(ImportBatchError) as cm:
            self.service.import_excel(self._file(b"not an excel"), self.admin.id)
        self.assertFalse(cm.exception.unexpected)
        self.assertIn("文件无法读取", cm.exception.batch.fail_reason)

    def test_unexpected_error_rolls_back_and_records_failed_batch(self):
        data = _xlsx_bytes([_row("D1"), _row("D2")])
        with mock.patch.object(
            ImportService, "_row_to_task", side_effect=RuntimeError("数据库炸了")
        ):
            with self.assertRaises(ImportBatchError) as cm:
                self.service.import_excel(self._file(data), self.admin.id)
        err = cm.exception
        self.assertTrue(err.unexpected)
        self.assertIsInstance(err.__cause__, RuntimeError)
        saved = ImportBatch.query.get(err.batch.id)
        self.assertEqual(saved.status, "failed")
        self.assertIn("服务器异常", saved.fail_reason)
        self.assertIn("数据库炸了", saved.fail_reason)
        self.assertEqual(ClassificationTask.query.count(), 0)

    # ---------- API ----------

    def _admin_headers(self) -> dict:
        return {"Authorization": f"Bearer {create_access_token(identity=str(self.admin.id))}"}

    def _post(self, data: bytes):
        self.app.config["UPLOAD_FOLDER"] = self._tmp.name
        return self.client.post(
            "/api/imports",
            headers=self._admin_headers(),
            data={"file": (io.BytesIO(data), "测试.xlsx")},
            content_type="multipart/form-data",
        )

    def test_api_success_includes_summary(self):
        resp = self._post(_xlsx_bytes([_row("E1")]))
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()["data"]
        self.assertEqual(body["status"], "completed")
        self.assertEqual(body["warning_rows"], 0)
        self.assertEqual(body["assigned_rows"], 0)

    def test_api_header_error_returns_400_with_batch(self):
        resp = self._post(_xlsx_bytes([_row("F1")], ["错误表头", *EXCEL_HEADERS[1:]]))
        self.assertEqual(resp.status_code, 400)
        body = resp.get_json()
        self.assertIn("表头", body["message"])
        self.assertEqual(body["data"]["status"], "failed")
        self.assertIn("表头", body["data"]["fail_reason"])

    def test_api_unexpected_error_returns_500_with_batch(self):
        with mock.patch.object(ImportService, "_row_to_task", side_effect=RuntimeError("boom")):
            resp = self._post(_xlsx_bytes([_row("G1")]))
        self.assertEqual(resp.status_code, 500)
        body = resp.get_json()
        self.assertEqual(body["data"]["status"], "failed")
        self.assertIn("服务器异常", body["data"]["fail_reason"])


if __name__ == "__main__":
    unittest.main()
