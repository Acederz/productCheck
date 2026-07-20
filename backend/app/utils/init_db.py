"""数据库初始化脚本。"""

from app.constants import ROLE_ADMIN
from app.extensions import db
from app.models import User
from app.models.user import SystemConfig


def init_database(app):
    """创建表并初始化默认数据。"""
    with app.app_context():
        db.create_all()

        # 默认管理员
        admin = User.query.filter_by(username=app.config["ADMIN_USERNAME"]).first()
        if not admin:
            admin = User(
                username=app.config["ADMIN_USERNAME"],
                role=ROLE_ADMIN,
                is_active=True,
            )
            admin.set_password(app.config["ADMIN_PASSWORD"])
            db.session.add(admin)

        # 默认系统配置
        if not SystemConfig.query.filter_by(config_key="operator_export_enabled").first():
            db.session.add(
                SystemConfig(
                    config_key="operator_export_enabled",
                    config_value="false",
                )
            )

        db.session.commit()
        print(f"数据库初始化完成，默认管理员: {app.config['ADMIN_USERNAME']}")
