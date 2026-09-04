# 审核中心与导出页筛选增强 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 审核中心按操作员多选筛选；导出任务支持状态/平台/操作员多选；导出正式库平台多选。

**Architecture:** 在 `query_filters.py` 增加可复用的 `apply_assignee_id_filter` / `apply_csv_in_filter`（或平台/状态专用小函数）；审核列表与任务导出共用。前端 ReviewList / ExportPage 用多选 + `join(',')` 传参。

**Tech Stack:** Flask、SQLAlchemy、Vue 3、Element Plus、unittest

## Global Constraints

- 规格：`docs/superpowers/specs/2026-09-04-review-export-filters-design.md`
- 操作员选项：仅 `role=operator` 且 `is_active=true`
- 多选语义为「或」；空参数不筛
- 正式库不加操作员筛选
- 中文注释；SOLID / DRY / KISS
- **不自动 git commit**（除非用户明确要求）

## Files

- Modify: `backend/app/utils/query_filters.py`
- Modify: `backend/app/api/reviews.py`
- Modify: `backend/app/services/export_service.py`
- Modify: `backend/app/api/export.py`（透传 `assignee_id`）
- Create: `backend/tests/test_review_export_filters.py`
- Modify: `frontend/src/views/admin/ReviewList.vue`
- Modify: `frontend/src/views/admin/ExportPage.vue`
- Modify: `README.md`（若有筛选能力描述则补充一句）

---

### Task 1: 后端筛选工具 + 审核/导出（TDD）

**Files:**
- Modify: `backend/app/utils/query_filters.py`
- Modify: `backend/app/api/reviews.py`
- Modify: `backend/app/services/export_service.py`
- Modify: `backend/app/api/export.py`
- Create: `backend/tests/test_review_export_filters.py`

**Interfaces:**
- Produces:
  - `apply_assignee_id_filter(query, model, assignee_id=None)`
  - `apply_platform_filter(query, model, platform=None)` — 逗号多值 `in_`
  - `apply_status_filter(query, model, status=None)` — 逗号多值且仅保留 `TASK_STATUSES` 中的合法值
- `filter_tasks(..., assignee_id=None)` 使用上述工具
- `_paginate_review_list` 使用 `apply_assignee_id_filter`
- `export_tasks` API 传入 `assignee_id=request.args.get("assignee_id")`

- [ ] **Step 1: 写失败/行为测试**

在 `backend/tests/test_review_export_filters.py` 用 unittest + `create_app`，前缀 `UT_REF_`：

1. `ExportService.filter_tasks(status="待处理,待审核")` → 只含这两种状态（造 2～3 条任务）
2. `filter_tasks(platform="淘宝,京东")` → 并集
3. `filter_tasks(assignee_id="id1,id2")` → 并集
4. `filter_tasks()` 无参 → 不过滤上述字段
5. 用 test_client `GET /api/reviews/pending?assignee_id=a,b`（管理员 token）断言返回条数（或至少 200 且 items 的 assignee_id 均在集合内）——若造数成本高，至少测 `parse`/`filter_tasks` 三层即可，审核 API 测一条多选

测试需清理 `UT_REF_` 用户与任务。

- [ ] **Step 2: 跑测试确认 RED**

```bat
cd backend
..\.venv\Scripts\python.exe -m unittest tests.test_review_export_filters -v
```

- [ ] **Step 3: 实现工具函数**

```python
def apply_assignee_id_filter(query, model, assignee_id=None):
    """按负责人 ID 筛选（支持多选）。"""
    ids = parse_int_ids(assignee_id)
    if not ids:
        return query
    return query.filter(model.assignee_id.in_(ids))


def apply_platform_filter(query, model, platform=None):
    """按平台筛选（支持逗号多选）。"""
    platforms = parse_csv_arg(platform)
    if not platforms:
        return query
    if len(platforms) == 1:
        return query.filter_by(platform=platforms[0])
    return query.filter(model.platform.in_(platforms))


def apply_status_filter(query, model, status=None):
    """按任务状态筛选（支持逗号多选，仅保留合法状态）。"""
    from app.constants import TASK_STATUSES

    statuses = [s for s in parse_csv_arg(status) if s in TASK_STATUSES]
    if not statuses:
        return query
    if len(statuses) == 1:
        return query.filter_by(status=statuses[0])
    return query.filter(model.status.in_(statuses))
```

