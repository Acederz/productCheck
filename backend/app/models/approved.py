"""审核通过后的正式数据模型。"""

from datetime import datetime

from app.extensions import db


class ApprovedProduct(db.Model):
    """正式商品数据（宝贝ID 唯一）。"""

    __tablename__ = "approved_products"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    product_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    row_no = db.Column(db.Integer, nullable=True)
    main_image = db.Column(db.Text, nullable=True)
    product_name = db.Column(db.String(500), nullable=False)
    brand = db.Column(db.String(128), nullable=True)
    is_operating = db.Column(db.String(16), nullable=True)
    category_large = db.Column(db.String(128), nullable=True)
    category_segment = db.Column(db.JSON, nullable=True)
    category_type = db.Column(db.String(128), nullable=True)
    material_main = db.Column(db.String(128), nullable=True)
    material_aux = db.Column(db.String(128), nullable=True)
    packaging = db.Column(db.String(128), nullable=True)
    size = db.Column(db.String(128), nullable=True)
    roll_count = db.Column(db.String(128), nullable=True)
    total_count = db.Column(db.String(128), nullable=True)
    product_attr = db.Column(db.Text, nullable=True)
    desc_images = db.Column(db.JSON, nullable=True)
    product_url = db.Column(db.Text, nullable=True)
    platform = db.Column(db.String(64), nullable=False)
    source_task_id = db.Column(db.BigInteger, nullable=True)
    version = db.Column(db.Integer, nullable=False, default=1)
    approved_by = db.Column(db.BigInteger, db.ForeignKey("users.id"), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ApprovedProductHistory(db.Model):
    """正式数据历史版本。"""

    __tablename__ = "approved_product_history"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    approved_product_id = db.Column(
        db.BigInteger, db.ForeignKey("approved_products.id"), nullable=False
    )
    version = db.Column(db.Integer, nullable=False)
    snapshot_json = db.Column(db.JSON, nullable=False)
    replaced_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    replaced_by_task_id = db.Column(db.BigInteger, nullable=True)
