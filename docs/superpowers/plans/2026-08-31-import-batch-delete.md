# 按导入批次删除数据 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 管理员可在「数据导入」页按批次硬删除该批任务、匹配正式库与导入记录。

**Architecture:** 删除逻辑集中在 `ImportService.delete_batch`；`DELETE /api/imports/<id>` 仅做鉴权与异常映射；前端在 `ImportList.vue` 操作列加确认删除。正式库只删 `batch_id` 仍等于本批次的行。

**Tech Stack:** Flask、SQLAlchemy、Vue 3、Element Plus、unittest

## Global Constraints

- 规格以 `docs/superpowers/specs/2026-08-31-import-batch-delete-design.md` 为准
- 仅管理员可删；`processing` 批次拒绝删除
- 正式库：仅删 `ApprovedProduct.batch_id == batch_id`；已被其他批次覆盖的保留
- 任务侧 `task_drafts` / `field_change_logs` / `assignment_logs` / `review_logs` 随任务删除；`operation_logs` 保留并新增 `delete_import_batch`
- 磁盘文件尽力删除，失败不影响接口成功
- 中文注释；SOLID / DRY / KISS
- **不自动 git commit**（除非用户明确要求）

## Files

- Modify: `backend/app/services/import_service.py` — 新增 `delete_batch`
- Modify: `backend/app/api/imports.py` — 新增 `DELETE /<batch_id>`
- Create: `backend/tests/test_import_batch_delete.py` — 服务层删除用例（连本机 MySQL，数据前缀隔离）
- Modify: `frontend/src/api/imports.js` — `deleteImportApi`
- Modify: `frontend/src/views/admin/ImportList.vue` — 删除按钮与确认框
- Modify: `README.md` — 补充按批次删除说明

---

### Task 1: ImportService.delete_batch（TDD）

**Files:**
- Create: `backend/tests/test_import_batch_delete.py`
- Modify: `backend/app/services/import_service.py`

**Interfaces:**
- Consumes: 现有模型与 `write_operation_log`
- Produces:
  - `ImportService.delete_batch(batch_id: int, operator_id: int) -> dict`
  - 成功返回：`{"batch_no": str, "deleted_tasks": int, "deleted_approved": int}`
  - 批次不存在：`ValueError("批次不存在")`（或自定义，API 映射 404）
  - `processing`：`ValueError("批次正在导入中，请稍后再试")`

- [ ] **Step 1: 写失败测试（覆盖规格测试要点 1–3、5）**

在 `backend/tests/test_import_batch_delete.py` 创建用例（从 `backend` 目录运行；用唯一 `batch_no` 前缀 `UT_DEL_`，`tearDown` / `finally` 清理残留）：

