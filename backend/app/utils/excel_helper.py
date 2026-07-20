"""Excel 通用工具。"""

import json
from typing import Any


def cell_str(value: Any) -> str:
    """单元格转字符串，去除首尾空白。"""
    if value is None:
        return ""
    if isinstance(value, float) and value == int(value):
        return str(int(value))
    return str(value).strip()


def parse_desc_images(value: Any) -> list:
    """解析宝贝文描图 JSON 或单 URL。"""
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    text = cell_str(value)
    if not text:
        return []
    if text.startswith("["):
        try:
            data = json.loads(text)
            return data if isinstance(data, list) else [text]
        except json.JSONDecodeError:
            return [text]
    return [text]


def parse_segment(value: Any) -> list:
    """解析区隔字段，支持单值或逗号分隔。"""
    text = cell_str(value)
    if not text:
        return []
    if "，" in text:
        parts = text.split("，")
    elif "," in text:
        parts = text.split(",")
    else:
        parts = [text]
    return [p.strip() for p in parts if p.strip()]