- [ ] **Step 4: 接入 reviews / export_service / export API**

`filter_tasks`：

```python
def filter_tasks(self, status=None, platform=None, batch_id=None, keyword=None,
                 category_large=None, category_segment=None, assignee_id=None):
    from app.utils.query_filters import (
        apply_assignee_id_filter,
        apply_batch_id_filter,
        apply_category_filters,
        apply_platform_filter,
        apply_status_filter,
    )
    query = ClassificationTask.query
    query = apply_status_filter(query, ClassificationTask, status)
    query = apply_platform_filter(query, ClassificationTask, platform)
    query = apply_assignee_id_filter(query, ClassificationTask, assignee_id)
    query = apply_batch_id_filter(query, ClassificationTask, batch_id)
    # keyword + category 保持现有逻辑
    ...
```

`filter_approved` 的 platform 分支改为调用 `apply_platform_filter`。

`export.py` `filter_tasks(...)` 增加 `assignee_id=request.args.get("assignee_id")`。

`reviews.py` 用 `apply_assignee_id_filter` 替换单值判断；import `parse_int_ids` 或直接 import 新函数。

- [ ] **Step 5: 测试 GREEN**

```bat
cd backend
..\.venv\Scripts\python.exe -m unittest tests.test_review_export_filters -v
```

---

### Task 2: 审核中心前端操作员筛选

**Files:**
- Modify: `frontend/src/views/admin/ReviewList.vue`

**Interfaces:**
- Consumes: `listUsersApi`、现有 `buildQueryParams` / `withBatchParams`

- [ ] **Step 1:** `onMounted` 拉用户列表，过滤启用操作员 → `operatorOptions`（`{ id, username }`）
- [ ] **Step 2:** 批次与大类之间加「操作员」`el-select` multiple / filterable / clearable / collapse-tags
- [ ] **Step 3:** `buildQueryParams` 附加 `assignee_id: selected.join(',')`（有选中时）
- [ ] **Step 4:** `handleReset` 清空选择

---

### Task 3: 导出页前端多选

**Files:**
- Modify: `frontend/src/views/admin/ExportPage.vue`

- [ ] **Step 1:** 任务表单：`status` / `platform` / `assignee_id` 改为数组 + multiple select；加载启用操作员选项
- [ ] **Step 2:** 正式库：`platform` 改为数组 + multiple
- [ ] **Step 3:** 导出时：

```js
await downloadTasksExport({
  status: taskFilters.status.length ? taskFilters.status.join(',') : undefined,
  platform: taskFilters.platform.length ? taskFilters.platform.join(',') : undefined,
  assignee_id: taskFilters.assigneeIds.length ? taskFilters.assigneeIds.join(',') : undefined,
  keyword: taskFilters.keyword || undefined,
})
```

正式库同理只传 `platform` join。

---

### Task 4: README 与验收

- [ ] README「当前进度」相关行补充：审核中心可按操作员筛选；导出支持状态/平台/操作员多选（措辞简洁）
- [ ] 复跑 `tests.test_review_export_filters`
- [ ] 报告标注：自动化 vs 浏览器点测（审核筛选、导出下载）

---

## Spec coverage

| 规格项 | 任务 |
|--------|------|
| 审核 assignee 多选 | Task 1 + 2 |
| 任务导出 status/platform/assignee 多选 | Task 1 + 3 |
| 正式库 platform 多选 | Task 1（复用）+ 3 |
| 启用操作员选项 | Task 2 + 3 |
| README | Task 4 |

## 执行说明

默认不 commit。实现后需重启后端热重载，避免路由/逻辑未刷新。
