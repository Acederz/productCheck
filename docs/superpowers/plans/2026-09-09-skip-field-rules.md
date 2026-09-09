# 无需填写字段规则 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按大类禁用指定分类字段（灰掉清空），管理员单独导入 Excel，暂存/提交后端强制拦截。

**Architecture:** 独立 `skip_field_rule_versions` / `skip_field_rules` 表与 `SkipFieldRuleService`；API 提供导入/版本/按大类查禁用字段；`TaskService` 在 `update_task` / `save_draft` / `_validate_for_submit` 强制校验；前端填写控件按禁用列表 `disabled` 并清空。

**Tech Stack:** Flask、SQLAlchemy、openpyxl、Vue 3、Element Plus、unittest

## Global Constraints

- 规格：`docs/superpowers/specs/2026-09-09-skip-field-rules-design.md`
- 仅按「大类」精确匹配；忽略 Excel「区隔」列
- 单元格「无」→ 禁用；前端灰掉清空；暂存/提交存空
- 后端有值则拒绝（不静默清空）；禁用字段免必填
- 单独导入、全量覆盖、只读最新版本；优先级高于级联规则
- 中文注释；SOLID / DRY / KISS
- **不自动 git commit**（除非用户明确要求）

## Files

- Create: `backend/app/models/skip_field_rule.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/app/services/skip_field_rule_service.py`
- Create: `backend/app/api/skip_field_rules.py`
- Modify: `backend/app/api/__init__.py`
- Modify: `backend/app/services/task_service.py`
- Modify: `backend/app/utils/log_display.py`
- Modify: `backend/app/api/users.py`（删除操作员时置空 `created_by`）
- Create: `backend/tests/test_skip_field_rules.py`
- Create: `frontend/src/api/skipFieldRules.js`
- Modify: `frontend/src/views/admin/RuleManage.vue`
- Modify: `frontend/src/composables/useClassificationCascade.js`
- Modify: `frontend/src/views/operator/MyTasks.vue`
- Modify: `frontend/src/components/ClassificationForm.vue`（若仍被使用）
- Modify: `README.md`

### 字段映射常量（全任务共用）

```python
# 中文列名 -> 任务/API 英文字段（可禁用列；不含大类/区隔）
SKIP_FIELD_CN_TO_EN = {
    "类别": "category_type",
    "主材质": "material_main",
    "辅材质": "material_aux",
    "包装方式": "packaging",
    "尺寸": "size",
    "卷数": "roll_count",
    "总入数": "total_count",
}
SKIP_FIELD_EN_TO_CN = {v: k for k, v in SKIP_FIELD_CN_TO_EN.items()}
```

---

### Task 1: 模型 + SkipFieldRuleService（导入与查询，TDD）

**Files:**
- Create: `backend/app/models/skip_field_rule.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/app/services/skip_field_rule_service.py`
- Create: `backend/tests/test_skip_field_rules.py`

**Interfaces:**
- Produces:
  - `SkipFieldRuleVersion` / `SkipFieldRule` 模型
  - `SkipFieldRuleService.get_latest_version() -> SkipFieldRuleVersion | None`
  - `SkipFieldRuleService.get_disabled_fields(category_large: str) -> list[str]`（英文字段名）
  - `SkipFieldRuleService.import_from_excel(file_path: str, user_id: int | None, remark: str = "") -> dict`

- [ ] **Step 1: 写失败测试（服务层）**

在 `backend/tests/test_skip_field_rules.py`：

