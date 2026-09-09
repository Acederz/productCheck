"""用户管理接口（管理员）。"""

from flask import Blueprint, g, request

from app.constants import ROLE_ADMIN, ROLE_OPERATOR
from app.extensions import db
from app.models.user import User
from app.utils.auth_decorator import admin_required
from app.utils.response import fail, success

users_bp = Blueprint("users", __name__)


@users_bp.get("")
@admin_required
def list_users():
    """用户列表。"""
    users = User.query.order_by(User.id.asc()).all()
    return success([u.to_dict() for u in users])


@users_bp.post("")
@admin_required
def create_user():
    """创建用户。"""
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    role = data.get("role") or ROLE_OPERATOR

    if not username or not password:
        return fail("账号和密码不能为空")
    if role not in (ROLE_ADMIN, ROLE_OPERATOR):
        return fail("角色无效")
    if User.query.filter_by(username=username).first():
        return fail("账号已存在")

    user = User(username=username, role=role, is_active=True)
    user.set_password(password)
    db.session.add(user)
    from app.services.operation_log_service import write_operation_log
    write_operation_log(g.current_user.id, "create_user", "user", None, {"username": username, "role": role})
    db.session.commit()
    return success(user.to_dict(), message="创建成功")


@users_bp.put("/<int:user_id>")
@admin_required
def update_user(user_id: int):
    """更新用户状态或重置密码。"""
    user = User.query.get(user_id)
    if not user:
        return fail("用户不存在", 404)

    data = request.get_json(silent=True) or {}
    if "is_active" in data:
        user.is_active = bool(data["is_active"])
    if data.get("password"):
        user.set_password(data["password"])

    from app.services.operation_log_service import write_operation_log
    write_operation_log(g.current_user.id, "update_user", "user", user_id, {"is_active": user.is_active})
    db.session.commit()
    return success(user.to_dict(), message="更新成功")


@users_bp.delete("/<int:user_id>")
@admin_required
def delete_user(user_id: int):
    """删除操作员账号（有未完成任务则拒绝）。"""
    from app.constants import (
        TASK_STATUS_PENDING,
        TASK_STATUS_REJECTED,
        TASK_STATUS_REVIEW,
    )
    from app.models.approved import ApprovedProduct
    from app.models.log import AssignmentLog, FieldChangeLog, OperationLog, ReviewLog
    from app.models.rule import ClassificationRuleChangeLog, ClassificationRuleVersion
    from app.models.task import ClassificationTask, TaskDraft
    from app.models.user import SystemConfig
    from app.services.operation_log_service import write_operation_log

    user = User.query.get(user_id)
    if not user:
        return fail("用户不存在", 404)
    if user.id == g.current_user.id:
        return fail("不能删除当前登录账号")
    if user.role == ROLE_ADMIN:
        return fail("不能删除管理员账号", 403)

    unfinished = ClassificationTask.query.filter(
        ClassificationTask.assignee_id == user_id,
        ClassificationTask.status.in_(
            [TASK_STATUS_PENDING, TASK_STATUS_REVIEW, TASK_STATUS_REJECTED]
        ),
    ).count()
    if unfinished:
        return fail(f"该账号仍有 {unfinished} 条未完成任务，请先处理或改派后再删")

    username = user.username
    try:
        TaskDraft.query.filter_by(assignee_id=user_id).delete(synchronize_session=False)
        ClassificationTask.query.filter_by(assignee_id=user_id).update(
            {ClassificationTask.assignee_id: None}, synchronize_session=False
        )
        ClassificationTask.query.filter_by(reviewed_by=user_id).update(
            {ClassificationTask.reviewed_by: None}, synchronize_session=False
        )
        ApprovedProduct.query.filter_by(approved_by=user_id).update(
            {ApprovedProduct.approved_by: None}, synchronize_session=False
        )
        OperationLog.query.filter_by(user_id=user_id).update(
            {OperationLog.user_id: None}, synchronize_session=False
        )
        FieldChangeLog.query.filter_by(operator_id=user_id).update(
            {FieldChangeLog.operator_id: None}, synchronize_session=False
        )
        AssignmentLog.query.filter_by(operator_id=user_id).update(
            {AssignmentLog.operator_id: None}, synchronize_session=False
        )
        ReviewLog.query.filter_by(operator_id=user_id).update(
            {ReviewLog.operator_id: None}, synchronize_session=False
        )
        SystemConfig.query.filter_by(updated_by=user_id).update(
            {SystemConfig.updated_by: None}, synchronize_session=False
        )
        ClassificationRuleVersion.query.filter_by(created_by=user_id).update(
            {ClassificationRuleVersion.created_by: None}, synchronize_session=False
        )
        from app.models.skip_field_rule import SkipFieldRuleVersion

        SkipFieldRuleVersion.query.filter_by(created_by=user_id).update(
            {SkipFieldRuleVersion.created_by: None}, synchronize_session=False
        )
        ClassificationRuleChangeLog.query.filter_by(operator_id=user_id).update(
            {ClassificationRuleChangeLog.operator_id: None}, synchronize_session=False
        )
        write_operation_log(
            g.current_user.id,
            "delete_user",
            "user",
            user_id,
            {"username": username, "user_id": user_id},
        )
        db.session.delete(user)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        return fail(f"删除失败：{exc}", 500)

    return success(message="删除成功")
