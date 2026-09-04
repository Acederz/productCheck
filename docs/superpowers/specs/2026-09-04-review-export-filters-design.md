# 审核中心与导出页筛选增强设计

日期：2026-09-04  
状态：已确认，按方案实施  
（由「审核中心操作员筛选」扩展：导出任务增加操作员；任务/正式库平台多选；任务状态多选）

## 背景

1. 审核中心已有平台、批次、大类、区隔、关键词筛选，后端待审核接口仅支持单值 `assignee_id`，前端无操作员筛选项。
2. 数据导出页：任务导出的状态/平台为单选；正式库平台为单选（后端已支持逗号多平台）；任务导出无操作员筛选。

## 需求结论

### A. 审核中心

1. 筛选栏「批次号」与「大类」之间增加「操作员」多选（可搜索、可清空）。
2. 选项：启用中的操作员（`role=operator` 且 `is_active=true`），不含管理员。
3. 参数：`assignee_id=1,2,3`；多选语义为「或」。
4. 重置时清空；选项数据复用 `GET /api/users` 前端过滤。

### B. 导出任务数据

1. 增加「操作员」多选（规则同审核中心，按任务 `assignee_id`）。
2. 「状态」改为多选（未分发 / 待处理 / 待审核 / 已驳回 / 已通过）。
3. 「平台」改为多选。
4. 参数：`assignee_id`、`status`、`platform` 均为逗号分隔；多选为「或」；空则不筛。

### C. 导出正式库数据

1. 「平台」改为多选（前端改多选；后端已支持逗号多平台则保持/对齐）。
2. **不加**操作员筛选。

## 后端设计

### 1. 待审核列表（`backend/app/api/reviews.py`）

将单值：

```python
if assignee_id.isdigit():
    query = query.filter_by(assignee_id=int(assignee_id))
```

改为：

```python
assignee_ids = parse_int_ids(assignee_id)
if assignee_ids:
    query = query.filter(ClassificationTask.assignee_id.in_(assignee_ids))
```

### 2. 任务导出（`export_service.export_tasks` / `api/export.py`）

- `status`：支持逗号多值 → `status.in_(...)`（合法状态以外的片段跳过或忽略）
- `platform`：支持逗号多值 → `platform.in_(...)`（与正式库导出对齐）
- 新增/透传 `assignee_id`：`parse_int_ids` + `assignee_id.in_(...)`

### 3. 正式库导出

- 保持/确认 `platform` 逗号多选已生效；前端改为多选传参即可。
- 可选小重构：抽 `apply_platform_filter` / `apply_assignee_id_filter` 到 `query_filters.py`，避免任务/正式库重复逻辑（YAGNI 可内联，保持可读即可）。

## 前端设计

| 页面 | 改动 |
|------|------|
| `ReviewList.vue` | 操作员多选 + 查询参数 |
| `ExportPage.vue` | 任务：状态/平台/操作员多选；正式库：平台多选；加载启用操作员选项 |

导出下载参数将数组 `join(',')` 后再传给现有 download API。

## 测试要点

1. 审核：`assignee_id` 单/多/空  
2. 任务导出：`status` 多选、`platform` 多选、`assignee_id` 多选及组合  
3. 正式库导出：`platform` 多选  
4. 不传参时行为与改前一致（导出全量或原默认）  

## 验收标准

- 审核中心可按操作员多选过滤待审核列表  
- 导出任务可按状态、平台、操作员多选过滤  
- 导出正式库平台可多选  
- 选项仅为启用中的操作员；管理员不在选项中  

## 非目标

- 正式库不按操作员/审核人筛选  
- 任务管理列表本期不加操作员筛选  
- 不改导出列结构与清洗规则  
