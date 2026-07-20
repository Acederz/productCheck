"""操作与审计日志模型。"""

from datetime import datetime

from app.extensions import db


class OperationLog(db.Model):
    """通用操作日志。"""

    __tablename__ = "operation_logs"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey("users.id"), nullable=True)
    action = db.Column(db.String(64), nullable=False)
    target_type = db.Column(db.String(64), nullable=True)
    target_id = db.Column(db.BigInteger, nullable=True)
    detail_json = db.Column(db.JSON, nullable=True)
    ip = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class FieldChangeLog(db.Model):
    """字段级变更日志。"""

    __tablename__ = "field_change_logs"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    task_id = db.Column(db.BigInteger, db.ForeignKey("classification_tasks.id"), nullable=False)
    field_name = db.Column(db.String(64), nullable=False)
    old_value = db.Column(db.Text, nullable=True)
    new_value = db.Column(db.Text, nullable=True)
    reason = db.Column(db.Text, nullable=True)
    operator_id = db.Column(db.BigInteger, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class AssignmentLog(db.Model):
    """任务分配记录。"""

    __tablename__ = "assignment_logs"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    task_id = db.Column(db.BigInteger, db.ForeignKey("classification_tasks.id"), nullable=False)
    from_user_id = db.Column(db.BigInteger, nullable=True)
    to_user_id = db.Column(db.BigInteger, nullable=True)
    operator_id = db.Column(db.BigInteger, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class ReviewLog(db.Model):
    """审核记录。"""

    __tablename__ = "review_logs"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    task_id = db.Column(db.BigInteger, db.ForeignKey("classification_tasks.id"), nullable=False)
    action = db.Column(db.String(32), nullable=False)  # approve/reject/withdraw
    reason = db.Column(db.Text, nullable=True)
    operator_id = db.Column(db.BigInteger, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
