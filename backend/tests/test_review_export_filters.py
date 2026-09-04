"""审核/导出多选筛选 — ExportService.filter_tasks 与审核 API。"""
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
    TASK_STATUS_PENDING,
    TASK_STATUS_REVIEW,
)
from app.extensions import db
from app.models.approved import ApprovedProduct
from app.models.task import ClassificationTask, ImportBatch
from app.models.user import User
from app.services.export_service import ExportService

UT_REF_PREFIX = "UT_REF_"


class ReviewExportFilterTests(unittest.TestCase):
    """ExportService.filter_tasks 多选筛选行为。"""

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.ctx = cls.app.app_context()
        cls.ctx.push()
        cls.export_service = ExportService(Path(cls.app.config["EXPORT_FOLDER"]))
        cls._cleanup_ut_ref_data()

    @classmethod
    def tearDownClass(cls):
        cls._cleanup_ut_ref_data()
        cls.ctx.pop()

    @classmethod
    def _cleanup_ut_ref_data(cls):
        """清理 UT_REF_ 前缀测试用户、批次、任务与正式库记录。"""
        db.session.rollback()
        approved = ApprovedProduct.query.filter(
            ApprovedProduct.product_id.like(f"{UT_REF_PREFIX}%")
        ).all()
        for item in approved:
            db.session.delete(item)
        tasks = ClassificationTask.query.filter(
            ClassificationTask.product_id.like(f"{UT_REF_PREFIX}%")
        ).all()
        for task in tasks:
            db.session.delete(task)
        batches = ImportBatch.query.filter(
            ImportBatch.batch_no.like(f"{UT_REF_PREFIX}%")
        ).all()
        for batch in batches:
            db.session.delete(batch)
        users = User.query.filter(User.username.like(f"{UT_REF_PREFIX}%")).all()
        for user in users:
            db.session.delete(user)
        db.session.commit()

    def tearDown(self):
        db.session.rollback()
        self._cleanup_ut_ref_data()

    def _make_batch(self) -> ImportBatch:
        batch = ImportBatch(
            batch_no=f"{UT_REF_PREFIX}batch",
            file_name="t.xlsx",
            file_path="",
            total_rows=1,
            success_rows=1,
            fail_rows=0,
            status="completed",
            uploaded_by=1,
        )
        db.session.add(batch)
        db.session.flush()
        return batch

    def _make_operator(self, suffix: str) -> User:
        user = User(
            username=f"{UT_REF_PREFIX}op_{suffix}",
            role=ROLE_OPERATOR,
            is_active=True,
        )
        user.set_password("ut_test_pass")
        db.session.add(user)
        db.session.flush()
        return user

    def _make_task(
        self,
        batch_id: int,
        suffix: str,
        *,
        status=TASK_STATUS_PENDING,
        platform="淘宝",
        assignee_id=None,
    ) -> ClassificationTask:
        task = ClassificationTask(
            batch_id=batch_id,
            product_id=f"{UT_REF_PREFIX}{suffix}",
            product_name="测试商品",
            platform=platform,
            status=status,
            assignee_id=assignee_id,
        )
        db.session.add(task)
        db.session.flush()
        return task

    def _ut_ref_ids(self, query):
        """从查询结果中提取 UT_REF_ 测试任务 ID 集合。"""
        return {
            t.id
            for t in query.all()
            if t.product_id.startswith(UT_REF_PREFIX)
        }

    def test_filter_tasks_status_multi(self):
        """status 逗号多选仅返回合法状态并集。"""
        batch = self._make_batch()
        t_pending = self._make_task(batch.id, "st_pending", status=TASK_STATUS_PENDING)
        t_review = self._make_task(batch.id, "st_review", status=TASK_STATUS_REVIEW)
        t_approved = self._make_task(batch.id, "st_approved", status=TASK_STATUS_APPROVED)
        db.session.commit()

        query = self.export_service.filter_tasks(status="待处理,待审核")
        ids = self._ut_ref_ids(query)
        self.assertEqual(ids, {t_pending.id, t_review.id})
        self.assertNotIn(t_approved.id, ids)

    def test_filter_tasks_platform_multi(self):
        """platform 逗号多选返回平台并集。"""
        batch = self._make_batch()
        t_tb = self._make_task(batch.id, "pl_tb", platform="淘宝")
        t_jd = self._make_task(batch.id, "pl_jd", platform="京东")
        t_other = self._make_task(batch.id, "pl_other", platform="消费者洞察淘宝")
        db.session.commit()

        query = self.export_service.filter_tasks(platform="淘宝,京东")
        ids = self._ut_ref_ids(query)
        self.assertEqual(ids, {t_tb.id, t_jd.id})
        self.assertNotIn(t_other.id, ids)

    def test_filter_tasks_assignee_id_multi(self):
        """assignee_id 逗号多选返回负责人并集。"""
        batch = self._make_batch()
        op1 = self._make_operator("a")
        op2 = self._make_operator("b")
        op3 = self._make_operator("c")
        t1 = self._make_task(batch.id, "asg_1", assignee_id=op1.id)
        t2 = self._make_task(batch.id, "asg_2", assignee_id=op2.id)
        t3 = self._make_task(batch.id, "asg_3", assignee_id=op3.id)
        db.session.commit()

        query = self.export_service.filter_tasks(assignee_id=f"{op1.id},{op2.id}")
        ids = self._ut_ref_ids(query)
        self.assertEqual(ids, {t1.id, t2.id})
        self.assertNotIn(t3.id, ids)

    def test_filter_tasks_no_filter_params(self):
        """无 status/platform/assignee_id 参数时不过滤上述字段。"""
        batch = self._make_batch()
        op = self._make_operator("all")
        tasks = [
            self._make_task(
                batch.id,
                "nf_1",
                status=TASK_STATUS_PENDING,
                platform="淘宝",
                assignee_id=op.id,
            ),
            self._make_task(
                batch.id,
                "nf_2",
                status=TASK_STATUS_APPROVED,
                platform="京东",
                assignee_id=None,
            ),
        ]
        db.session.commit()

        query = self.export_service.filter_tasks()
        ids = self._ut_ref_ids(query)
        self.assertEqual(ids, {t.id for t in tasks})

    def test_filter_tasks_invalid_status_typo(self):
        """status 全为非法值时返回空结果，而非全量。"""
        batch = self._make_batch()
        self._make_task(batch.id, "inv_st", status=TASK_STATUS_PENDING)
        db.session.commit()

        query = self.export_service.filter_tasks(status="不存在的状态,typo")
        ids = self._ut_ref_ids(query)
        self.assertEqual(ids, set())

    def test_filter_tasks_status_platform_assignee_combo(self):
        """status + platform + assignee_id 组合筛选取交集。"""
        batch = self._make_batch()
        op1 = self._make_operator("combo_a")
        op2 = self._make_operator("combo_b")
        hit = self._make_task(
            batch.id,
            "combo_hit",
            status=TASK_STATUS_PENDING,
            platform="淘宝",
            assignee_id=op1.id,
        )
        self._make_task(
            batch.id,
            "combo_wrong_status",
            status=TASK_STATUS_APPROVED,
            platform="淘宝",
            assignee_id=op1.id,
        )
        self._make_task(
            batch.id,
            "combo_wrong_platform",
            status=TASK_STATUS_PENDING,
            platform="京东",
            assignee_id=op1.id,
        )
        self._make_task(
            batch.id,
            "combo_wrong_assignee",
            status=TASK_STATUS_PENDING,
            platform="淘宝",
            assignee_id=op2.id,
        )
        db.session.commit()

        query = self.export_service.filter_tasks(
            status=TASK_STATUS_PENDING,
            platform="淘宝",
            assignee_id=str(op1.id),
        )
        ids = self._ut_ref_ids(query)
        self.assertEqual(ids, {hit.id})

    def _make_approved(self, suffix: str, *, platform="淘宝") -> ApprovedProduct:
        item = ApprovedProduct(
            product_id=f"{UT_REF_PREFIX}ap_{suffix}",
            product_name="测试正式库",
            platform=platform,
        )
        db.session.add(item)
        db.session.flush()
        return item

    def test_filter_approved_platform_multi(self):
        """filter_approved 支持 platform 逗号多选。"""
        t_tb = self._make_approved("fa_tb", platform="淘宝")
        t_jd = self._make_approved("fa_jd", platform="京东")
        self._make_approved("fa_other", platform="消费者洞察淘宝")
        db.session.commit()

        query = self.export_service.filter_approved(platform="淘宝,京东")
        ids = {
            p.id
            for p in query.all()
            if p.product_id.startswith(UT_REF_PREFIX)
        }
        self.assertEqual(ids, {t_tb.id, t_jd.id})


