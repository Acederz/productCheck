"""按导入批次删除 — ImportService 单测与 DELETE API 冒烟。"""
import json
import sys
import unittest
from pathlib import Path

from flask_jwt_extended import create_access_token

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from app.constants import ROLE_ADMIN, ROLE_OPERATOR
from app.extensions import db
from app.models.user import User
from app.models.approved import ApprovedProduct, ApprovedProductHistory
from app.models.log import AssignmentLog, FieldChangeLog, ReviewLog
from app.models.task import ClassificationTask, ImportBatch, TaskDraft
from app.services.import_service import ImportService

UT_DEL_PREFIX = "UT_DEL_"


class DeleteBatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.ctx = cls.app.app_context()
        cls.ctx.push()
        cls._cleanup_ut_del_batches()

    @classmethod
    def tearDownClass(cls):
        cls._cleanup_ut_del_batches()
        cls.ctx.pop()

    @classmethod
    def _cleanup_ut_del_batches(cls):
        """清理 UT_DEL_ 前缀测试批次及关联数据，避免重复运行污染。"""
        db.session.rollback()
        batches = ImportBatch.query.filter(
            ImportBatch.batch_no.like(f"{UT_DEL_PREFIX}%")
        ).all()
        for batch in batches:
            task_ids = [
                t.id
                for t in ClassificationTask.query.filter_by(batch_id=batch.id).all()
            ]
            if task_ids:
                TaskDraft.query.filter(TaskDraft.task_id.in_(task_ids)).delete(
                    synchronize_session=False
                )
                FieldChangeLog.query.filter(FieldChangeLog.task_id.in_(task_ids)).delete(
                    synchronize_session=False
                )
                AssignmentLog.query.filter(AssignmentLog.task_id.in_(task_ids)).delete(
                    synchronize_session=False
                )
                ReviewLog.query.filter(ReviewLog.task_id.in_(task_ids)).delete(
                    synchronize_session=False
                )
                ClassificationTask.query.filter(
                    ClassificationTask.id.in_(task_ids)
                ).delete(synchronize_session=False)
            approved_ids = [
                a.id
                for a in ApprovedProduct.query.filter_by(batch_id=batch.id).all()
            ]
            if approved_ids:
                ApprovedProductHistory.query.filter(
                    ApprovedProductHistory.approved_product_id.in_(approved_ids)
                ).delete(synchronize_session=False)
                ApprovedProduct.query.filter(ApprovedProduct.id.in_(approved_ids)).delete(
                    synchronize_session=False
                )
            db.session.delete(batch)
        # 清理测试中可能残留的正式库商品（batch_id 指向其他批次）
        for pid in ("P_TASK_ONLY", "P_APPR_SAME", "P_OVERWRITE"):
            ap = ApprovedProduct.query.filter_by(product_id=pid).first()
            if ap:
                ApprovedProductHistory.query.filter_by(
                    approved_product_id=ap.id
                ).delete(synchronize_session=False)
                db.session.delete(ap)
        db.session.commit()

    def tearDown(self):
        """单测结束后回滚异常事务并清理残留。"""
        db.session.rollback()
        self._cleanup_ut_del_batches()

    def _make_batch(self, suffix: str, status: str = "completed") -> ImportBatch:
        batch = ImportBatch(
            batch_no=f"{UT_DEL_PREFIX}{suffix}",
            file_name="t.xlsx",
            file_path="",
            total_rows=1,
            success_rows=1,
            fail_rows=0,
            status=status,
            uploaded_by=1,
        )
        db.session.add(batch)
        db.session.flush()
        return batch

    def _make_task(self, batch_id: int, product_id: str) -> ClassificationTask:
        task = ClassificationTask(
            batch_id=batch_id,
            product_id=product_id,
            product_name="n",
            platform="淘宝",
        )
        db.session.add(task)
        db.session.flush()
        return task

    def test_delete_tasks_only(self):
        batch = self._make_batch("tasks_only")
        task = self._make_task(batch.id, "P_TASK_ONLY")
        db.session.add(TaskDraft(task_id=task.id, assignee_id=1, draft_json={"a": 1}))
        db.session.commit()
        bid = batch.id
        svc = ImportService(Path(self.app.config["UPLOAD_FOLDER"]))
        result = svc.delete_batch(bid, operator_id=1)
        self.assertEqual(result["deleted_tasks"], 1)
        self.assertEqual(result["deleted_approved"], 0)
        self.assertIsNone(ImportBatch.query.get(bid))
        self.assertEqual(ClassificationTask.query.filter_by(batch_id=bid).count(), 0)

    def test_delete_approved_same_batch(self):
        batch = self._make_batch("appr_same")
        task = self._make_task(batch.id, "P_APPR_SAME")
        ap = ApprovedProduct(
            product_id="P_APPR_SAME",
            product_name="n",
            platform="淘宝",
            source_task_id=task.id,
            batch_id=batch.id,
        )
        db.session.add(ap)
        db.session.flush()
        db.session.add(
            ApprovedProductHistory(
                approved_product_id=ap.id,
                version=1,
                snapshot_json={"product_id": "P_APPR_SAME"},
            )
        )
        db.session.commit()
        bid = batch.id
        result = ImportService(Path(self.app.config["UPLOAD_FOLDER"])).delete_batch(
            bid, operator_id=1
        )
        self.assertEqual(result["deleted_approved"], 1)
        self.assertIsNone(ApprovedProduct.query.filter_by(product_id="P_APPR_SAME").first())

    def test_keep_approved_overwritten_by_other_batch(self):
        batch_old = self._make_batch("appr_old")
        batch_new = self._make_batch("appr_new")
        self._make_task(batch_old.id, "P_OVERWRITE")
        ap = ApprovedProduct(
            product_id="P_OVERWRITE",
            product_name="n",
            platform="淘宝",
            batch_id=batch_new.id,  # 已被新批次覆盖
        )
        db.session.add(ap)
        db.session.commit()
        old_id = batch_old.id
        ImportService(Path(self.app.config["UPLOAD_FOLDER"])).delete_batch(
            old_id, operator_id=1
        )
        kept = ApprovedProduct.query.filter_by(product_id="P_OVERWRITE").first()
        self.assertIsNotNone(kept)
        self.assertEqual(kept.batch_id, batch_new.id)
        # 清理新批次与正式库，避免污染
        db.session.delete(kept)
        db.session.delete(batch_new)
        db.session.commit()

    def test_reject_processing(self):
        batch = self._make_batch("processing", status="processing")
        db.session.commit()
        bid = batch.id
        with self.assertRaises(ValueError) as ctx:
            ImportService(Path(self.app.config["UPLOAD_FOLDER"])).delete_batch(
                bid, operator_id=1
            )
        self.assertIn("导入中", str(ctx.exception))
        self.assertIsNotNone(ImportBatch.query.get(bid))
        db.session.delete(ImportBatch.query.get(bid))
        db.session.commit()


