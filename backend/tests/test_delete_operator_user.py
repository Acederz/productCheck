"""管理员删除操作员账号单测。"""
import json
import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from flask_jwt_extended import create_access_token

from app import create_app
from app.constants import (
    ROLE_ADMIN,
    ROLE_OPERATOR,
    TASK_STATUS_APPROVED,
    TASK_STATUS_PENDING,
    TASK_STATUS_REJECTED,
    TASK_STATUS_REVIEW,
)
from app.extensions import db
from app.models.log import OperationLog
from app.models.task import ClassificationTask, TaskDraft
from app.models.user import User


class DeleteOperatorUserTests(unittest.TestCase):
    _UT_OP = "UT_DEL_USER_op"

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()
        cls.ctx = cls.app.app_context()
        cls.ctx.push()

    @classmethod
    def tearDownClass(cls):
        cls._cleanup_op()
        cls.ctx.pop()

    @classmethod
    def _cleanup_op(cls):
        op = User.query.filter_by(username=cls._UT_OP).first()
        if not op:
            return
        TaskDraft.query.filter_by(assignee_id=op.id).delete(synchronize_session=False)
        ClassificationTask.query.filter_by(assignee_id=op.id).update(
            {ClassificationTask.assignee_id: None}, synchronize_session=False
        )
        ClassificationTask.query.filter_by(reviewed_by=op.id).update(
            {ClassificationTask.reviewed_by: None}, synchronize_session=False
        )
        db.session.delete(op)
        db.session.commit()

    def setUp(self):
        self._cleanup_op()
        op = User(username=self._UT_OP, role=ROLE_OPERATOR, is_active=True)
        op.set_password("OpPass12")
        db.session.add(op)
        db.session.commit()
        self.op_id = op.id

    def _admin_headers(self):
        admin = User.query.filter_by(role=ROLE_ADMIN, is_active=True).first()
        self.assertIsNotNone(admin)
        token = create_access_token(identity=str(admin.id))
        return {"Authorization": f"Bearer {token}"}

    def _make_task(self, status: str) -> ClassificationTask:
        t = ClassificationTask(
            product_id=f"P_{status}_{self.op_id}",
            product_name="n",
            platform="淘宝",
            status=status,
            assignee_id=self.op_id,
        )
        db.session.add(t)
        db.session.commit()
        return t

    def test_delete_operator_ok(self):
        resp = self.client.delete(
            f"/api/users/{self.op_id}", headers=self._admin_headers()
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(User.query.filter_by(username=self._UT_OP).first())
        log = (
            OperationLog.query.filter_by(action="delete_user", target_id=self.op_id)
            .order_by(OperationLog.id.desc())
            .first()
        )
        self.assertIsNotNone(log)
        self.assertEqual(log.detail_json.get("username"), self._UT_OP)
        self.assertEqual(log.detail_json.get("user_id"), self.op_id)

    def test_reject_when_pending_tasks(self):
        self._make_task(TASK_STATUS_PENDING)
        resp = self.client.delete(
            f"/api/users/{self.op_id}", headers=self._admin_headers()
        )
        self.assertEqual(resp.status_code, 400)
        body = json.loads(resp.data)
        self.assertIn("未完成", body["message"])
        self.assertIsNotNone(User.query.get(self.op_id))

    def test_reject_when_review_tasks(self):
        self._make_task(TASK_STATUS_REVIEW)
        resp = self.client.delete(
            f"/api/users/{self.op_id}", headers=self._admin_headers()
        )
        self.assertEqual(resp.status_code, 400)
        body = json.loads(resp.data)
        self.assertIn("未完成", body["message"])
        self.assertIsNotNone(User.query.get(self.op_id))

    def test_reject_when_rejected_tasks(self):
        self._make_task(TASK_STATUS_REJECTED)
        resp = self.client.delete(
            f"/api/users/{self.op_id}", headers=self._admin_headers()
        )
        self.assertEqual(resp.status_code, 400)
        body = json.loads(resp.data)
        self.assertIn("未完成", body["message"])
        self.assertIsNotNone(User.query.get(self.op_id))

    def test_allow_when_only_approved(self):
        t = self._make_task(TASK_STATUS_APPROVED)
        resp = self.client.delete(
            f"/api/users/{self.op_id}", headers=self._admin_headers()
        )
        self.assertEqual(resp.status_code, 200)
        db.session.refresh(t)
        self.assertIsNone(t.assignee_id)
        self.assertEqual(t.status, TASK_STATUS_APPROVED)

    def test_reject_delete_admin(self):
        # 创建另一名管理员作为删除目标（避免与登录管理员为同一人）
        target_name = "UT_DEL_USER_admin_target"
        target = User.query.filter_by(username=target_name).first()
        if target:
            db.session.delete(target)
            db.session.commit()
        target = User(username=target_name, role=ROLE_ADMIN, is_active=True)
        target.set_password("AdPass12")
        db.session.add(target)
        db.session.commit()
        resp = self.client.delete(
            f"/api/users/{target.id}", headers=self._admin_headers()
        )
        self.assertEqual(resp.status_code, 403)
        self.assertIn("管理员", json.loads(resp.data)["message"])
        db.session.delete(target)
        db.session.commit()

    def test_reject_delete_self(self):
        # 用临时管理员作为「自己」：创建 UT 管理员再删自己
        name = "UT_DEL_USER_admin_self"
        u = User.query.filter_by(username=name).first()
        if u:
            db.session.delete(u)
            db.session.commit()
        u = User(username=name, role=ROLE_ADMIN, is_active=True)
        u.set_password("AdPass12")
        db.session.add(u)
        db.session.commit()
        headers = {
            "Authorization": f"Bearer {create_access_token(identity=str(u.id))}"
        }
        resp = self.client.delete(f"/api/users/{u.id}", headers=headers)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("当前登录", json.loads(resp.data)["message"])
        db.session.delete(u)
        db.session.commit()


if __name__ == "__main__":
    unittest.main()
