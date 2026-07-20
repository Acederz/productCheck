"""审核通过与正式库写入服务。"""

from datetime import datetime

from app.constants import TASK_STATUS_APPROVED, TASK_STATUS_REVIEW
from app.extensions import db
from app.models.approved import ApprovedProduct, ApprovedProductHistory
from app.models.log import ReviewLog
from app.models.task import ClassificationTask
from app.services.operation_log_service import write_operation_log


class ReviewService:
    """审核业务逻辑。"""

    def _task_to_approved_dict(self, task: ClassificationTask) -> dict:
        """任务转正式库字段快照。"""
        return {
            "product_id": task.product_id,
            "row_no": task.row_no,
            "main_image": task.main_image,
            "product_name": task.product_name,
            "brand": task.brand,
            "is_operating": task.is_operating,
            "category_large": task.category_large,
            "category_segment": task.category_segment,
            "category_type": task.category_type,
            "material_main": task.material_main,
            "material_aux": task.material_aux,
            "packaging": task.packaging,
            "size": task.size,
            "roll_count": task.roll_count,
            "total_count": task.total_count,
            "product_attr": task.product_attr,
            "desc_images": task.desc_images,
            "product_url": task.product_url,
            "platform": task.platform,
        }

    def _write_approved(self, task: ClassificationTask, admin_id: int) -> None:
        """审核通过写入正式库（宝贝ID 唯一，覆盖保留历史）。"""
        existing = ApprovedProduct.query.filter_by(product_id=task.product_id).first()
        now = datetime.utcnow()
        snapshot = self._task_to_approved_dict(task)

        if existing:
            db.session.add(
                ApprovedProductHistory(
                    approved_product_id=existing.id,
                    version=existing.version,
                    snapshot_json={
                        "product_id": existing.product_id,
                        "product_name": existing.product_name,
                        "brand": existing.brand,
                        "is_operating": existing.is_operating,
                        "category_large": existing.category_large,
                        "category_segment": existing.category_segment,
                        "category_type": existing.category_type,
                        "material_main": existing.material_main,
                        "material_aux": existing.material_aux,
                        "packaging": existing.packaging,
                        "size": existing.size,
                        "roll_count": existing.roll_count,
                        "total_count": existing.total_count,
                        "product_attr": existing.product_attr,
                        "desc_images": existing.desc_images,
                        "product_url": existing.product_url,
                        "platform": existing.platform,
                        "version": existing.version,
                    },
                    replaced_by_task_id=task.id,
                )
            )
            for key, val in snapshot.items():
                setattr(existing, key, val)
            existing.version += 1
            existing.source_task_id = task.id
            existing.approved_by = admin_id
            existing.approved_at = now
            existing.updated_at = now
        else:
            approved = ApprovedProduct(
                **snapshot,
                source_task_id=task.id,
                version=1,
                approved_by=admin_id,
                approved_at=now,
            )
            db.session.add(approved)

    def approve_tasks(self, task_ids: list, admin_id: int) -> dict:
        """批量审核通过。"""
        tasks = ClassificationTask.query.filter(ClassificationTask.id.in_(task_ids)).all()
        success, skipped = [], []

        for task in tasks:
            if task.status != TASK_STATUS_REVIEW:
                skipped.append({"id": task.id, "reason": "仅待审核状态可通过"})
                continue

            self._write_approved(task, admin_id)
            task.status = TASK_STATUS_APPROVED
            task.reviewed_by = admin_id
            task.reviewed_at = datetime.utcnow()
            task.reject_reason = None

            db.session.add(
                ReviewLog(task_id=task.id, action="approve", operator_id=admin_id)
            )
            success.append(task.id)

        write_operation_log(admin_id, "approve_tasks", "task", None, {"task_ids": success})
        db.session.commit()
        return {"success_ids": success, "skipped": skipped}

    def reject_tasks(self, task_ids: list, admin_id: int, reason: str = "") -> dict:
        """批量驳回。"""
        from app.constants import TASK_STATUS_REJECTED

        tasks = ClassificationTask.query.filter(ClassificationTask.id.in_(task_ids)).all()
        success, skipped = [], []

        for task in tasks:
            if task.status != TASK_STATUS_REVIEW:
                skipped.append({"id": task.id, "reason": "仅待审核状态可驳回"})
                continue

            task.status = TASK_STATUS_REJECTED
            task.reviewed_by = admin_id
            task.reviewed_at = datetime.utcnow()
            task.reject_reason = reason or None

            db.session.add(
                ReviewLog(
                    task_id=task.id,
                    action="reject",
                    reason=reason,
                    operator_id=admin_id,
                )
            )
            success.append(task.id)

        write_operation_log(
            admin_id,
            "reject_tasks",
            "task",
            None,
            {"task_ids": success, "reason": reason},
        )
        db.session.commit()
        return {"success_ids": success, "skipped": skipped}
