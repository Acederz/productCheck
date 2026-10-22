"""多选字段 JSON 数组：解析旧逗号串时保留选项内逗号。"""

import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.utils.multi_value import (
    MULTI_JSON_FIELDS,
    normalize_multi_for_storage,
    parse_stored_multi_value,
)


class MultiValueParseTests(unittest.TestCase):
    def test_array_passthrough(self):
        self.assertEqual(
            parse_stored_multi_value(["平口", "点断"]),
            ["平口", "点断"],
        )

    def test_single_string_no_comma(self):
        self.assertEqual(parse_stored_multi_value("平口"), ["平口"])

    def test_legacy_comma_split_without_known(self):
        self.assertEqual(
            parse_stored_multi_value("平口,点断"),
            ["平口", "点断"],
        )

    def test_option_with_comma_kept_when_known(self):
        known = {"金,银丝交织包含海绵", "平口"}
        self.assertEqual(
            parse_stored_multi_value("金,银丝交织包含海绵", known),
            ["金,银丝交织包含海绵"],
        )

    def test_option_with_comma_coalesce_after_naive_split(self):
        """旧串被错误理解前，拆段后仍能拼回已知选项。"""
        known = {"金,银丝交织包含海绵"}
        # 模拟已被拆坏的中间态：整串仍可命中 known
        self.assertEqual(
            parse_stored_multi_value("金,银丝交织包含海绵", known),
            ["金,银丝交织包含海绵"],
        )

    def test_multi_real_options_with_known(self):
        known = {"平口", "点断", "金,银丝交织包含海绵"}
        self.assertEqual(
            parse_stored_multi_value("平口,点断", known),
            ["平口", "点断"],
        )

    def test_mixed_known_comma_option_and_other(self):
        known = {"金,银丝交织包含海绵", "其它"}
        self.assertEqual(
            parse_stored_multi_value("金,银丝交织包含海绵,其它", known),
            ["金,银丝交织包含海绵", "其它"],
        )

    def test_normalize_storage_list(self):
        self.assertEqual(
            normalize_multi_for_storage([" 金,银丝交织包含海绵 ", ""]),
            ["金,银丝交织包含海绵"],
        )

    def test_normalize_storage_empty(self):
        self.assertIsNone(normalize_multi_for_storage([]))
        self.assertIsNone(normalize_multi_for_storage(None))

    def test_multi_json_fields_cover_expected(self):
        self.assertIn("category_type", MULTI_JSON_FIELDS)
        self.assertIn("category_segment", MULTI_JSON_FIELDS)
        self.assertNotIn("category_large", MULTI_JSON_FIELDS)


if __name__ == "__main__":
    unittest.main()
