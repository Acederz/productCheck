"""操作日志中文展示工具。

将库中存储的英文 action / target_type / JSON 详情，转换为用户可读的中文描述。
"""

from __future__ import annotations

from app.models.user import User

# 操作类型
ACTION_LABELS = {
    "import_excel": "导入商品数据",
    "import_rules": "导入分类规则",
    "assign_tasks": "分配任务",
    "withdraw_tasks": "撤回任务",
    "submit_tasks": "提交审核",
    "approve_tasks": "审核通过",
    "reject_tasks": "审核驳回",
    "create_user": "创建用户",
    "update_user": "更新用户",
    "update_config": "修改系统设置",
    "export_tasks": "导出任务数据",
    "export_approved": "导出正式数据",
    "login": "登录",
    "logout": "退出登录",
}

# 对象类型
TARGET_TYPE_LABELS = {
    "task": "任务",
    "user": "用户",
    "import_batch": "导入批次",
    "rule_version": "规则版本",
    "system_config": "系统配置",
    "export": "导出文件",
    "approved_product": "正式数据",
}

# 详情字段键
DETAIL_KEY_LABELS = {
    "task_ids": "任务编号",
    "assignee_id": "操作员",
    "username": "用户名",
    "role": "角色",
    "is_active": "是否启用",
    "reason": "原因",
    "version_no": "版本号",
    "nodes": "规则行数",
    "field_rules": "补充规则行数",
    "count": "导出条数",
    "filters": "筛选条件",
    "key": "配置项",
    "value": "配置值",
    "batch_no": "批次号",
    "file_name": "文件名",
    "total_rows": "总行数",
    "success_rows": "成功行数",
    "fail_rows": "失败行数",
}

# 字段变更日志字段名
FIELD_NAME_LABELS = {
    "is_operating": "是否经营",
    "category_large": "大类",
    "category_segment": "区隔",
    "category_type": "类别",
    "material_main": "主材质",
    "material_aux": "辅材质",
    "packaging": "包装方式",
    "size": "尺寸",
    "roll_count": "卷数",
    "total_count": "总入数",
    "product_name": "宝贝名称",
    "brand": "品牌",
    "platform": "数据平台",
    "status": "状态",
}

ROLE_LABELS = {
    "admin": "管理员",
    "operator": "操作员",
}

CONFIG_KEY_LABELS = {
    "operator_export_enabled": "允许操作员导出数据",
}


def action_label(action: str | None) -> str:
    """操作类型中文名。"""
    if not action:
        return "-"
    return ACTION_LABELS.get(action, action)


def target_type_label(target_type: str | None) -> str:
    """对象类型中文名。"""
    if not target_type:
        return "-"
    return TARGET_TYPE_LABELS.get(target_type, target_type)


def field_name_label(field_name: str | None) -> str:
    """字段名中文。"""
    if not field_name:
        return "-"
    return FIELD_NAME_LABELS.get(field_name, field_name)


def _user_name_map() -> dict:
    """用户 ID -> 用户名。"""
    try:
        return {u.id: u.username for u in User.query.all()}
    except Exception:
        return {}


def _format_scalar(key: str, value) -> str:
    """格式化单个详情值。"""
    if value is None or value == "":
        return "空"
    if key == "role":
        return ROLE_LABELS.get(str(value), str(value))
    if key == "is_active":
        return "启用" if value in (True, 1, "1", "true", "True") else "停用"
    if key == "key":
        return CONFIG_KEY_LABELS.get(str(value), str(value))
    if key == "value" and isinstance(value, str) and value.lower() in ("true", "false", "1", "0"):
        return "开启" if value.lower() in ("true", "1") else "关闭"
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, list):
        if not value:
            return "无"
        # 任务编号列表：只展示数量 + 前若干个，避免过长
        if key == "task_ids":
            preview = "、".join(str(v) for v in value[:8])
            if len(value) > 8:
                preview += f" 等共 {len(value)} 条"
            else:
                preview += f"（共 {len(value)} 条）"
            return preview
        return "、".join(str(v) for v in value)
    if isinstance(value, dict):
        parts = []
        for k, v in value.items():
            label = DETAIL_KEY_LABELS.get(k, k)
            parts.append(f"{label}={_format_scalar(k, v)}")
        return "；".join(parts) if parts else "无"
    return str(value)


def format_detail_text(detail_json, users: dict | None = None) -> str:
    """将 detail_json 转为中文可读句子。"""
    if not detail_json:
        return "-"
    if not isinstance(detail_json, dict):
        return str(detail_json)

    users = users if users is not None else _user_name_map()
    parts = []
    for key, value in detail_json.items():
        label = DETAIL_KEY_LABELS.get(key, key)
        # 操作员 ID 转用户名
        if key == "assignee_id" and value is not None:
            name = users.get(int(value), None) if str(value).isdigit() else None
            display = f"{name}（编号 {value}）" if name else str(value)
            parts.append(f"{label}：{display}")
            continue
        parts.append(f"{label}：{_format_scalar(key, value)}")
    return "；".join(parts) if parts else "-"


def enrich_operation_log(log_dict: dict, users: dict | None = None) -> dict:
    """为操作日志字典补充中文展示字段。"""
    users = users if users is not None else _user_name_map()
    log_dict["action_label"] = action_label(log_dict.get("action"))
    log_dict["target_type_label"] = target_type_label(log_dict.get("target_type"))
    log_dict["detail_text"] = format_detail_text(log_dict.get("detail_json"), users)
    return log_dict


def enrich_field_change_log(log_dict: dict) -> dict:
    """为字段变更日志补充中文字段名。"""
    log_dict["field_label"] = field_name_label(log_dict.get("field_name"))
    return log_dict


def list_action_options() -> list[dict]:
    """操作类型筛选项（中文）。"""
    return [{"value": k, "label": v} for k, v in ACTION_LABELS.items()]
