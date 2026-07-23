"""列表查询共用的筛选条件工具。"""

from sqlalchemy import or_, func


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
