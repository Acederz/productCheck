# 审核中心按范围批量通过 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 审核中心支持「全部审核通过」与「按当前条件审核通过」：先查最新条数二次确认，再服务端分批通过。

**Architecture:** 抽取与 pending 列表相同的筛选查询构建；新增 count / approve-scope 两个管理端接口；`ReviewService` 先收集匹配 ID 再按批调用现有 `approve_tasks`；前端两按钮驱动确认与加长超时请求。

**Tech Stack:** Flask、SQLAlchemy、Vue 3、Element Plus、unittest

## Global Constraints

- 规格：`docs/superpowers/specs/2026-09-14-review-approve-scope-design.md`
- `scope=all` 忽略筛选；`scope=filtered` 与 pending 列表筛选一致
- 仅「待审核」；仅管理员
- count=0 不弹确认；>0 二次确认展示服务器条数
- 先收集 ID 再分批 approve（每批 100）；前端 loading 防重复
- 中文注释；SOLID / DRY / KISS
- **不自动 git commit**（除非用户明确要求）

## Files

- Modify: `backend/app/api/reviews.py` — 抽取筛选查询；新增 count / approve-scope
- Modify: `backend/app/services/review_service.py` — `approve_by_scope`
- Modify: `backend/app/utils/log_display.py` — 操作日志中文
- Create: `backend/tests/test_review_approve_scope.py`
- Modify: `frontend/src/api/reviews.js`
- Modify: `frontend/src/views/admin/ReviewList.vue`
- Modify: `README.md`

---

### Task 1: 后端筛选复用 + count / approve-scope（TDD）

**Files:**
- Modify: `backend/app/api/reviews.py`
- Modify: `backend/app/services/review_service.py`
- Modify: `backend/app/utils/log_display.py`
- Create: `backend/tests/test_review_approve_scope.py`

**Interfaces:**
- Produces:
  - `_build_pending_query(filters: dict | None, *, ignore_filters: bool) -> Query`
  - `GET /api/reviews/approve-scope-count?scope=all|filtered&...`
  - `POST /api/reviews/approve-scope` body `{scope, filters?}`
  - `ReviewService.approve_by_scope(scope, filters, admin_id) -> {success_count, skipped_count, total_matched}`

- [ ] **Step 1: 写失败测试**

`backend/tests/test_review_approve_scope.py` 要点（对齐现有 `test_delete_operator_user.py` 风格：真实 DB、UT 前缀清理）：

```python
"""审核中心按范围批量通过单测。"""
# create_app + admin token
# 创建若干 status=待审核 任务：平台淘宝/京东、不同大类
# test_count_all_ignores_filters: filtered query 有 platform=淘宝，但 scope=all count 含全部待审核
# test_count_filtered: scope=filtered&platform=淘宝 只计淘宝
# test_count_zero: 无待审核 → count 0
# test_approve_scope_filtered: 只通过淘宝，京东仍待审核；返回 success_count
# test_approve_scope_all: 全部变已通过
# test_operator_forbidden: 操作员 403
# test_invalid_scope: 400
```

- [ ] **Step 2: 运行确认 RED**

```bash
cd backend
python -m unittest tests.test_review_approve_scope -v
```

Expected: FAIL（路由/方法不存在）

- [ ] **Step 3: 抽取 pending 筛选查询**

在 `reviews.py` 将 `_paginate_review_list` 中的 filter 逻辑抽成：

```python
def _filters_from_request_args() -> dict:
    return {
        "platform": request.args.get("platform", ""),
        "keyword": request.args.get("keyword", "").strip(),
        "assignee_id": request.args.get("assignee_id", "").strip(),
        "batch_id": request.args.get("batch_id", ""),
        "category_large": request.args.get("category_large", ""),
        "category_segment": request.args.get("category_segment", ""),
    }

def _filters_from_body(data: dict) -> dict:
    f = data.get("filters") or {}
    return {
        "platform": f.get("platform") or "",
        "keyword": (f.get("keyword") or "").strip(),
        "assignee_id": (f.get("assignee_id") or "").strip() if f.get("assignee_id") is not None else "",
        "batch_id": f.get("batch_id") or "",
        "category_large": f.get("category_large") or "",
        "category_segment": f.get("category_segment") or "",
    }

def _build_pending_query(filters: dict | None = None, *, apply_filters: bool = True):
    """待审核查询；apply_filters=False 时仅按 status 过滤（全部通过）。"""
    query = ClassificationTask.query.filter_by(status=TASK_STATUS_REVIEW)
    if not apply_filters:
        return query
    filters = filters or {}
    platform_list = parse_csv_arg(filters.get("platform") or "")
    keyword = (filters.get("keyword") or "").strip()
    # …与现有 pending 完全一致的 platform/keyword/assignee/batch/category 过滤
    return query
```