```python
"""无需填写字段规则：导入解析与按大类查询。"""
import sys
import tempfile
import unittest
from pathlib import Path

import openpyxl
from openpyxl import Workbook

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from app.extensions import db
from app.models.skip_field_rule import SkipFieldRule, SkipFieldRuleVersion
from app.services.skip_field_rule_service import SkipFieldRuleService

UT_PREFIX = "UT_SKIP_"


class SkipFieldRuleServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.ctx = cls.app.app_context()
        cls.ctx.push()

    @classmethod
    def tearDownClass(cls):
        cls._cleanup()
        cls.ctx.pop()

    @classmethod
    def _cleanup(cls):
        db.session.rollback()
        versions = SkipFieldRuleVersion.query.filter(
            SkipFieldRuleVersion.version_no.like(f"{UT_PREFIX}%")
        ).all()
        ids = [v.id for v in versions]
        if ids:
            SkipFieldRule.query.filter(SkipFieldRule.version_id.in_(ids)).delete(
                synchronize_session=False
            )
            SkipFieldRuleVersion.query.filter(SkipFieldRuleVersion.id.in_(ids)).delete(
                synchronize_session=False
            )
            db.session.commit()

    def tearDown(self):
        self._cleanup()

    def _write_xlsx(self, rows: list[tuple]) -> str:
        wb = Workbook()
        ws = wb.active
        headers = ["大类", "区隔", "类别", "主材质", "辅材质", "包装方式", "尺寸", "卷数", "总入数"]
        ws.append(headers)
        for row in rows:
            ws.append(list(row))
        fd, path = tempfile.mkstemp(suffix=".xlsx")
        import os
        os.close(fd)
        wb.save(path)
        return path

    def test_import_and_query_by_large(self):
        path = self._write_xlsx(
            [
                ("拖把类", None, None, None, None, None, None, "无", "无"),
                ("手套类", None, None, None, None, None, None, None, "无"),
            ]
        )
        svc = SkipFieldRuleService()
        # 测试里用可控 version_no：实现可接受 remark 含 UT_PREFIX，或测试后改 version_no
        result = svc.import_from_excel(path, user_id=None, remark=f"{UT_PREFIX}t1")
        self.assertGreaterEqual(result["rule_count"], 2)
        # 将最新 version_no 改成 UT 前缀便于清理（若服务已用 v时间戳）
        ver = svc.get_latest_version()
        self.assertIsNotNone(ver)
        ver.version_no = f"{UT_PREFIX}{ver.version_no}"
        db.session.commit()

        self.assertEqual(
            sorted(svc.get_disabled_fields("拖把类")),
            ["roll_count", "total_count"],
        )
        self.assertEqual(svc.get_disabled_fields("手套类"), ["total_count"])
        self.assertEqual(svc.get_disabled_fields("保鲜膜类"), [])
        self.assertEqual(svc.get_disabled_fields(""), [])

    def test_full_replace_on_reimport(self):
        path1 = self._write_xlsx([("拖把类", None, None, None, None, None, None, "无", "无")])
        path2 = self._write_xlsx([("刷子类", None, None, None, None, None, None, "无", None)])
        svc = SkipFieldRuleService()
        svc.import_from_excel(path1, None, f"{UT_PREFIX}a")
        v1 = svc.get_latest_version()
        v1.version_no = f"{UT_PREFIX}a_{v1.id}"
        db.session.commit()
        svc.import_from_excel(path2, None, f"{UT_PREFIX}b")
        v2 = svc.get_latest_version()
        v2.version_no = f"{UT_PREFIX}b_{v2.id}"
        db.session.commit()
        self.assertEqual(svc.get_disabled_fields("拖把类"), [])
        self.assertEqual(svc.get_disabled_fields("刷子类"), ["roll_count"])

    def test_missing_large_header_raises(self):
        wb = Workbook()
        ws = wb.active
        ws.append(["区隔", "卷数"])
        ws.append(["x", "无"])
        fd, path = tempfile.mkstemp(suffix=".xlsx")
        import os
        os.close(fd)
        wb.save(path)
        with self.assertRaises(ValueError):
            SkipFieldRuleService().import_from_excel(path, None, f"{UT_PREFIX}bad")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 运行确认失败**

```bash
cd backend
python -m unittest tests.test_skip_field_rules -v
```

Expected: FAIL（模块/类不存在）

- [ ] **Step 3: 实现模型**

`backend/app/models/skip_field_rule.py`：

```python
"""无需填写字段规则模型。"""

from datetime import datetime

from app.extensions import db


