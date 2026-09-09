"""无需填写字段规则模型。"""

from datetime import datetime

from app.extensions import db


class SkipFieldRuleVersion(db.Model):
    """无需填写字段规则版本。"""

    __tablename__ = "skip_field_rule_versions"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    version_no = db.Column(db.String(32), nullable=False, unique=True)
    remark = db.Column(db.String(255), nullable=True)
    created_by = db.Column(db.BigInteger, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class SkipFieldRule(db.Model):
    """按大类禁用的字段列表。"""

    __tablename__ = "skip_field_rules"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    version_id = db.Column(
        db.BigInteger, db.ForeignKey("skip_field_rule_versions.id"), nullable=False
    )
    category_large = db.Column(db.String(128), nullable=False, index=True)
    disabled_fields = db.Column(db.JSON, nullable=False, default=list)  # 中文列名
    is_active = db.Column(db.Boolean, nullable=False, default=True)
