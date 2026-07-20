"""日志查询服务。"""

from app.extensions import db
from app.models.log import FieldChangeLog, OperationLog
from app.models.user import User
from app.utils.log_display import (
    enrich_field_change_log,
    enrich_operation_log,
    list_action_options,
)


class LogService:
    """操作与字段变更日志查询。"""

    def _user_map(self) -> dict:
        return {u.id: u.username for u in User.query.all()}

    def list_operation_logs(self, page: int, page_size: int, action: str = "") -> dict:
        """分页查询操作日志（含中文可读字段）。"""
        query = OperationLog.query
        if action:
            # 支持英文 action 精确/模糊，也支持中文关键词匹配
            from app.utils.log_display import ACTION_LABELS

            matched_codes = [
                code
                for code, label in ACTION_LABELS.items()
                if action in code or action in label
            ]
            if matched_codes:
                query = query.filter(
                    db.or_(
                        OperationLog.action.in_(matched_codes),
                        OperationLog.action.like(f"%{action}%"),
                    )
                )
            else:
                query = query.filter(OperationLog.action.like(f"%{action}%"))

        total = query.count()
        items = (
            query.order_by(OperationLog.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        users = self._user_map()
        result_items = []
        for log in items:
            data = {
                "id": log.id,
                "username": users.get(log.user_id, ""),
                "action": log.action,
                "target_type": log.target_type,
                "target_id": log.target_id,
                "detail_json": log.detail_json,
                "ip": log.ip,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            result_items.append(enrich_operation_log(data, users))

        return {
            "items": result_items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "action_options": list_action_options(),
        }

    def list_field_change_logs(
        self, page: int, page_size: int, task_id: int | None = None
    ) -> dict:
        """分页查询字段变更日志（字段名中文化）。"""
        query = FieldChangeLog.query
        if task_id:
            query = query.filter_by(task_id=task_id)
        total = query.count()
        items = (
            query.order_by(FieldChangeLog.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        users = self._user_map()
        result_items = []
        for log in items:
            data = {
                "id": log.id,
                "task_id": log.task_id,
                "field_name": log.field_name,
                "old_value": log.old_value,
                "new_value": log.new_value,
                "reason": log.reason,
                "username": users.get(log.operator_id, ""),
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            result_items.append(enrich_field_change_log(data))

        return {
            "items": result_items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
