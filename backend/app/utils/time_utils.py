"""时间显示工具：库内存 UTC（无时区），对外统一输出北京时间字符串。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

# 中国无夏令时，固定 UTC+8
BEIJING_TZ = timezone(timedelta(hours=8))
DISPLAY_FORMAT = "%Y-%m-%d %H:%M:%S"


def fmt_beijing(dt: datetime | None) -> str | None:
    """将时间转为北京时间字符串 ``YYYY-MM-DD HH:MM:SS``。

    - 无时区的 datetime 视为 UTC（库内 ``datetime.utcnow()`` 写入）
    - 带时区的按其时区换算
    - ``None`` 返回 ``None``
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(BEIJING_TZ).strftime(DISPLAY_FORMAT)
