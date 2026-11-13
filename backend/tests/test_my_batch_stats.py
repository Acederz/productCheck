"""操作员按批次切换统计：服务与 API 单测（内存 SQLite，不写共享 MySQL）。"""

from __future__ import annotations

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
from app.models.task import ClassificationTask, ImportBatch
from app.models.user import User
from app.services.my_batch_stats_service import get_batch_stats, list_assigned_batches


class MyBatchStatsTests(unittest.TestCase):
    """覆盖批次列表、默认批次、指定批次与越权批次。"""

    def setUp(self):
        self.app = create_app("testing")
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.client = self.app.test_client()

        # SQLite 下 BigInteger 主键不自增，显式指定 ID
        self.admin = self._user(1, "ut_admin", ROLE_ADMIN)
        self.op_a = self._user(2, "ut_op_a", ROLE_OPERATOR)
        self.op_b = self._user(3, "ut_op_b", ROLE_OPERATOR)

        # 批次 10：A 有任务；批次 20：A 有任务；批次 30（全系统最新）：只有 B
        self._batch(10, "B10", "淘宝.xlsx")
        self._batch(20, "B20", "京东.xlsx")
        self._batch(30, "B30", "最新.xlsx")
        self._batch(40, "B40", "失败.xlsx", status="failed")

        task_id = 100
        plan = [
            (10, self.op_a.id, TASK_STATUS_PENDING, 2),
            (10, self.op_a.id, TASK_STATUS_REVIEW, 3),
            (20, self.op_a.id, TASK_STATUS_PENDING, 1),
            (20, self.op_a.id, TASK_STATUS_REJECTED, 1),
            (20, self.op_a.id, TASK_STATUS_REVIEW, 2),
            (20, self.op_a.id, TASK_STATUS_APPROVED, 4),
            (30, self.op_b.id, TASK_STATUS_PENDING, 5),
            (40, self.op_a.id, TASK_STATUS_PENDING, 1),
        ]
        for batch_id, assignee_id, status, count in plan:
            for _ in range(count):
                task_id += 1
                db.session.add(
                    ClassificationTask(
                        id=task_id,
                        batch_id=batch_id,
                        product_id=f"P{task_id}",
                        product_name=f"商品{task_id}",
                        platform="淘宝",
                        status=status,
                        assignee_id=assignee_id,
                    )
                )
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def _user(self, uid: int, username: str, role: str) -> User:
        user = User(id=uid, username=username, role=role, is_active=True)
        user.set_password("x")
        db.session.add(user)
        db.session.commit()
        return user

    def _batch(self, bid: int, batch_no: str, file_name: str, status: str = "completed"):
        db.session.add(
            ImportBatch(
                id=bid,
                batch_no=batch_no,
                file_name=file_name,
                file_path="-",
                status=status,
                uploaded_by=self.admin.id,
            )
        )
        db.session.commit()

    def _headers(self, user: User) -> dict:
        token = create_access_token(identity=str(user.id))
        return {"Authorization": f"Bearer {token}"}

    # ---------- 服务层 ----------

    def test_list_assigned_batches_only_own_completed_desc(self):
        """只列含自己任务的已完成批次，按 ID 倒序。"""
        items = list_assigned_batches(self.op_a.id)
        self.assertEqual([i["id"] for i in items], [20, 10])
        self.assertEqual(items[0]["batch_no"], "B20")
        self.assertEqual(items[0]["file_name"], "京东.xlsx")

    def test_default_stats_use_latest_own_batch_not_global_latest(self):
        """不传批次时取自己最近被分配的批次，而非全系统最新批次。"""
        stats = get_batch_stats(self.op_a.id)
        self.assertEqual(stats["batch_id"], 20)
        self.assertEqual(stats["batch_no"], "B20")
        self.assertEqual(stats["total"], 8)
        self.assertEqual(stats["pending"], 2)
        self.assertEqual(stats["submitted"], 2)
        self.assertEqual(stats["approved"], 4)

    def test_stats_for_specified_batch(self):
        """指定批次时按该批次统计。"""
        stats = get_batch_stats(self.op_a.id, 10)
        self.assertEqual(stats["batch_id"], 10)
        self.assertEqual(stats["total"], 5)
        self.assertEqual(stats["pending"], 2)
        self.assertEqual(stats["submitted"], 3)
        self.assertEqual(stats["approved"], 0)

    def test_stats_for_batch_not_assigned_returns_zero(self):
        """传入没有自己任务的批次：返回 0，不泄露他人数据。"""
        stats = get_batch_stats(self.op_a.id, 30)
        self.assertEqual(stats["total"], 0)
        self.assertEqual(stats["pending"], 0)
        self.assertIsNone(stats["batch_id"])

    def test_no_assigned_batches_returns_empty(self):
        """从未被分配任务的操作员：列表为空，统计为 0。"""
        op_c = self._user(4, "ut_op_c", ROLE_OPERATOR)
        self.assertEqual(list_assigned_batches(op_c.id), [])
        stats = get_batch_stats(op_c.id)
        self.assertIsNone(stats["batch_id"])
        self.assertEqual(stats["total"], 0)

    # ---------- API ----------

    def test_api_my_batches(self):
        resp = self.client.get("/api/tasks/my/batches", headers=self._headers(self.op_a))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual([i["id"] for i in resp.get_json()["data"]], [20, 10])

    def test_api_my_stats_with_batch_id(self):
        resp = self.client.get(
            "/api/tasks/my/stats?batch_id=10", headers=self._headers(self.op_a)
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()["data"]
        self.assertEqual(data["batch_id"], 10)
        self.assertEqual(data["total"], 5)

    def test_api_my_stats_invalid_batch_id_returns_zero(self):
        """非数字 batch_id 视为未指定以外的无效值，返回 0。"""
        resp = self.client.get(
            "/api/tasks/my/stats?batch_id=abc", headers=self._headers(self.op_a)
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["data"]["total"], 0)

    def test_api_my_batches_admin_forbidden(self):
        resp = self.client.get("/api/tasks/my/batches", headers=self._headers(self.admin))
        self.assertEqual(resp.status_code, 403)


if __name__ == "__main__":
    unittest.main()
