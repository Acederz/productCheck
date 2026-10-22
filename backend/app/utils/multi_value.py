"""分类多选字段：统一按 JSON 数组存取，并兼容旧逗号分隔串。

选项名本身可含逗号（如「金,银丝交织包含海绵」），不得再被当成多选分隔符。
"""

from __future__ import annotations

from typing import Any, Iterable

# 与区隔一样按 JSON 数组落库的多选业务字段（不含大类）
MULTI_JSON_FIELDS = frozenset(
    {
        "category_segment",
        "category_type",
        "material_main",
        "material_aux",
        "packaging",
        "size",
        "roll_count",
        "total_count",
    }
)


def _clean_list(parts: Iterable[Any]) -> list[str]:
    return [str(v).strip() for v in parts if v is not None and str(v).strip()]


def _coalesce_parts(parts: list[str], known: set[str]) -> list[str]:
    """把连续片段用逗号拼回，若命中已知选项则合并为一项。"""
    if not parts:
        return []
    if not known:
        return parts

    result: list[str] = []
    i = 0
    n = len(parts)
    while i < n:
        matched: str | None = None
        # 从最长片段组合试到最短，优先整词命中（含选项内逗号）
        for j in range(n, i, -1):
            joined_en = ",".join(parts[i:j])
            joined_cn = "，".join(parts[i:j])
            if joined_en in known:
                matched = joined_en
                i = j
                break
            if joined_cn in known:
                matched = joined_cn
                i = j
                break
        if matched is not None:
            result.append(matched)
        else:
            result.append(parts[i])
            i += 1
    return result


def parse_stored_multi_value(
    value: Any, known_options: Iterable[str] | None = None
) -> list[str]:
    """
    将库内多选值规范为字符串列表。

    - list → 去空白
    - 无逗号字符串 → 单元素
    - 含逗号旧串 → 先拆分，再用 known_options 合并「选项内逗号」
    - 整串已在 known_options → 不拆
    """
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return _clean_list(value)

    text = str(value).strip()
    if not text:
        return []

    known = {str(x).strip() for x in (known_options or []) if str(x).strip()}
    if text in known:
        return [text]
    if "，" not in text and "," not in text:
        return [text]

    parts = [p.strip() for p in text.replace("，", ",").split(",") if p.strip()]
    return _coalesce_parts(parts, known)


def normalize_multi_for_storage(
    value: Any, known_options: Iterable[str] | None = None
) -> list[str] | None:
    """写入前规范为 JSON 数组；空则 None。"""
    if value is None:
        return None
    if isinstance(value, str):
        parsed = parse_stored_multi_value(value, known_options)
    elif isinstance(value, (list, tuple, set)):
        parsed = _clean_list(value)
    else:
        text = str(value).strip()
        parsed = [text] if text else []
    return parsed or None


def load_known_option_sets_from_rules() -> dict[str, set[str]]:
    """从最新分类规则节点收集各多选字段已知选项（用于旧串智能还原）。"""
    from sqlalchemy import distinct

    from app.extensions import db
    from app.models.rule import ClassificationRuleNode, ClassificationRuleVersion

    known: dict[str, set[str]] = {f: set() for f in MULTI_JSON_FIELDS}
    version = (
        ClassificationRuleVersion.query.order_by(ClassificationRuleVersion.id.desc())
        .first()
    )
    if not version:
        return known

    attr_map = {
        "category_segment": ClassificationRuleNode.category_segment,
        "category_type": ClassificationRuleNode.category_type,
        "material_main": ClassificationRuleNode.material_main,
        "material_aux": ClassificationRuleNode.material_aux,
        "packaging": ClassificationRuleNode.packaging,
        "size": ClassificationRuleNode.size_option,
    }
    for field, col in attr_map.items():
        rows = (
            db.session.query(distinct(col))
            .filter(
                ClassificationRuleNode.version_id == version.id,
                ClassificationRuleNode.is_active.is_(True),
                col.isnot(None),
                col != "",
            )
            .all()
        )
        for (val,) in rows:
            if val is not None and str(val).strip():
                known[field].add(str(val).strip())
    return known
