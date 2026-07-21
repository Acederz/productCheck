"""数据库初始化脚本。"""

from app.constants import ROLE_ADMIN
from app.extensions import db
from app.models import (
    ApprovedProduct,
    ApprovedProductHistory,
    AssignmentLog,
    ClassificationTask,
    FieldChangeLog,
    ImportBatch,
    OperationLog,
    ReviewLog,
    TaskDraft,
    User,
)
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


def reset_keep_admin_and_rules(app):
    """
    清空业务数据，只保留：
    - 管理员账号（role=admin）
    - 分类规则相关表（版本 / 节点 / 字段规则）
    - 系统配置

    会删除：操作员账号、导入批次、任务、草稿、正式库、各类操作日志等。
    """
    with app.app_context():
        db.create_all()

        # 按外键依赖顺序删除业务表（规则表不动）
        clear_order = [
            FieldChangeLog,
            AssignmentLog,
            ReviewLog,
            OperationLog,
            TaskDraft,
            ApprovedProductHistory,
            ApprovedProduct,
            ClassificationTask,
            ImportBatch,
        ]

        deleted_counts = {}
        for model in clear_order:
            count = model.query.delete(synchronize_session=False)
            deleted_counts[model.__tablename__] = count

        # 删除非管理员用户（操作员等）
        removed_users = User.query.filter(User.role != ROLE_ADMIN).delete(
            synchronize_session=False
        )
        deleted_counts["users_non_admin"] = removed_users

        # 确保至少有默认管理员与系统配置
        admin_name = app.config["ADMIN_USERNAME"]
        admin = User.query.filter_by(username=admin_name, role=ROLE_ADMIN).first()
        if not admin:
            # 若库中已有其他管理员，保留；否则创建 .env 中的默认管理员
            any_admin = User.query.filter_by(role=ROLE_ADMIN).first()
            if not any_admin:
                admin = User(
                    username=admin_name,
                    role=ROLE_ADMIN,
                    is_active=True,
                )
                admin.set_password(app.config["ADMIN_PASSWORD"])
                db.session.add(admin)
                print(f"已重新创建管理员账号: {admin_name}")

        if not SystemConfig.query.filter_by(config_key="operator_export_enabled").first():
            db.session.add(
                SystemConfig(
                    config_key="operator_export_enabled",
                    config_value="false",
                )
            )

        db.session.commit()

        kept_admins = User.query.filter_by(role=ROLE_ADMIN).count()
        print("业务数据已清空，仅保留管理员与分类规则。")
        print(f"保留管理员账号数: {kept_admins}")
        for table, count in deleted_counts.items():
            print(f"  删除 {table}: {count} 行")
        print("保留表: classification_rule_versions / nodes / field_rules（及规则变更日志）")
