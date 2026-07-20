"""本地验证：规则导入与商品导入（需已配置 MySQL 并 init-db）。"""

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.utils.stdio_utf8 import configure_stdio_utf8

configure_stdio_utf8()

from app import create_app
from app.services.rule_service import RuleService

PROJECT = BACKEND.parent
RULE_FILE = PROJECT / "需求相关" / "分类规则全维度拆分_最新版.xlsx"


def main():
    app = create_app()
    with app.app_context():
        if not RULE_FILE.exists():
            print("SKIP: 规则样例文件不存在")
            return
        service = RuleService()
        result = service.import_from_excel(str(RULE_FILE), user_id=1, remark="验证脚本导入")
        print("规则导入成功:", result)

        opts = service.get_cascade_options("大类", {})
        print("大类数量:", len(opts["options"]))

        path = {"大类": "保鲜袋类", "区隔": ["保鲜袋"]}
        opts2 = service.get_cascade_options("类别", path)
        print("保鲜袋类/保鲜袋 的类别样例:", opts2["options"][:5])

        meta = service.get_field_meta("卷数", {**path, "类别": "平口", "主材质": "HDPE（雾面）", "辅材质": "点断", "包装方式": "盒装"})
        print("卷数控件:", meta)


if __name__ == "__main__":
    main()
