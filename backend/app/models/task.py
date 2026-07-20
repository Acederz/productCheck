"""分类任务与导入批次模型。"""

from datetime import datetime

from app.constants import PLATFORMS, TASK_STATUS_UNASSIGNED, TASK_STATUSES
from app.extensions import db


class ImportBatch(db.Model):
    """Excel 导入批次。"""

    __tablename__ = "import_batches"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    batch_no = db.Column(db.String(32), unique=True, nullable=False, index=True)
    file_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    total_rows = db.Column(db.Integer, nullable=False, default=0)
    success_rows = db.Column(db.Integer, nullable=False, default=0)
    fail_rows = db.Column(db.Integer, nullable=False, default=0)
    error_report_path = db.Column(db.String(500), nullable=True)
    status = db.Column(
        db.Enum("processing", "completed", "failed", name="import_status"),
        nullable=False,
        default="processing",
    )
    uploaded_by = db.Column(db.BigInteger, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self) -> dict:
        """转为 API 字典。"""
        return {
            "id": self.id,
            "batch_no": self.batch_no,
            "file_name": self.file_name,
            "total_rows": self.total_rows,
            "success_rows": self.success_rows,
            "fail_rows": self.fail_rows,
            "has_error_report": bool(self.error_report_path),
            "status": self.status,
            "uploaded_by": self.uploaded_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ClassificationTask(db.Model):
    """待分类任务（Excel 每行一条）。"""

    __tablename__ = "classification_tasks"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    batch_id = db.Column(db.BigInteger, db.ForeignKey("import_batches.id"), nullable=True)
    row_no = db.Column(db.Integer, nullable=True)

    # 原始字段（9 个不可改 + 序号）
    product_id = db.Column(db.String(64), nullable=False, index=True)
    main_image = db.Column(db.Text, nullable=True)
    product_name = db.Column(db.String(500), nullable=False)
    brand = db.Column(db.String(128), nullable=True)
    product_attr = db.Column(db.Text, nullable=True)
    desc_images = db.Column(db.JSON, nullable=True)
    product_url = db.Column(db.Text, nullable=True)
    platform = db.Column(
        db.Enum(*PLATFORMS, name="platform_enum"),
        nullable=False,
        index=True,
    )

    # 可编辑分类字段
    is_operating = db.Column(db.String(16), nullable=True)
    category_large = db.Column(db.String(128), nullable=True)
    category_segment = db.Column(db.JSON, nullable=True)  # 区隔多选
    category_type = db.Column(db.String(128), nullable=True)
    material_main = db.Column(db.String(128), nullable=True)
    material_aux = db.Column(db.String(128), nullable=True)
    packaging = db.Column(db.String(128), nullable=True)
    size = db.Column(db.String(128), nullable=True)
    roll_count = db.Column(db.String(128), nullable=True)
    total_count = db.Column(db.String(128), nullable=True)

    # 流程字段
    status = db.Column(
        db.Enum(*TASK_STATUSES, name="task_status"),
        nullable=False,
        default=TASK_STATUS_UNASSIGNED,
        index=True,
    )
    assignee_id = db.Column(db.BigInteger, db.ForeignKey("users.id"), nullable=True, index=True)
    assigned_at = db.Column(db.DateTime, nullable=True)
    submitted_at = db.Column(db.DateTime, nullable=True)
    reviewed_by = db.Column(db.BigInteger, db.ForeignKey("users.id"), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    reject_reason = db.Column(db.Text, nullable=True)
    rule_snapshot_id = db.Column(db.BigInteger, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def to_dict(self) -> dict:
        """转为 API 字典。"""
        return {
            "id": self.id,
            "batch_id": self.batch_id,
            "row_no": self.row_no,
            "product_id": self.product_id,
            "main_image": self.main_image,
            "product_name": self.product_name,
            "brand": self.brand,
            "is_operating": self.is_operating,
            "category_large": self.category_large,
            "category_segment": self.category_segment or [],
            "category_type": self.category_type,
            "material_main": self.material_main,
            "material_aux": self.material_aux,
            "packaging": self.packaging,
            "size": self.size,
            "roll_count": self.roll_count,
            "total_count": self.total_count,
            "product_attr": self.product_attr,
            "desc_images": self.desc_images or [],
            "product_url": self.product_url,
            "platform": self.platform,
            "status": self.status,
            "assignee_id": self.assignee_id,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "reject_reason": self.reject_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class TaskDraft(db.Model):
    """操作员填写的服务端暂存。"""

    __tablename__ = "task_drafts"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    task_id = db.Column(
        db.BigInteger, db.ForeignKey("classification_tasks.id"), nullable=False
    )
    assignee_id = db.Column(db.BigInteger, db.ForeignKey("users.id"), nullable=False)
    draft_json = db.Column(db.JSON, nullable=False, default=dict)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        db.UniqueConstraint("task_id", "assignee_id", name="uk_task_assignee_draft"),
    )
