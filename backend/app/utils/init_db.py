"""数据库初始化脚本。"""

import json

from sqlalchemy import inspect, text

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
from app.utils.multi_value import (
    MULTI_JSON_FIELDS,
    load_known_option_sets_from_rules,
    normalize_multi_for_storage,
)

# 任务/正式库需检查/迁移的多选列
_MULTI_JSON_COLUMNS = tuple(sorted(MULTI_JSON_FIELDS))


def _column_type_name(col_info: dict) -> str:
    return str(col_info.get("type", "")).upper()


def _exec_with_deadlock_retry(fn, *, retries: int = 5, label: str = ""):
    """MySQL 死锁时短等待重试。"""
    import time

    from sqlalchemy.exc import OperationalError

    last_err = None
    for attempt in range(retries):
        try:
            return fn()
        except OperationalError as exc:
            last_err = exc
            # 1213 deadlock
            if "1213" not in str(exc) and "Deadlock" not in str(exc):
                raise
            db.session.rollback()
            time.sleep(0.3 * (attempt + 1))
            print(f"死锁重试 {label} ({attempt + 1}/{retries})")
    raise last_err


def _migrate_one_multi_column(
    table: str, col: str, known: set[str]
) -> bool:
    """迁移单列；已是 JSON 返回 False。"""
    inspector = inspect(db.engine)
    cols = {c["name"]: c for c in inspector.get_columns(table)}
    if col not in cols:
        return False
    type_name = _column_type_name(cols[col])
    if "JSON" in type_name:
        return False

    def _widen():
        if "TEXT" not in type_name and "JSON" not in type_name:
            db.session.execute(
                text(f"ALTER TABLE `{table}` MODIFY COLUMN `{col}` TEXT NULL")
            )
            db.session.commit()

    _exec_with_deadlock_retry(_widen, label=f"{table}.{col} TEXT")

    rows = db.session.execute(
        text(f"SELECT `id`, `{col}` FROM `{table}` WHERE `{col}` IS NOT NULL")
    ).fetchall()
    batch_n = 0
    for row_id, raw in rows:
        if isinstance(raw, (list, dict)):
            parsed = normalize_multi_for_storage(raw, known)
        else:
            text_val = str(raw).strip() if raw is not None else ""
            if text_val.startswith("[") and text_val.endswith("]"):
                try:
                    parsed = normalize_multi_for_storage(json.loads(text_val), known)
                except json.JSONDecodeError:
                    parsed = normalize_multi_for_storage(text_val, known)
            else:
                parsed = normalize_multi_for_storage(text_val, known)

        def _update(rid=row_id, val=parsed):
            db.session.execute(
                text(f"UPDATE `{table}` SET `{col}` = :v WHERE `id` = :id"),
                {
                    "v": json.dumps(val, ensure_ascii=False) if val else None,
                    "id": rid,
                },
            )

        _exec_with_deadlock_retry(_update, label=f"{table}.{col} id={row_id}")
        batch_n += 1
        if batch_n % 200 == 0:
            db.session.commit()
    db.session.commit()

    def _to_json():
        db.session.execute(
            text(f"ALTER TABLE `{table}` MODIFY COLUMN `{col}` JSON NULL")
        )
        db.session.commit()

    _exec_with_deadlock_retry(_to_json, label=f"{table}.{col} JSON")
    return True


def _migrate_table_multi_columns_to_json(table: str, known_by_field: dict[str, set[str]]):
    """
    将表中多选列从 VARCHAR/TEXT 迁为 JSON 数组。

    步骤：先改为 TEXT → 写入 JSON 文本 → 再改为 JSON。
    已是 JSON 的列跳过。
    """
    inspector = inspect(db.engine)
    if table not in inspector.get_table_names():
        return
    migrated = []
    for col in _MULTI_JSON_COLUMNS:
        known = known_by_field.get(col) or set()
        if _migrate_one_multi_column(table, col, known):
            migrated.append(col)
            print(f"  完成 {table}.{col}")

    if migrated:
        print(f"已迁移 {table} 多选列为 JSON: {', '.join(migrated)}")


def ensure_schema(app):
    """
    创建缺失表，并为已有库补齐增量字段。

    说明：SQLAlchemy create_all 不会 ALTER 已有表，生产更新需执行本函数。
    """
    with app.app_context():
        db.create_all()
        inspector = inspect(db.engine)
        tables = set(inspector.get_table_names())
        if "approved_products" not in tables:
            return

        cols = {c["name"] for c in inspector.get_columns("approved_products")}
        if "batch_id" not in cols:
            # MySQL：正式库增加来源批次字段
            db.session.execute(
                text(
                    "ALTER TABLE approved_products "
                    "ADD COLUMN batch_id BIGINT NULL, "
                    "ADD INDEX ix_approved_products_batch_id (batch_id)"
                )
            )
            db.session.commit()
            print("已为 approved_products 增加 batch_id 字段")

        # 分类多选：VARCHAR 逗号串 → JSON 数组（兼容「金,银丝…」）
        known = load_known_option_sets_from_rules()
        if "classification_tasks" in tables:
            _migrate_table_multi_columns_to_json("classification_tasks", known)
        _migrate_table_multi_columns_to_json("approved_products", known)


def init_database(app):
    """创建数据库表并初始化默认数据。"""
    ensure_schema(app)
    with app.app_context():
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

        if not SystemConfig.query.filter_by(
            config_key="operator_change_password_enabled"
        ).first():
            db.session.add(
                SystemConfig(
                    config_key="operator_change_password_enabled",
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
        ensure_schema(app)

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

        if not SystemConfig.query.filter_by(
            config_key="operator_change_password_enabled"
        ).first():
            db.session.add(
                SystemConfig(
                    config_key="operator_change_password_enabled",
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