```python
"""按导入批次删除 — ImportService 单测。"""
import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from app.extensions import db
from app.models.approved import ApprovedProduct, ApprovedProductHistory
from app.models.log import AssignmentLog, FieldChangeLog, OperationLog, ReviewLog
from app.models.task import ClassificationTask, ImportBatch, TaskDraft
from app.services.import_service import ImportService


class DeleteBatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.ctx = cls.app.app_context()
        cls.ctx.push()

    @classmethod
    def tearDownClass(cls):
        cls.ctx.pop()

    def _make_batch(self, suffix: str, status: str = "completed") -> ImportBatch:
        batch = ImportBatch(
            batch_no=f"UT_DEL_{suffix}",
            file_name="t.xlsx",
            file_path="",
            total_rows=1,
            success_rows=1,
            fail_rows=0,
            status=status,
            uploaded_by=1,
        )
        db.session.add(batch)
        db.session.flush()
        return batch

    def _make_task(self, batch_id: int, product_id: str) -> ClassificationTask:
        task = ClassificationTask(
            batch_id=batch_id,
            product_id=product_id,
            product_name="n",
            platform="淘宝",
        )
        db.session.add(task)
        db.session.flush()
        return task

    def test_delete_tasks_only(self):
        batch = self._make_batch("tasks_only")
        task = self._make_task(batch.id, "P_TASK_ONLY")
        TaskDraft(task_id=task.id, assignee_id=1, draft_json={"a": 1})
        db.session.commit()
        bid = batch.id
        svc = ImportService(Path(self.app.config["UPLOAD_FOLDER"]))
        result = svc.delete_batch(bid, operator_id=1)
        self.assertEqual(result["deleted_tasks"], 1)
        self.assertEqual(result["deleted_approved"], 0)
        self.assertIsNone(ImportBatch.query.get(bid))
        self.assertEqual(ClassificationTask.query.filter_by(batch_id=bid).count(), 0)

    def test_delete_approved_same_batch(self):
        batch = self._make_batch("appr_same")
        task = self._make_task(batch.id, "P_APPR_SAME")
        ap = ApprovedProduct(
            product_id="P_APPR_SAME",
            product_name="n",
            platform="淘宝",
            source_task_id=task.id,
            batch_id=batch.id,
        )
        db.session.add(ap)
        db.session.flush()
        db.session.add(
            ApprovedProductHistory(
                approved_product_id=ap.id,
                version=1,
                snapshot_json={"product_id": "P_APPR_SAME"},
            )
        )
        db.session.commit()
        bid = batch.id
        result = ImportService(Path(self.app.config["UPLOAD_FOLDER"])).delete_batch(
            bid, operator_id=1
        )
        self.assertEqual(result["deleted_approved"], 1)
        self.assertIsNone(ApprovedProduct.query.filter_by(product_id="P_APPR_SAME").first())

    def test_keep_approved_overwritten_by_other_batch(self):
        batch_old = self._make_batch("appr_old")
        batch_new = self._make_batch("appr_new")
        self._make_task(batch_old.id, "P_OVERWRITE")
        ap = ApprovedProduct(
            product_id="P_OVERWRITE",
            product_name="n",
            platform="淘宝",
            batch_id=batch_new.id,  # 已被新批次覆盖
        )
        db.session.add(ap)
        db.session.commit()
        old_id = batch_old.id
        ImportService(Path(self.app.config["UPLOAD_FOLDER"])).delete_batch(
            old_id, operator_id=1
        )
        kept = ApprovedProduct.query.filter_by(product_id="P_OVERWRITE").first()
        self.assertIsNotNone(kept)
        self.assertEqual(kept.batch_id, batch_new.id)
        # 清理新批次与正式库，避免污染
        db.session.delete(kept)
        db.session.delete(batch_new)
        db.session.commit()

    def test_reject_processing(self):
        batch = self._make_batch("processing", status="processing")
        db.session.commit()
        bid = batch.id
        with self.assertRaises(ValueError) as ctx:
            ImportService(Path(self.app.config["UPLOAD_FOLDER"])).delete_batch(
                bid, operator_id=1
            )
        self.assertIn("导入中", str(ctx.exception))
        self.assertIsNotNone(ImportBatch.query.get(bid))
        db.session.delete(ImportBatch.query.get(bid))
        db.session.commit()


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑测试确认失败**

```bat
cd backend
python -m unittest tests.test_import_batch_delete -v
```

Expected: `AttributeError` 或 `ImportError`（尚无 `delete_batch`）

- [ ] **Step 3: 实现 `ImportService.delete_batch`**

在 `import_service.py` 增加方法（要点，实现时补全中文注释与 import）：

```python
def delete_batch(self, batch_id: int, operator_id: int) -> dict:
    """按批次硬删除任务、匹配正式库与导入记录。"""
    from app.models.approved import ApprovedProduct, ApprovedProductHistory
    from app.models.log import AssignmentLog, FieldChangeLog, ReviewLog
    from app.models.task import TaskDraft

    batch = ImportBatch.query.get(batch_id)
    if not batch:
        raise ValueError("批次不存在")
    if batch.status == "processing":
        raise ValueError("批次正在导入中，请稍后再试")

    batch_no = batch.batch_no
    file_path = batch.file_path
    error_report_path = batch.error_report_path

    tasks = ClassificationTask.query.filter_by(batch_id=batch_id).all()
    task_ids = [t.id for t in tasks]
    approved_rows = ApprovedProduct.query.filter_by(batch_id=batch_id).all()
    approved_ids = [a.id for a in approved_rows]
    deleted_tasks = len(task_ids)
    deleted_approved = len(approved_ids)

    try:
        if task_ids:
            TaskDraft.query.filter(TaskDraft.task_id.in_(task_ids)).delete(
                synchronize_session=False
            )
            FieldChangeLog.query.filter(FieldChangeLog.task_id.in_(task_ids)).delete(
                synchronize_session=False
            )
            AssignmentLog.query.filter(AssignmentLog.task_id.in_(task_ids)).delete(
                synchronize_session=False
            )
            ReviewLog.query.filter(ReviewLog.task_id.in_(task_ids)).delete(
                synchronize_session=False
            )
        if approved_ids:
            ApprovedProductHistory.query.filter(
                ApprovedProductHistory.approved_product_id.in_(approved_ids)
            ).delete(synchronize_session=False)
            ApprovedProduct.query.filter(ApprovedProduct.id.in_(approved_ids)).delete(
                synchronize_session=False
            )
        if task_ids:
            ClassificationTask.query.filter(
                ClassificationTask.id.in_(task_ids)
            ).delete(synchronize_session=False)
        db.session.delete(batch)
        write_operation_log(
            operator_id,
            "delete_import_batch",
            "import_batch",
            batch_id,
            {
                "batch_no": batch_no,
                "deleted_tasks": deleted_tasks,
                "deleted_approved": deleted_approved,
            },
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    for path_str in (file_path, error_report_path):
        if not path_str:
            continue
        try:
            p = Path(path_str)
            if p.is_file():
                p.unlink()
        except OSError:
            # 文件删除失败不影响业务结果
            pass

    return {
        "batch_no": batch_no,
        "deleted_tasks": deleted_tasks,
        "deleted_approved": deleted_approved,
    }
```

注意：`ApprovedProduct.platform` 等字段按模型必填约束填充测试数据；若测试插入失败，对照 `ClassificationTask` / `ApprovedProduct` 模型补齐必填列。

- [ ] **Step 4: 再跑测试确认通过**

```bat
cd backend
python -m unittest tests.test_import_batch_delete -v
```

Expected: 全部 `ok`

---

### Task 2: DELETE API

**Files:**
- Modify: `backend/app/api/imports.py`

**Interfaces:**
- Consumes: `ImportService.delete_batch(batch_id, operator_id) -> dict`
- Produces: `DELETE /api/imports/<int:batch_id>`，`admin_required`

- [ ] **Step 1: 增加路由**

```python
@imports_bp.delete("/<int:batch_id>")
@admin_required
def delete_import_batch(batch_id: int):
    """按批次删除导入数据（任务、匹配正式库、批次记录）。"""
    service = ImportService(Path(current_app.config["UPLOAD_FOLDER"]))
    try:
        result = service.delete_batch(batch_id, g.current_user.id)
    except ValueError as exc:
        msg = str(exc)
        code = 404 if "不存在" in msg else 400
        return fail(msg, code)
    except Exception as exc:
        db.session.rollback()
        return fail(f"删除失败：{exc}", 500)
    return success(result, message="删除完成")
```

- [ ] **Step 2: 手工或用 Flask test_client 冒烟（管理员 token）**

```bat
REM 示例：用已有管理员登录拿到 token 后
curl -X DELETE http://127.0.0.1:5000/api/imports/999999 -H "Authorization: Bearer <token>"
```

Expected：不存在批次时 `code`/消息为批次不存在（404）

- [ ] **Step 3: 补测非管理员拒绝（规格要点 4）**

在 `test_import_batch_delete.py` 增加 API 级用例，或用操作员 token 调 `DELETE` 期望 403。若暂不写自动化，则在 README 验收清单写明手工验证。

推荐最小自动化（同文件增加）：

```python
def test_api_non_admin_forbidden(self):
    # 若项目无现成造用户/JWT 辅助，本步可改为手工验收并在本计划 Task 4 勾选
    pass
```

实现时优先：用 `Flask-JWT-Extended` 为操作员角色签发 token，`client.delete` 断言 403；若成本过高则 Task 4 手工验收并在测试文件注释说明。

---

### Task 3: 前端删除入口

**Files:**
- Modify: `frontend/src/api/imports.js`
- Modify: `frontend/src/views/admin/ImportList.vue`

**Interfaces:**
- Consumes: `DELETE /api/imports/{id}` → `{ batch_no, deleted_tasks, deleted_approved }`
- Produces: `deleteImportApi(id)`；列表「删除」按钮

- [ ] **Step 1: API 封装**

```js
export function deleteImportApi(id) {
  return request.delete(`/imports/${id}`)
}
```

- [ ] **Step 2: ImportList 操作列**

- 加宽操作列（如 `width="200"`）
- 增加危险样式「删除」按钮
- 使用 `ElMessageBox.confirm`：

文案示例：`确定删除批次 ${row.batch_no}？将删除该批次下任务及仍归属该批次的正式库数据，且不可恢复。`

- 确认后调用 `deleteImportApi(row.id)`
- 成功：`ElMessage.success(\`已删除任务 ${res.data.deleted_tasks} 条、正式库 ${res.data.deleted_approved} 条\`)`，再 `loadBatches()`
- 取消：无操作；错误：依赖现有 request 拦截器

- [ ] **Step 3: 浏览器验收**

管理员打开「数据导入」→ 对测试批次点删除 → 确认 → 列表刷新且该批次消失。

---

### Task 4: README 与收尾验收

**Files:**
- Modify: `README.md`

- [ ] **Step 1: README「当前进度 / 数据导入」行补充「支持按批次删除」**
- [ ] **Step 2: 「主要 API」表增加 `DELETE /api/imports/{id}`**
- [ ] **Step 3: 对照规格验收清单勾选**

| 项 | 期望 |
|----|------|
| 管理员可删 | 通过 |
| 确认后才删 | 通过 |
| 任务+任务侧日志+匹配正式库+批次记录消失 | 通过 |
| 被覆盖正式库保留 | 通过（Task 1 单测） |
| 操作日志有 `delete_import_batch` | 查库或日志页 |
| 非管理员 / processing | 拒绝 |

- [ ] **Step 4: 再跑一遍单元测试确认无回归**

```bat
cd backend
python -m unittest tests.test_import_batch_delete -v
```

---

## Spec coverage（自检）

| 规格项 | 任务 |
|--------|------|
| 列表删除入口 + 确认弹窗 | Task 3 |
| 仅管理员 | Task 2 + Task 4 |
| 删草稿/任务日志/任务/匹配正式库/历史/批次 | Task 1 |
| 覆盖保留 | Task 1 `test_keep_approved_overwritten...` |
| processing 拒绝 | Task 1 |
| 操作日志 | Task 1 实现 |
| 磁盘尽力删 | Task 1 实现 |
| README | Task 4 |

## 执行说明

Plan 已保存。实现时请按 Task 顺序；默认不 commit。