`_paginate_review_list` 改为调用 `_build_pending_query(_filters_from_request_args())`。

- [ ] **Step 4: ReviewService.approve_by_scope**

```python
APPROVE_SCOPE_BATCH_SIZE = 100

def approve_by_scope(self, scope: str, filters: dict | None, admin_id: int) -> dict:
    """先收集匹配待审核 ID，再分批 approve_tasks。"""
    # 注意：approve_tasks 内部会 commit；分批调用即可
    # total_matched = len(ids)
    # 累加 success_ids / skipped
    # 另写 write_operation_log(..., "approve_tasks_scope", ..., {scope, success_count, skipped_count, filters})
```

ID 收集：由 API 层用 `_build_pending_query` 查出 `id` 列表后传入 service，**或** service 接收已构建好的 id 列表。推荐 API：

```python
query = _build_pending_query(filters, apply_filters=(scope == "filtered"))
ids = [r.id for r in query.with_entities(ClassificationTask.id).all()]
result = review_service.approve_by_scope(ids, admin_id, scope=scope, filters=filters)
```

`approve_by_scope` 对 `ids` 按 100 切片调用 `approve_tasks`。

- [ ] **Step 5: 注册两个路由**

- GET count：校验 scope ∈ {all, filtered}；返回 `{"count": n}`
- POST approve-scope：同上；body 解析；调用分批通过；message 拼「已通过 X 条」

`log_display.py`：
- `ACTION_LABELS["approve_tasks_scope"] = "按范围审核通过"`

- [ ] **Step 6: 跑通测试**

```bash
cd backend
python -m unittest tests.test_review_approve_scope -v
```

Expected: PASS

---

### Task 2: 前端按钮与确认流

**Files:**
- Modify: `frontend/src/api/reviews.js`
- Modify: `frontend/src/views/admin/ReviewList.vue`

- [ ] **Step 1: API 封装**

```javascript
export function approveScopeCountApi(params) {
  return request.get('/reviews/approve-scope-count', { params })
}

export function approveScopeApi(payload) {
  return request.post('/reviews/approve-scope', payload, { timeout: 180000 })
}
```

- [ ] **Step 2: ReviewList 增加按钮与处理函数**

标题栏增加：

```html
<el-button type="success" plain :loading="scopeApproving" @click="handleApproveScope('all')">
  全部审核通过
</el-button>
<el-button type="success" plain :loading="scopeApproving" @click="handleApproveScope('filtered')">
  按当前条件审核通过
</el-button>
```

逻辑：

```javascript
async function handleApproveScope(scope) {
  const filters = { /* 与 buildQueryParams 相同的筛选字段，不含 page */ }
  const countParams = scope === 'all' ? { scope: 'all' } : { scope: 'filtered', ...filters }
  const countRes = await approveScopeCountApi(countParams)
  const n = countRes.data?.count ?? 0
  if (n === 0) {
    ElMessage.info('当前没有待审核数据')
    return
  }
  const tip = scope === 'all'
    ? `将审核通过全部待审核数据共 ${n} 条，且不受当前筛选影响。是否继续？`
    : `将按当前查询条件审核通过 ${n} 条。是否继续？`
  await ElMessageBox.confirm(tip, '确认审核通过', { type: 'warning' })
  scopeApproving.value = true
  try {
    const res = await approveScopeApi({
      scope,
      filters: scope === 'filtered' ? filters : undefined,
    })
    ElMessage.success(res.message || `已通过 ${res.data.success_count} 条`)
    selectedIds.value = []
    await loadList()
  } finally {
    scopeApproving.value = false
  }
}
```

用户取消确认时吞掉 `ElMessageBox` 的 cancel，勿当错误提示。

- [ ] **Step 3: 手动验收清单**

1. 无待审核 → 点两按钮均提示无数据  
2. 筛选平台后：全部 count ≥ 条件 count  
3. 按条件通过后列表只剩未命中筛选的待审核  
4. 全部通过后待审核为空（忽略并发新提交）  

---

### Task 3: README 收尾

**Files:**
- Modify: `README.md`

- [ ] **Step 1:** 在审核相关功能行补充「支持全部 / 按当前条件审核通过」；API 表增加两行。

- [ ] **Step 2:** 再跑后端单测

```bash
cd backend
python -m unittest tests.test_review_approve_scope -v
```

---

## Spec coverage（自检）

| 规格项 | 任务 |
|--------|------|
| count 接口 + 0 条不确认 | Task 1 + 2 |
| all / filtered 语义 | Task 1 |
| 分批 approve、汇总返回 | Task 1 |
| 前端双按钮 + 确认文案 + loading | Task 2 |
| README | Task 3 |
| 非目标（驳回范围、异步队列） | 不实现 |

## 非目标

- 全部/按条件驳回  
- 异步任务队列与进度条  
- 改变勾选批量通过行为  