class ReviewAssigneeFilterApiTests(unittest.TestCase):
    """GET /api/reviews/pending 操作员多选筛选。"""

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()
        cls.ctx = cls.app.app_context()
        cls.ctx.push()
        ReviewExportFilterTests._cleanup_ut_ref_data()

    @classmethod
    def tearDownClass(cls):
        ReviewExportFilterTests._cleanup_ut_ref_data()
        cls.ctx.pop()

    def tearDown(self):
        db.session.rollback()
        ReviewExportFilterTests._cleanup_ut_ref_data()

    def _admin_token(self) -> str:
        admin = User.query.filter_by(role=ROLE_ADMIN, is_active=True).first()
        self.assertIsNotNone(admin, "需要至少一名启用中的管理员账号")
        return create_access_token(identity=str(admin.id))

    def test_pending_reviews_assignee_id_multi(self):
        """待审核列表支持 assignee_id 逗号多选。"""
        helper = ReviewExportFilterTests()
        batch = helper._make_batch()
        op1 = helper._make_operator("api_a")
        op2 = helper._make_operator("api_b")
        op3 = helper._make_operator("api_c")
        t1 = helper._make_task(
            batch.id,
            "rev_1",
            status=TASK_STATUS_REVIEW,
            assignee_id=op1.id,
        )
        t2 = helper._make_task(
            batch.id,
            "rev_2",
            status=TASK_STATUS_REVIEW,
            assignee_id=op2.id,
        )
        helper._make_task(
            batch.id,
            "rev_3",
            status=TASK_STATUS_REVIEW,
            assignee_id=op3.id,
        )
        db.session.commit()

        resp = self.client.get(
            f"/api/reviews/pending?assignee_id={op1.id},{op2.id}",
            headers={"Authorization": f"Bearer {self._admin_token()}"},
        )
        self.assertEqual(resp.status_code, 200)
        body = json.loads(resp.data)
        self.assertEqual(body["code"], 200)
        items = body["data"]["items"]
        returned_ids = {item["id"] for item in items if item["product_id"].startswith(UT_REF_PREFIX)}
        self.assertEqual(returned_ids, {t1.id, t2.id})
        for item in items:
            if item["product_id"].startswith(UT_REF_PREFIX):
                self.assertIn(item["assignee_id"], (op1.id, op2.id))


if __name__ == "__main__":
    unittest.main()
