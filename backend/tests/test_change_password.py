"""操作员自助修改密码 API 单测。"""
import json
import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from flask_jwt_extended import create_access_token

from app import create_app
from app.constants import ROLE_ADMIN, ROLE_OPERATOR
from app.extensions import db
from app.models.log import OperationLog
from app.models.user import SystemConfig, User


class ChangePasswordTests(unittest.TestCase):
    _UT_OP = "UT_CPWD_operator"
    _OLD = "OldPass12"
    _NEW = "NewPass34"

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()
        cls.ctx = cls.app.app_context()
        cls.ctx.push()

    @classmethod
    def tearDownClass(cls):
        cls._cleanup_ut_user()
        cls.ctx.pop()

    @classmethod
    def _cleanup_ut_user(cls):
        """删除 UT 用户及其操作日志，避免外键约束导致清理失败。"""
        op = User.query.filter_by(username=cls._UT_OP).first()
        if op:
            OperationLog.query.filter_by(user_id=op.id).delete(synchronize_session=False)
            db.session.delete(op)
            db.session.commit()

    def setUp(self):
        self._cleanup_ut_user()
        op = User(username=self._UT_OP, role=ROLE_OPERATOR, is_active=True)
        op.set_password(self._OLD)
        db.session.add(op)
        db.session.commit()
        self.op_id = op.id
        # 产品默认禁止操作员自助改密
        self._set_change_pwd_enabled(False)

    def _set_change_pwd_enabled(self, enabled: bool):
        """设置操作员改密开关（测试辅助）。"""
        key = "operator_change_password_enabled"
        row = SystemConfig.query.filter_by(config_key=key).first()
        if not row:
            row = SystemConfig(config_key=key, config_value="true" if enabled else "false")
            db.session.add(row)
        else:
            row.config_value = "true" if enabled else "false"
        db.session.commit()

    def _op_headers(self):
        token = create_access_token(identity=str(self.op_id))
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def _admin_headers(self):
        admin = User.query.filter_by(role=ROLE_ADMIN, is_active=True).first()
        self.assertIsNotNone(admin)
        token = create_access_token(identity=str(admin.id))
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def _post(self, headers, body):
        return self.client.post(
            "/api/auth/change-password",
            headers=headers,
            data=json.dumps(body),
        )

    def test_operator_success(self):
        self._set_change_pwd_enabled(True)
        resp = self._post(
            self._op_headers(),
            {
                "old_password": self._OLD,
                "new_password": self._NEW,
                "confirm_password": self._NEW,
            },
        )
        self.assertEqual(resp.status_code, 200)
        op = User.query.get(self.op_id)
        self.assertTrue(op.check_password(self._NEW))
        self.assertFalse(op.check_password(self._OLD))
        log = (
            OperationLog.query.filter_by(action="change_password", target_id=self.op_id)
            .order_by(OperationLog.id.desc())
            .first()
        )
        self.assertIsNotNone(log)

    def test_wrong_old_password(self):
        self._set_change_pwd_enabled(True)
        resp = self._post(
            self._op_headers(),
            {
                "old_password": "WrongPass1",
                "new_password": self._NEW,
                "confirm_password": self._NEW,
            },
        )
        self.assertEqual(resp.status_code, 400)
        body = json.loads(resp.data)
        self.assertIn("原密码", body["message"])
        op = User.query.get(self.op_id)
        self.assertTrue(op.check_password(self._OLD))

    def test_confirm_mismatch(self):
        self._set_change_pwd_enabled(True)
        resp = self._post(
            self._op_headers(),
            {
                "old_password": self._OLD,
                "new_password": self._NEW,
                "confirm_password": "NewPass99",
            },
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("不一致", json.loads(resp.data)["message"])

    def test_weak_password(self):
        self._set_change_pwd_enabled(True)
        resp = self._post(
            self._op_headers(),
            {
                "old_password": self._OLD,
                "new_password": "short1",
                "confirm_password": "short1",
            },
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("8", json.loads(resp.data)["message"])

    def test_same_as_old(self):
        self._set_change_pwd_enabled(True)
        resp = self._post(
            self._op_headers(),
            {
                "old_password": self._OLD,
                "new_password": self._OLD,
                "confirm_password": self._OLD,
            },
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("不能与原密码相同", json.loads(resp.data)["message"])

    def test_admin_forbidden(self):
        resp = self._post(
            self._admin_headers(),
            {
                "old_password": "x",
                "new_password": self._NEW,
                "confirm_password": self._NEW,
            },
        )
        self.assertEqual(resp.status_code, 403)
        self.assertIn("用户管理", json.loads(resp.data)["message"])

    def test_disabled_returns_403(self):
        self._set_change_pwd_enabled(False)
        resp = self._post(
            self._op_headers(),
            {
                "old_password": self._OLD,
                "new_password": self._NEW,
                "confirm_password": self._NEW,
            },
        )
        self.assertEqual(resp.status_code, 403)
        body = json.loads(resp.data)
        self.assertIn("未开放", body.get("message", ""))
        op = User.query.get(self.op_id)
        self.assertTrue(op.check_password(self._OLD))

    def test_me_includes_flag_false(self):
        self._set_change_pwd_enabled(False)
        resp = self.client.get("/api/auth/me", headers=self._op_headers())
        self.assertEqual(resp.status_code, 200)
        body = json.loads(resp.data)
        self.assertFalse(body["data"]["operator_change_password_enabled"])

    def test_me_includes_flag_true(self):
        self._set_change_pwd_enabled(True)
        resp = self.client.get("/api/auth/me", headers=self._op_headers())
        self.assertEqual(resp.status_code, 200)
        body = json.loads(resp.data)
        self.assertTrue(body["data"]["operator_change_password_enabled"])


if __name__ == "__main__":
    unittest.main()
