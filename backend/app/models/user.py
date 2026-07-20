"""用户与系统配置模型。"""

from datetime import datetime

import bcrypt

from app.constants import ROLE_ADMIN, ROLE_OPERATOR
from app.extensions import db


class User(db.Model):
    """系统用户。"""

    __tablename__ = "users"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(
        db.Enum(ROLE_ADMIN, ROLE_OPERATOR, name="user_role"),
        nullable=False,
        default=ROLE_OPERATOR,
    )
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def set_password(self, raw_password: str) -> None:
        """设置密码哈希。"""
        self.password_hash = bcrypt.hashpw(
            raw_password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

    def check_password(self, raw_password: str) -> bool:
        """校验密码。"""
        return bcrypt.checkpw(
            raw_password.encode("utf-8"), self.password_hash.encode("utf-8")
        )

    def to_dict(self) -> dict:
        """序列化为字典（不含密码）。"""
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class SystemConfig(db.Model):
    """系统配置项。"""

    __tablename__ = "system_config"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    config_key = db.Column(db.String(64), unique=True, nullable=False)
    config_value = db.Column(db.Text, nullable=True)
    updated_by = db.Column(db.BigInteger, db.ForeignKey("users.id"), nullable=True)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