class DeleteBatchApiTests(unittest.TestCase):
    """DELETE /api/imports/<batch_id> API 级用例。"""

    _UT_OPERATOR = "ut_del_api_operator"

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()
        cls.ctx = cls.app.app_context()
        cls.ctx.push()

    @classmethod
    def tearDownClass(cls):
        op = User.query.filter_by(username=cls._UT_OPERATOR).first()
        if op:
            db.session.delete(op)
            db.session.commit()
        cls.ctx.pop()

    def _admin_token(self) -> str:
        admin = User.query.filter_by(role=ROLE_ADMIN, is_active=True).first()
        self.assertIsNotNone(admin, "需要至少一名启用中的管理员账号")
        return create_access_token(identity=str(admin.id))

    def _operator_token(self) -> str:
        op = User.query.filter_by(username=self._UT_OPERATOR).first()
        if not op:
            op = User(username=self._UT_OPERATOR, role=ROLE_OPERATOR, is_active=True)
            op.set_password("ut_test_pass")
            db.session.add(op)
            db.session.commit()
        return create_access_token(identity=str(op.id))

    def test_api_missing_batch_404(self):
        """不存在批次应返回 404。"""
        resp = self.client.delete(
            "/api/imports/999999999",
            headers={"Authorization": f"Bearer {self._admin_token()}"},
        )
        self.assertEqual(resp.status_code, 404)
        body = json.loads(resp.data)
        self.assertEqual(body["code"], 404)
        self.assertIn("不存在", body["message"])

    def test_api_non_admin_forbidden(self):
        """非管理员应返回 403。"""
        resp = self.client.delete(
            "/api/imports/1",
            headers={"Authorization": f"Bearer {self._operator_token()}"},
        )
        self.assertEqual(resp.status_code, 403)
        body = json.loads(resp.data)
        self.assertEqual(body["code"], 403)
        self.assertIn("管理员", body["message"])


if __name__ == "__main__":
    unittest.main()
