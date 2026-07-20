"""分类规则模型。"""

from datetime import datetime

from app.extensions import db


class ClassificationRuleVersion(db.Model):
    """分类规则版本。"""

    __tablename__ = "classification_rule_versions"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    version_no = db.Column(db.String(32), nullable=False, unique=True)
    remark = db.Column(db.String(255), nullable=True)
    created_by = db.Column(db.BigInteger, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class ClassificationRuleNode(db.Model):
    """主规则树节点（来自 Sheet「分类规则」）。"""

    __tablename__ = "classification_rule_nodes"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    version_id = db.Column(
        db.BigInteger, db.ForeignKey("classification_rule_versions.id"), nullable=False
    )
    category_large = db.Column(db.String(128), nullable=False)
    category_segment = db.Column(db.String(128), nullable=True)
    category_type = db.Column(db.String(128), nullable=True)
    material_main = db.Column(db.String(128), nullable=True)
    material_aux = db.Column(db.String(128), nullable=True)
    packaging = db.Column(db.String(128), nullable=True)
    size_option = db.Column(db.String(128), nullable=True)
    roll_input_mode = db.Column(db.String(8), nullable=True)  # 0/1
    total_input_mode = db.Column(db.String(8), nullable=True)  # 0/1
    is_active = db.Column(db.Boolean, nullable=False, default=True)


class ClassificationFieldRule(db.Model):
    """字段级补充规则（尺寸/卷数/总入数/辅材质/包装方式 Sheet）。"""

    __tablename__ = "classification_field_rules"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    version_id = db.Column(
        db.BigInteger, db.ForeignKey("classification_rule_versions.id"), nullable=False
    )
    field_name = db.Column(db.String(32), nullable=False, index=True)
    input_mode = db.Column(db.String(8), nullable=False)  # 0=文本, 1=下拉
    path_large = db.Column(db.String(128), nullable=True)
    path_segment = db.Column(db.String(128), nullable=True)
    path_type = db.Column(db.String(128), nullable=True)
    path_material_main = db.Column(db.String(128), nullable=True)
    path_material_aux = db.Column(db.String(128), nullable=True)
    path_packaging = db.Column(db.String(128), nullable=True)
    path_size = db.Column(db.String(128), nullable=True)
    path_roll = db.Column(db.String(128), nullable=True)
    option_value = db.Column(db.String(255), nullable=True)
    hint = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)


class ClassificationRuleChangeLog(db.Model):
    """规则变更审计。"""

    __tablename__ = "classification_rule_change_logs"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    rule_type = db.Column(db.String(32), nullable=False)
    rule_id = db.Column(db.BigInteger, nullable=True)
    action = db.Column(db.String(32), nullable=False)
    before_json = db.Column(db.JSON, nullable=True)
    after_json = db.Column(db.JSON, nullable=True)
    operator_id = db.Column(db.BigInteger, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
