"""导出分类清洗：多值用 + 拼接、去括号（含区隔）。"""

import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.utils.export_clean import (
    clean_and_upper_classification_value,
    clean_export_classification_value,
)


class ExportCleanPlusJoinTests(unittest.TestCase):
    """多值连接符与括号清洗。"""

    def test_multi_value_list_joins_with_plus(self):
        self.assertEqual(
            clean_export_classification_value(["保鲜袋", "连卷袋"]),
            "保鲜袋+连卷袋",
        )

    def test_comma_separated_string_joins_with_plus(self):
        self.assertEqual(
            clean_export_classification_value("盒装，袋装"),
            "盒装+袋装",
        )

    def test_strip_english_parentheses(self):
        self.assertEqual(
            clean_export_classification_value("XXX(jjj)"),
            "XXX",
        )

    def test_strip_chinese_parentheses(self):
        self.assertEqual(
            clean_export_classification_value("保鲜袋（说明）"),
            "保鲜袋",
        )

    def test_segment_list_strips_paren_and_joins_with_plus(self):
        """区隔多选：去括号后用 + 拼接。"""
        self.assertEqual(
            clean_export_classification_value(["XXX(jjj)", "YYY"]),
            "XXX+YYY",
        )

    def test_whitelist_keeps_paren_content(self):
        self.assertEqual(
            clean_export_classification_value("免刀撕（点断）"),
            "免刀撕（点断）",
        )

    def test_drop_standalone_dash_in_multi(self):
        self.assertEqual(
            clean_export_classification_value("盒装、-"),
            "盒装",
        )

    def test_clean_and_upper_after_strip(self):
        self.assertEqual(
            clean_and_upper_classification_value(["abc(x)", "def"]),
            "ABC+DEF",
        )


if __name__ == "__main__":
    unittest.main()
