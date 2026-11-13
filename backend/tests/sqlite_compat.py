"""单测用 SQLite 兼容：BigInteger 主键在 SQLite 中编译为 INTEGER，才能自增。

只在测试中导入，不影响 MySQL 建表。
"""

from sqlalchemy import BigInteger
from sqlalchemy.ext.compiler import compiles


@compiles(BigInteger, "sqlite")
def _bigint_as_integer_on_sqlite(type_, compiler, **kw):  # noqa: ANN001, ARG001
    return "INTEGER"
