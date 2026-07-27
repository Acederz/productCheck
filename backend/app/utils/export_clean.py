"""导出数据清洗工具。

管理员导出时，对「类别」及之后字段做展示清洗：
- 去掉英文/中文括号及其内容（白名单整词保留）
- 单独的「-」视为空；多值中的「-」丢弃（如 盒装、- → 盒装）
"""

from __future__ import annotations

import re
from typing import Any

# 导出时需清洗的字段（自「类别」起，含主材质等）
EXPORT_CLEAN_FIELDS = (
    "category_type",
    "material_main",
    "material_aux",
    "packaging",
    "size",
    "roll_count",
    "total_count",
)

# 保留括号内容的完整词（不去掉括号内文字）
_PAREN_KEEP_VALUES = frozenset(
    {
        "免刀撕（点断）",
        "免刀撕（单张）",
        "免刀撕(点断)",
        "免刀撕(单张)",
    }
)

_RE_CN_PAREN = re.compile(r"（[^）]*）")
_RE_EN_PAREN = re.compile(r"\([^)]*\)")
# 把「盒装.-」「盒装、-」这类分隔成多值，便于去掉单独的 -
_RE_DASH_SEP = re.compile(r"[.．、，,]\s*-\s*|-\s*[.．、，,]")


def _strip_parentheses(text: str) -> str:
    """去掉括号及其中内容；白名单整词原样返回。"""
    raw = text.strip()
    if not raw:
        return ""
    if raw in _PAREN_KEEP_VALUES:
        return raw
    cleaned = _RE_CN_PAREN.sub("", raw)
    cleaned = _RE_EN_PAREN.sub("", cleaned)
    return cleaned.strip()


def _clean_token(token: str) -> str:
    """清洗单个选项值。"""
    text = str(token).strip() if token is not None else ""
    if not text or text == "-":
        return ""
    text = _strip_parentheses(text)
    if not text or text == "-":
        return ""
    return text


def clean_export_classification_value(value: Any) -> str:
    """
    清洗类别及后续分类字段的导出值。

    参数:
        value: 字符串、逗号分隔多值，或 list
    返回:
        清洗后的导出字符串（多值用中文逗号连接）；无效则为空串
    """
    if value is None:
        return ""

    if isinstance(value, (list, tuple, set)):
        parts = [str(v) for v in value]
    else:
        text = str(value).strip()
        if not text or text == "-":
            return ""
        # 统一把「值.-」「值、-」中的单独横杠拆出去
        text = _RE_DASH_SEP.sub("，", text)
        parts = re.split(r"[，,]", text)

    cleaned: list[str] = []
    seen: set[str] = set()
    for part in parts:
        item = _clean_token(part)
        if not item or item in seen:
            continue
        seen.add(item)
        cleaned.append(item)
    return "，".join(cleaned)


def upper_classification_text(value: Any) -> str:
    """
    正式库展示/导出：分类字段中的英文字母统一大写（中文等不变）。

    仅做展示层转换，不写回数据库。
    """
    if value is None:
        return ""
    if isinstance(value, (list, tuple, set)):
        text = "，".join(str(v).strip() for v in value if str(v).strip())
    else:
        text = str(value).strip()
    if not text or text == "-":
        return ""
    return text.upper()


def clean_and_upper_classification_value(value: Any) -> str:
    """先做导出清洗，再英文字母大写（正式库导出用）。"""
    cleaned = clean_export_classification_value(value)
    return cleaned.upper() if cleaned else ""
