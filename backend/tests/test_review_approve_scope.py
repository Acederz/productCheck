"""审核中心按范围批量通过单测。"""
import json
import sys
import unittest
from pathlib import Path

from flask_jwt_extended import create_access_token

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from app.constants import (
    ROLE_ADMIN,
    ROLE_OPERATOR,
    TASK_STATUS_APPROVED,
    TASK_STATUS_REVIEW,
)
from app.extensions import db
from app.models.approved import ApprovedProduct, ApprovedProductHistory
from app.models.log import ReviewLog
from app.models.task import ClassificationTask
from app.models.user import User
from app.services.review_service import ReviewService

UT_PREFIX = "UT_AS_"


class ReviewApproveScopeTests(unittest.TestCase):
    """按范围统计与批量通过 API。"""

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()
        cls.ctx = cls.app.app_context()
        cls.ctx.push()
        cls._cleanup_ut()

    @classmethod
    def tearDownClass(cls):
        cls._cleanup_ut()
        cls.ctx.pop()

    @classmethod
    def _cleanup_ut(cls):
        db.session.rollback()
        tasks = ClassificationTask.query.filter(
            ClassificationTask.product_id.like(f"{UT_PREFIX}%")
        ).all()
        task_ids = [t.id for t in tasks]
        if task_ids:
            ReviewLog.query.filter(ReviewLog.task_id.in_(task_ids)).delete(
                synchronize_session=False
            )
        for pid in [t.product_id for t in tasks]:
            ap = ApprovedProduct.query.filter_by(product_id=pid).first()
            if ap:
                ApprovedProductHistory.query.filter_by(
                    approved_product_id=ap.id
                ).delete(synchronize_session=False)
                db.session.delete(ap)
        for task in tasks:
            db.session.delete(task)
        users = User.query.filter(User.username.like(f"{UT_PREFIX}%")).all()
        for user in users:
            db.session.delete(user)
        db.session.commit()

    def setUp(self):
        self._cleanup_ut()

    def tearDown(self):
        db.session.rollback()
        self._cleanup_ut()

    def _admin_headers(self):
        admin = User.query.filter_by(role=ROLE_ADMIN, is_active=True).first()
        self.assertIsNotNone(admin)
        token = create_access_token(identity=str(admin.id))
        return {"Authorization": f"Bearer {token}"}

    def _admin_user(self) -> User:
        admin = User.query.filter_by(role=ROLE_ADMIN, is_active=True).first()
        self.assertIsNotNone(admin)
        return admin

    def _operator_headers(self):
        op_name = f"{UT_PREFIX}op"
        op = User(username=op_name, role=ROLE_OPERATOR, is_active=True)
        op.set_password("OpPass12")
        db.session.add(op)
        db.session.commit()
        token = create_access_token(identity=str(op.id))
        return {"Authorization": f"Bearer {token}"}

    def _scope_count(self, scope: str, **query) -> int:
        params = {"scope": scope, **query}
        resp = self.client.get(
            "/api/reviews/approve-scope-count",
            query_string=params,
            headers=self._admin_headers(),
        )
        self.assertEqual(resp.status_code, 200)
        return json.loads(resp.data)["data"]["count"]

    def _pending_review_count(self) -> int:
        """与 scope=all 统计口径一致的待审核总数。"""
        return ClassificationTask.query.filter_by(status=TASK_STATUS_REVIEW).count()

    def _make_review_task(
        self,
        *,
        platform: str = "淘宝",
        tag: str = "x",
        product_name: str | None = None,
    ) -> ClassificationTask:
        pid = f"{UT_PREFIX}{platform}_{tag}"
        name = product_name if product_name is not None else f"{UT_PREFIX}name_{tag}"
        t = ClassificationTask(
            product_id=pid,
            product_name=name,
            platform=platform,
            status=TASK_STATUS_REVIEW,
        )
        db.session.add(t)
        db.session.commit()
        return t

    def test_count_all_ignores_filters(self):
        self._make_review_task(platform="淘宝", tag="ca1")
        self._make_review_task(platform="京东", tag="ca2")
        expected_all = self._pending_review_count()
        self.assertEqual(self._scope_count("all"), expected_all)
        self.assertEqual(self._scope_count("all", platform="淘宝"), expected_all)
        self.assertEqual(
            self._scope_count("filtered", keyword=f"{UT_PREFIX}name_ca1"),
            1,
        )

    def test_count_filtered(self):
        tag = "cf_plat"
        self._make_review_task(platform="淘宝", tag=f"{tag}_tb")
        self._make_review_task(platform="京东", tag=f"{tag}_jd")
        self.assertEqual(
            self._scope_count(
                "filtered",
                platform="淘宝",
                keyword=f"{UT_PREFIX}name_{tag}_tb",
            ),
            1,
        )
        self.assertEqual(
            self._scope_count(
                "filtered",
                platform="京东",
                keyword=f"{UT_PREFIX}name_{tag}_jd",
            ),
            1,
        )

    def test_count_zero(self):
        self.assertEqual(
            self._scope_count("filtered", keyword=f"{UT_PREFIX}no_match_xyz"),
            0,
        )

    def test_approve_scope_filtered(self):
        """HTTP：仅用 UT 专属 keyword 命中单条，避免误伤共享库其它待审核。"""
        tag = "apf"
        kw = f"{UT_PREFIX}approve_kw_{tag}"
        tb = self._make_review_task(
            platform="淘宝", tag=f"{tag}_tb", product_name=f"{kw}_tb"
        )
        jd = self._make_review_task(
            platform="京东", tag=f"{tag}_jd", product_name=f"{kw}_jd_other"
        )
        expected = 1
        resp = self.client.post(
            "/api/reviews/approve-scope",
            headers={**self._admin_headers(), "Content-Type": "application/json"},
            data=json.dumps(
                {
                    "scope": "filtered",
                    "filters": {"keyword": f"{kw}_tb"},
                }
            ),
        )
        self.assertEqual(resp.status_code, 200)
        body = json.loads(resp.data)
        self.assertEqual(body["data"]["success_count"], expected)
        self.assertEqual(body["data"]["total_matched"], expected)
        db.session.refresh(tb)
        db.session.refresh(jd)
        self.assertEqual(tb.status, TASK_STATUS_APPROVED)
        self.assertEqual(jd.status, TASK_STATUS_REVIEW)

    def test_approve_by_scope_all_path_service(self):
        """不调用 POST scope=all；仅对显式 UT 任务 ID 走 approve_by_scope 全量路径。"""
        t1 = self._make_review_task(platform="淘宝", tag="svc_a1")
        t2 = self._make_review_task(platform="京东", tag="svc_a2")
        admin = self._admin_user()
        svc = ReviewService()
        result = svc.approve_by_scope(
            [t1.id, t2.id],
            admin.id,
            scope="all",
            filters=None,
        )
        self.assertEqual(result["success_count"], 2)
        self.assertEqual(result["total_matched"], 2)
        self.assertEqual(result["skipped_count"], 0)
        db.session.refresh(t1)
        db.session.refresh(t2)
        self.assertEqual(t1.status, TASK_STATUS_APPROVED)
        self.assertEqual(t2.status, TASK_STATUS_APPROVED)

    def test_approve_scope_filtered_http_unique_keyword(self):
        """HTTP filtered：同一 UT keyword 命中多条，仍不触及非 UT 数据。"""
        tag = "apf_multi"
        kw = f"{UT_PREFIX}batch_kw_{tag}"
        t1 = self._make_review_task(
            platform="淘宝", tag=f"{tag}_1", product_name=f"{kw}_1"
        )
        t2 = self._make_review_task(
            platform="京东", tag=f"{tag}_2", product_name=f"{kw}_2"
        )
        expected = 2
        resp = self.client.post(
            "/api/reviews/approve-scope",
            headers={**self._admin_headers(), "Content-Type": "application/json"},
            data=json.dumps(
                {
                    "scope": "filtered",
                    "filters": {"keyword": kw},
                }
            ),
        )
        self.assertEqual(resp.status_code, 200)
        body = json.loads(resp.data)
        self.assertEqual(body["data"]["success_count"], expected)
        self.assertEqual(body["data"]["total_matched"], expected)
        db.session.refresh(t1)
        db.session.refresh(t2)
        self.assertEqual(t1.status, TASK_STATUS_APPROVED)
        self.assertEqual(t2.status, TASK_STATUS_APPROVED)

    def test_operator_forbidden(self):
        resp = self.client.get(
            "/api/reviews/approve-scope-count",
            query_string={"scope": "all"},
            headers=self._operator_headers(),
        )
        self.assertEqual(resp.status_code, 403)

    def test_operator_forbidden_post_approve_scope(self):
        resp = self.client.post(
            "/api/reviews/approve-scope",
            headers={
                **self._operator_headers(),
                "Content-Type": "application/json",
            },
            data=json.dumps({"scope": "filtered", "filters": {"keyword": UT_PREFIX}}),
        )
        self.assertEqual(resp.status_code, 403)

    def test_invalid_scope(self):
        resp = self.client.get(
            "/api/reviews/approve-scope-count",
            query_string={"scope": "bogus"},
            headers=self._admin_headers(),
        )
        self.assertEqual(resp.status_code, 400)

    def test_post_invalid_scope(self):
        resp = self.client.post(
            "/api/reviews/approve-scope",
            headers={**self._admin_headers(), "Content-Type": "application/json"},
            data=json.dumps({"scope": "bogus"}),
        )
        self.assertEqual(resp.status_code, 400)

    def test_post_missing_scope(self):
        resp = self.client.post(
            "/api/reviews/approve-scope",
            headers={**self._admin_headers(), "Content-Type": "application/json"},
            data=json.dumps({}),
        )
        self.assertEqual(resp.status_code, 400)


if __name__ == "__main__":
    unittest.main()