class SkipFieldRuleVersion(db.Model):
    """无需填写字段规则版本。"""

    __tablename__ = "skip_field_rule_versions"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    version_no = db.Column(db.String(32), nullable=False, unique=True)
    remark = db.Column(db.String(255), nullable=True)
    created_by = db.Column(db.BigInteger, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class SkipFieldRule(db.Model):
    """按大类禁用的字段列表。"""

    __tablename__ = "skip_field_rules"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    version_id = db.Column(
        db.BigInteger, db.ForeignKey("skip_field_rule_versions.id"), nullable=False
    )
    category_large = db.Column(db.String(128), nullable=False, index=True)
    disabled_fields = db.Column(db.JSON, nullable=False, default=list)  # 中文列名
    is_active = db.Column(db.Boolean, nullable=False, default=True)
```

在 `models/__init__.py` 导出并加入 `__all__`。确保 `create_app` / `init-db` 的 `db.create_all()` 能建表（项目已 import models）。

- [ ] **Step 4: 实现 SkipFieldRuleService**

要点：
- `version_no = datetime.now().strftime("v%Y%m%d%H%M%S")`（与分类规则一致）
- 读首个 sheet；表头必须含「大类」；忽略列名「区隔」与「大类」本身
- 单元格去空格后等于「无」才计入；同大类多行取并集
- `disabled_fields` **库内存中文列名**；`get_disabled_fields` **返回英文字段名**
- 无任何「无」的大类行可不写库，或写空数组（推荐：有「无」才写行，查询未命中返回 `[]`）
- `import_from_excel` 返回 `{"version_no", "rule_count"}`；`db.session.commit()` 在服务内完成（与 `RuleService.import_from_excel` 对齐；若现有规则服务在 API 层 commit，则与其保持一致）

查看 `RuleService.import_from_excel` 的 commit 位置并对齐。

- [ ] **Step 5: 跑通测试**

```bash
cd backend
python manage.py init-db
python -m unittest tests.test_skip_field_rules -v
```

Expected: PASS

- [ ] **Step 6: （可选）用户要求时再 commit**

---

### Task 2: HTTP API

**Files:**
- Create: `backend/app/api/skip_field_rules.py`
- Modify: `backend/app/api/__init__.py`
- Modify: `backend/app/utils/log_display.py`
- Modify: `backend/tests/test_skip_field_rules.py`

**Interfaces:**
- Produces:
  - `POST /api/skip-field-rules/import`（`admin_required`，multipart `file` + 可选 `remark`）
  - `GET /api/skip-field-rules/version`（`login_required`）
  - `GET /api/skip-field-rules/disabled-fields?category_large=`（`login_required`）

- [ ] **Step 1: 扩展测试（API 冒烟）**

```python
from flask_jwt_extended import create_access_token
from app.constants import ROLE_ADMIN, ROLE_OPERATOR
from app.models.user import User

# 在同一测试文件增加：
class SkipFieldRuleApiTests(unittest.TestCase):
    # setUpClass 同服务测；用 admin/operator token
    def test_disabled_fields_api(self):
        # 先 import_from_excel 写入拖把类规则并 UT 前缀 version
        # GET /api/skip-field-rules/disabled-fields?category_large=拖把类
        # assert data == ["roll_count","total_count"]（顺序可用 set 比较）
        ...

    def test_import_requires_admin(self):
        # operator POST import → 403
        ...
```

- [ ] **Step 2: 实现 blueprint**

参考 `backend/app/api/rules.py`：
- 上传保存到 `UPLOAD_FOLDER`，文件名 `skip_field_rules_{filename}`
- 成功 `write_operation_log(..., "import_skip_field_rules", "skip_field_rule_version", version_id, {...})`
- `version`：无数据时 `success(None, message="尚未导入无需填写字段规则")`
- `disabled-fields`：`success({"fields": [...]})` 或直接 `success([...])`——**选定一种并在前端对齐**；推荐 `success({"fields": list})`

注册：`app.register_blueprint(skip_field_rules_bp, url_prefix="/api/skip-field-rules")`

`log_display.py` 增加：
- `ACTION_LABELS["import_skip_field_rules"] = "导入无需填写字段规则"`
- `TARGET_TYPE_LABELS["skip_field_rule_version"] = "无需填写规则版本"`

- [ ] **Step 3: 跑测试**

```bash
cd backend
python -m unittest tests.test_skip_field_rules -v
```

Expected: PASS

---

### Task 3: TaskService 强制校验（暂存 / 更新 / 提交）

**Files:**
- Modify: `backend/app/services/task_service.py`
- Modify: `backend/tests/test_skip_field_rules.py`

**Interfaces:**
- Consumes: `SkipFieldRuleService.get_disabled_fields`
- Produces: `_assert_no_disabled_field_values(category_large, payload: dict) -> None`（违规 `raise ValueError`）；`_validate_for_submit` 跳过禁用必填项

- [ ] **Step 1: 写失败测试**

```python
from app.constants import ROLE_OPERATOR, TASK_STATUS_PENDING
from app.models.task import ClassificationTask, TaskDraft
from app.models.user import User
from app.services.task_service import TaskService

class SkipFieldTaskValidationTests(unittest.TestCase):
    # 准备：导入拖把类禁用 roll/total；创建操作员 + 待处理任务，assignee=op

    def test_save_draft_rejects_disabled_value(self):
        svc = TaskService()
        with self.assertRaises(ValueError) as ctx:
            svc.save_draft(
                self.task_id,
                self.op_id,
                {"category_large": "拖把类", "roll_count": "2卷"},
            )
        self.assertIn("卷数", str(ctx.exception))

    def test_submit_skips_required_when_category_type_disabled(self):
        # 湿巾类：类别禁用；任务 is_operating=是，大类=湿巾类，有区隔，类别空
        # _validate_for_submit 应返回 None（不因缺类别失败）
        ...

    def test_update_task_rejects_disabled_value(self):
        # update_task 写入 total_count 有值 → ValueError
        ...
```

- [ ] **Step 2: 实现校验辅助**

在 `task_service.py`：

```python
def _field_has_value(self, value) -> bool:
    if value is None:
        return False
    if isinstance(value, list):
        return any(str(v).strip() for v in value)
    return bool(str(value).strip())

def _assert_no_disabled_field_values(self, category_large: str | None, data: dict) -> None:
    """禁用字段不得带非空值（不静默清空）。"""
    from app.services.skip_field_rule_service import (
        SKIP_FIELD_EN_TO_CN,
        SkipFieldRuleService,
    )
    large = self._normalize_category_large(category_large) if category_large else None
    disabled = SkipFieldRuleService().get_disabled_fields(large or "")
    for en in disabled:
        if en in data and self._field_has_value(data.get(en)):
            cn = SKIP_FIELD_EN_TO_CN.get(en, en)
            raise ValueError(f"{cn}无需填写")
```

- `save_draft`：在写库前，用 `draft_json` 的 `category_large`（或任务上已有大类）调用 `_assert_no_disabled_field_values`
- `update_task`：在 `_apply_editable_fields` 之前，用合并后的大类（`data` 优先否则 `task.category_large`）+ `data` 校验
- `_validate_for_submit`：
  1. 先对任务当前字段组 payload 做禁用有值检查
  2. 必填循环：若字段英文名在禁用列表则 `continue`；**区隔**仅当未来可禁用时才跳过（当前映射不含区隔，保持必填）

注意：提交校验读的是 **任务表字段**，不是草稿。操作员提交前通常已 `update_task`。若产品流程是只暂存再提交，确认 `submit_tasks` 是否先合并草稿——若否，前端提交前必须先保存。保持与现网一致，本任务只增强校验。

- [ ] **Step 3: 跑测试**

```bash
cd backend
python -m unittest tests.test_skip_field_rules -v
```

Expected: PASS

- [ ] **Step 4: 删除操作员时置空 FK**

在 `backend/app/api/users.py` 删除清理处增加：

```python
from app.models.skip_field_rule import SkipFieldRuleVersion
SkipFieldRuleVersion.query.filter_by(created_by=user_id).update(
    {SkipFieldRuleVersion.created_by: None}, synchronize_session=False
)
```

---

### Task 4: 管理端导入 UI

**Files:**
- Create: `frontend/src/api/skipFieldRules.js`
- Modify: `frontend/src/views/admin/RuleManage.vue`

- [ ] **Step 1: API 封装**

```javascript
import request from './request'

export function getSkipFieldRuleVersionApi() {
  return request.get('/skip-field-rules/version')
}

export function importSkipFieldRulesApi(file, remark = '') {
  const form = new FormData()
  if (file) form.append('file', file)
  if (remark) form.append('remark', remark)
  return request.post('/skip-field-rules/import', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function getDisabledFieldsApi(categoryLarge) {
  return request.get('/skip-field-rules/disabled-fields', {
    params: { category_large: categoryLarge || '' },
  })
}
```

- [ ] **Step 2: RuleManage 增加第二张卡片**

- 标题：「无需填写字段规则」
- 说明：上传 `无需填写字段.xlsx`；每次全量覆盖；仅按大类生效
- 选择文件（必选，与分类规则「可选样例」不同——无文件则提示先选择）
- 导入按钮、当前版本 tag、上次导入 `rule_count`
- `onMounted` 同时拉分类规则版本与 skip 版本

- [ ] **Step 3: 手动验收**

浏览器登录管理员 → 规则管理 → 导入 `需求相关/无需填写字段.xlsx` → 显示版本与约 12 条。

---

### Task 5: 填写端禁用与清空

**Files:**
- Modify: `frontend/src/composables/useClassificationCascade.js`
- Modify: `frontend/src/views/operator/MyTasks.vue`
- Modify: `frontend/src/components/ClassificationForm.vue`（若页面仍引用）

**Interfaces:**
- Produces（建议放 cascade composable）:
  - `fetchDisabledFields(categoryLarge) -> Promise<string[]>`
  - `applyDisabledFields(row, disabledEnList)`：对 list 内字段清空值；写入 `rowState.disabledFields`
  - `isFieldDisabled(rowId, field) -> boolean`

- [ ] **Step 1: composable 增加禁用缓存**

```javascript
import { getDisabledFieldsApi } from '@/api/skipFieldRules'

// key = `${skipVersionId}|${large}` → string[]
const disabledFieldsCache = new Map()
let knownSkipVersionId = null

export async function syncSkipFieldVersion() {
  const res = await getSkipFieldRuleVersionApi()
  const id = res.data?.id ?? null
  if (id !== knownSkipVersionId) {
    knownSkipVersionId = id
    disabledFieldsCache.clear()
  }
  return knownSkipVersionId
}

export async function fetchDisabledFields(categoryLarge) {
  const large = normalizeSingleLarge(categoryLarge)
  if (!large) return []
  await syncSkipFieldVersion()
  const key = `${knownSkipVersionId}|${large}`
  if (disabledFieldsCache.has(key)) return disabledFieldsCache.get(key)
  const res = await getDisabledFieldsApi(large)
  const fields = res.data?.fields || res.data || []
  disabledFieldsCache.set(key, fields)
  return fields
}

export function clearDisabledFieldValues(row, disabledList) {
  for (const f of disabledList) {
    if (MULTI_SELECT_FIELDS.includes(f)) row[f] = []
    else row[f] = ''
  }
}
```

在 `onDropdownVisible` / 加载选项前：若字段在禁用列表则直接 return，不请求规则选项。

- [ ] **Step 2: MyTasks 绑定 disabled**

- 行状态增加 `disabledFields: []`
- `handleCascadeChange(row, 'category_large')` 及行数据加载后：`fetchDisabledFields` → 赋值 → `clearDisabledFieldValues`
- 各分类 `el-select` 的 `:disabled` 改为：  
  `row.is_operating === '否' || getRowState(row.id).disabledFields.includes('category_type')`（按列替换字段名）
- 暂存/提交前可再清一次禁用字段，降低后端拒绝概率

- [ ] **Step 3: ClassificationForm 同步**

同样：大类变化拉禁用列表；控件 disabled；清空。

- [ ] **Step 4: 手动验收**

1. 导入补充表后，操作员选大类「拖把类」→ 卷数、总入数灰掉且空  
2. 选「湿巾类」→ 类别等禁用；有区隔时可提交，不因缺类别失败  
3. 用接口对暂存带 `roll_count` → 报错「卷数无需填写」

---

### Task 6: README 与收尾

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 更新功能表**

在「分类规则」相关行补充：支持单独导入「无需填写字段」；按大类禁用字段；暂存/提交后端校验。

在「主要 API」表增加三条 skip-field-rules 路径。

- [ ] **Step 2: 全量后端单测**

```bash
cd backend
python -m unittest tests.test_skip_field_rules tests.test_delete_operator_user -v
```

Expected: 相关用例 PASS（删除用户用例若触碰新 FK，确认已置空）

- [ ] **Step 3: 对照规格验收清单勾选**

规格「验收标准」五条全部满足即可宣告完成。

---

## Spec coverage（自检）

| 规格项 | 任务 |
|--------|------|
| 仅大类匹配、忽略区隔 | Task 1 |
| 独立表 + 全量覆盖版本 | Task 1 |
| 导入/版本/disabled-fields API | Task 2 |
| 暂存/提交/更新强制拒绝有值 | Task 3 |
| 禁用免必填 | Task 3 |
| 管理端单独导入 | Task 4 |
| 填写灰掉清空、优先于级联 | Task 5 |
| README | Task 6 |

## 非目标（计划不实现）

- 区隔维度、版本回滚 UI、合并进分类规则 Excel、审核列表样式改造
