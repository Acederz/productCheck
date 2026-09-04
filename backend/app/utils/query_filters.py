"""列表查询共用的筛选条件工具。"""

from sqlalchemy import false, func, or_


def parse_csv_arg(raw) -> list[str]:
    """解析逗号分隔的查询参数为去重后的字符串列表。"""
    if raw is None:
        return []
    if isinstance(raw, (list, tuple, set)):
        values = [str(item).strip() for item in raw if item is not None and str(item).strip()]
    else:
        text = str(raw).strip()
        if not text:
            return []
        values = [part.strip() for part in text.split(",") if part.strip()]
    # 保序去重
    seen = set()
    result = []
    for item in values:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def parse_int_ids(raw) -> list[int]:
    """解析逗号分隔的整数 ID 列表（非法片段跳过）。"""
    ids: list[int] = []
    seen: set[int] = set()
    for part in parse_csv_arg(raw):
        if not part.isdigit():
            continue
        value = int(part)
        if value in seen:
            continue
        seen.add(value)
        ids.append(value)
    return ids


def apply_batch_id_filter(query, model, batch_id=None):
    """按导入批次 ID 筛选（支持多选）。"""
    batch_ids = parse_int_ids(batch_id)
    if not batch_ids:
        return query
    return query.filter(model.batch_id.in_(batch_ids))


def apply_assignee_id_filter(query, model, assignee_id=None):
    """按负责人 ID 筛选（支持多选）。"""
    ids = parse_int_ids(assignee_id)
    if not ids:
        return query
    return query.filter(model.assignee_id.in_(ids))


def apply_platform_filter(query, model, platform=None):
    """按平台筛选（支持逗号多选）。"""
    platforms = parse_csv_arg(platform)
    if not platforms:
        return query
    if len(platforms) == 1:
        return query.filter_by(platform=platforms[0])
    return query.filter(model.platform.in_(platforms))


def apply_status_filter(query, model, status=None):
    """按任务状态筛选（支持逗号多选，仅保留合法状态）。"""
    from app.constants import TASK_STATUSES

    requested = parse_csv_arg(status)
    if not requested:
        # 未传 status 或空字符串：不过滤
        return query

    statuses = [s for s in requested if s in TASK_STATUSES]
    if not statuses:
        # 传了 status 但全部非法：强制空结果，避免误返回全量
        return query.filter(false())
    if len(statuses) == 1:
        return query.filter_by(status=statuses[0])
    return query.filter(model.status.in_(statuses))


def _json_string_literal(value: str) -> str:
    """生成 JSON_CONTAINS 所需的 JSON 字符串字面量。"""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def apply_category_filters(query, model, category_large=None, category_segment=None):
    """
    按大类、区隔筛选任务/正式库记录。

    多选语义为「或」：命中任一所选值即可。
    - 大类：库内常为逗号分隔字符串（如 A,B）
    - 区隔：库内为 JSON 数组
    """
    large_list = parse_csv_arg(category_large)
    segment_list = parse_csv_arg(category_segment)

    if large_list:
        large_col = model.category_large
        query = query.filter(
            or_(*[func.find_in_set(value, large_col) > 0 for value in large_list])
        )

    if segment_list:
        segment_col = model.category_segment
        query = query.filter(
            or_(
                *[
                    func.json_contains(segment_col, _json_string_literal(value)) == 1
                    for value in segment_list
                ]
            )
        )

    return query
