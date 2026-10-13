"""文本手填 / 主表占位 0·1 不得把下级级联选项滤空。"""

import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from app.extensions import db
from app.models.rule import (
    ClassificationFieldRule,
    ClassificationRuleNode,
    ClassificationRuleVersion,
)
from app.services.rule_service import RuleService

UT_PREFIX = "UT_TXTMODE_"


class TextModeCascadeTests(unittest.TestCase):
    """覆盖垃圾袋辅材质手填、保鲜膜包装手填、无补充规则时的占位通配。"""

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.ctx = cls.app.app_context()
        cls.ctx.push()
        cls.svc = RuleService()
        cls._cleanup()

    @classmethod
    def tearDownClass(cls):
        cls._cleanup()
        cls.ctx.pop()

    @classmethod
    def _cleanup(cls):
        db.session.rollback()
        versions = ClassificationRuleVersion.query.filter(
            ClassificationRuleVersion.version_no.like(f"{UT_PREFIX}%")
        ).all()
        for v in versions:
            ClassificationRuleNode.query.filter_by(version_id=v.id).delete()
            ClassificationFieldRule.query.filter_by(version_id=v.id).delete()
            db.session.delete(v)
        db.session.commit()

    def setUp(self):
        self._cleanup()
        self.version = ClassificationRuleVersion(
            version_no=f"{UT_PREFIX}v1",
            remark="unit test text mode cascade",
            created_by=1,
        )
        db.session.add(self.version)
        db.session.flush()

        # —— 垃圾袋类：辅材质占位 0 + 补充规则文本 ——
        for pack, size in (("背心", "L"), ("抽绳", "M")):
            db.session.add(
                ClassificationRuleNode(
                    version_id=self.version.id,
                    category_large="垃圾袋类",
                    category_segment="商务垃圾袋",
                    category_type="无香",
                    material_main="可降解",
                    material_aux="0",
                    packaging=pack,
                    size_option=size,
                    roll_input_mode="0",
                    total_input_mode="0",
                    is_active=True,
                )
            )
        db.session.add(
            ClassificationFieldRule(
                version_id=self.version.id,
                field_name="辅材质",
                input_mode="0",
                path_large="垃圾袋类",
                option_value="0",
                hint="厚度说明",
                is_active=True,
            )
        )

        # —— 保鲜膜类：包装方式占位 0 + 补充规则文本；尺寸为具体选项 ——
        db.session.add(
            ClassificationRuleNode(
                version_id=self.version.id,
                category_large="保鲜膜类",
                category_segment="普通",
                category_type="经济装",
                material_main="PE",
                material_aux="-",
                packaging="0",
                size_option="30M",
                roll_input_mode="0",
                total_input_mode="0",
                is_active=True,
            )
        )
        db.session.add(
            ClassificationRuleNode(
                version_id=self.version.id,
                category_large="保鲜膜类",
                category_segment="普通",
                category_type="经济装",
                material_main="PE",
                material_aux="-",
                packaging="0",
                size_option="100M",
                roll_input_mode="0",
                total_input_mode="0",
                is_active=True,
            )
        )
        db.session.add(
            ClassificationFieldRule(
                version_id=self.version.id,
                field_name="包装方式",
                input_mode="0",
                path_large="保鲜膜类",
                path_segment="普通",
                option_value="0",
                hint="短边CM",
                is_active=True,
            )
        )

        # —— 无补充规则、仅主表占位：仍应靠 0/1 通配出下级选项 ——
        db.session.add(
            ClassificationRuleNode(
                version_id=self.version.id,
                category_large="占位通配类",
                category_segment="区隔A",
                category_type="类别A",
                material_main="主材A",
                material_aux="0",
                packaging="盒装",
                size_option="S",
                roll_input_mode="0",
                total_input_mode="0",
                is_active=True,
            )
        )

        # —— 尺寸文本 + 卷数下拉：手填尺寸后卷数规则仍应命中 ——
        db.session.add(
            ClassificationRuleNode(
                version_id=self.version.id,
                category_large="盘具类",
                category_segment="一次性盘",
                category_type="圆盘",
                material_main="纸",
                material_aux="无",
                packaging="袋装",
                size_option="0",
                roll_input_mode="1",
                total_input_mode="0",
                is_active=True,
            )
        )
        db.session.add(
            ClassificationFieldRule(
                version_id=self.version.id,
                field_name="尺寸",
                input_mode="0",
                path_large="盘具类",
                path_segment="一次性盘",
                option_value="0",
                hint="英寸",
                is_active=True,
            )
        )
        db.session.add(
            ClassificationFieldRule(
                version_id=self.version.id,
                field_name="卷数",
                input_mode="1",
                path_large="盘具类",
                path_segment="一次性盘",
                path_size="0",  # 规则路径占位，不应挡住手填尺寸
                option_value="10个",
                is_active=True,
            )
        )
        db.session.add(
            ClassificationFieldRule(
                version_id=self.version.id,
                field_name="卷数",
                input_mode="1",
                path_large="盘具类",
                path_segment="一次性盘",
                option_value="20个",
                is_active=True,
            )
        )

        db.session.commit()
        self.assertEqual(self.svc.get_latest_version().id, self.version.id)

    def tearDown(self):
        self._cleanup()

    def test_garbage_bag_packaging_with_free_text_aux(self):
        path = {
            "大类": ["垃圾袋类"],
            "区隔": ["商务垃圾袋"],
            "类别": ["无香"],
            "主材质": ["可降解"],
            "辅材质": ["2丝"],
        }
        data = self.svc.get_cascade_options("包装方式", path)
        self.assertEqual(data["input_mode"], "select")
        self.assertEqual(sorted(data["options"]), ["抽绳", "背心"])

    def test_garbage_bag_size_with_free_text_aux(self):
        path = {
            "大类": ["垃圾袋类"],
            "区隔": ["商务垃圾袋"],
            "类别": ["无香"],
            "主材质": ["可降解"],
            "辅材质": ["2丝"],
            "包装方式": ["背心"],
        }
        data = self.svc.get_field_meta("尺寸", path)
        self.assertEqual(data["input_mode"], "select")
        self.assertIn("L", data["options"])

    def test_wrap_film_size_with_free_text_packaging(self):
        """保鲜膜类包装手填后，尺寸具体选项仍可从主表取出。"""
        path = {
            "大类": ["保鲜膜类"],
            "区隔": ["普通"],
            "类别": ["经济装"],
            "主材质": ["PE"],
            "辅材质": ["-"],
            "包装方式": ["20CM"],
        }
        data = self.svc.get_field_meta("尺寸", path)
        self.assertEqual(data["input_mode"], "select")
        self.assertEqual(sorted(data["options"]), ["100M", "30M"])

    def test_placeholder_wildcard_without_supplement_rule(self):
        """无 mode=0 补充规则时，主表辅材质=0 仍通配，包装方式有选项。"""
        path = {
            "大类": ["占位通配类"],
            "区隔": ["区隔A"],
            "类别": ["类别A"],
            "主材质": ["主材A"],
            "辅材质": ["任意手填"],
        }
        data = self.svc.get_cascade_options("包装方式", path)
        self.assertEqual(data["options"], ["盒装"])

    def test_roll_select_after_free_text_size(self):
        """尺寸手填后，卷数下拉补充规则仍应命中。"""
        path = {
            "大类": ["盘具类"],
            "区隔": ["一次性盘"],
            "类别": ["圆盘"],
            "主材质": ["纸"],
            "辅材质": ["无"],
            "包装方式": ["袋装"],
            "尺寸": ["9英寸"],
        }
        data = self.svc.get_field_meta("卷数", path)
        self.assertEqual(data["input_mode"], "select")
        self.assertEqual(sorted(data["options"]), ["10个", "20个"])


if __name__ == "__main__":
    unittest.main()
