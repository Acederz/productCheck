# 审核中心按范围批量通过设计

日期：2026-09-14  
状态：已确认，按方案 1 实施

## 背景

审核中心已支持勾选后「批量通过 / 批量驳回」。管理员在数据量较大时，需要：

1. **全部审核通过**：无视当前查询条件，通过所有待审核任务；
2. **按当前条件审核通过**：仅通过当前筛选命中的待审核任务。

两者均需二次确认，并展示将通过的条数（以服务器最新统计为准）。

## 需求结论

1. 入口：管理员「审核中心」标题栏，与现有批量按钮并列；**不依赖勾选**。
2. 点按钮先请求最新可通条数：
   - `0` → 提示「当前没有待审核数据」，**不**弹确认框；
   - `>0` → 二次确认，文案含条数与范围说明。
3. 「全部」忽略页面筛选；「按当前条件」使用与列表相同的筛选（平台 / 批次 / 操作员 / 大类 / 区隔 / 关键词）。
4. 仅处理状态为「待审核」的任务；仅管理员。
5. 后端在同一请求内分批调用现有 `approve_tasks`；前端 loading「处理中…」，结束后提示成功/跳过条数并刷新列表。
6. 条数统计与执行前可能存在并发变更：执行时非待审核等按现有逻辑记入 `skipped`，不回滚已通过记录。

## 方案选择

| 方案 | 说明 | 结论 |
|------|------|------|
| 方案 1 | 统计接口 + 按范围通过接口；服务端分批；前端两个按钮 | **采用** |
| 方案 2 | 异步任务队列 + 轮询进度 | 本期过重 |
| 方案 3 | 前端翻页循环调现有 `/approve` | 易中断、条数不准 |

## 接口设计

均需 `admin_required`。筛选参数与 `GET /api/reviews/pending` 对齐，复用同一套 filter 组装，避免两套逻辑。

### `GET /api/reviews/approve-scope-count`

- Query：
  - `scope`：`all` | `filtered`（必填）
  - 当 `scope=filtered`：与 pending 列表相同的筛选 query（`platform`、`batch_id`、`assignee_id`、`category_large`、`category_segment`、`keyword` 等）
  - 当 `scope=all`：忽略筛选参数
- 行为：`status=待审核` 条件下 `count()`
- 成功：`{ "count": N }`

### `POST /api/reviews/approve-scope`

- Body JSON：
  ```json
  {
    "scope": "all" | "filtered",
    "filters": {
      "platform": "...",
      "batch_id": "...",
      "assignee_id": "...",
      "category_large": "...",
      "category_segment": "...",
      "keyword": "..."
    }
  }
  ```
  - `scope=all` 时可不传或忽略 `filters`
  - `scope` 非法 → 400
- 行为：
  1. 按 scope 组装与列表一致的待审核查询；
  2. 分批取出任务 ID（建议每批 100，实现常量可调）；
  3. 每批调用现有 `ReviewService.approve_tasks`；
  4. 累加 `success_ids` / `skipped`，直到无更多待审核命中（注意：通过后状态变化，循环应以「本批查询结果为空」结束，或先收集 ID 再分批——**推荐先一次性查出全部匹配 ID 再分批 approve**，避免边通过边翻页漏/重；若内存压力大再改为 keyset 游标。默认数据量可接受时采用「先收集 ID」）。
- 成功：
  ```json
  {
    "success_count": 10,
    "skipped_count": 1,
    "total_matched": 11
  }
  ```
  - `message` 示例：`已通过 10 条，跳过 1 条`
- 写操作日志：可记一条汇总日志（如 `approve_tasks_scope`），detail 含 scope、success_count、skipped_count、filters 摘要；不必为每一条再写额外汇总以外的日志（单条通过日志仍由现有 `approve_tasks` 负责，若现有已按批写日志则保持）。

## 前端设计

- 文件：`frontend/src/views/admin/ReviewList.vue`、`frontend/src/api/reviews.js`（或现有 reviews API 模块）
- 按钮文案：
  - 「全部审核通过」
  - 「按当前条件审核通过」
- 交互：
  1. 点击 → 调 count（可短 loading）；
  2. `count === 0` → `ElMessage` 提示「当前没有待审核数据」；
  3. 否则 `ElMessageBox.confirm`：
     - 全部：`将审核通过全部待审核数据共 N 条，且不受当前筛选影响。是否继续？`
     - 条件：`将按当前查询条件审核通过 N 条。是否继续？`
  4. 确认 → 调 approve-scope，按钮 loading / 禁用双按钮防重复；
  5. 成功 → 提示 message，清空勾选（如有），刷新列表与统计。
- HTTP 超时：approve-scope 建议单独加大超时（如 120s+），避免大批量默认超时。

## 异常与边界

| 情况 | 处理 |
|------|------|
| 条数为 0 | 提示，不弹确认 |
| 确认后状态已被他人改动 | 跳过，计入 skipped |
| 非管理员 | 403 |
| scope 非法 / 缺参 | 400 |
| 请求失败 | 现有错误提示；已通过部分不回滚 |

## 测试要点

1. 无待审核 → count=0，前端不弹确认  
2. 有筛选时：`all` 的 count ≥ `filtered` 的 count  
3. `filtered` 通过后，仅筛选命中记录离开待审核；未命中仍在  
4. `all` 通过后，待审核列表为空（或仅剩并发新提交）  
5. 与勾选批量通过互不影响  
6. 非管理员调用 → 403  

## 验收标准

- 管理员可不勾选即可使用两个范围通过按钮  
- 确认框展示服务器最新条数  
- 全部 / 按条件范围语义正确  
- 结束后列表刷新，正式库按现有通过规则入库  

## 非目标

- 不做「全部驳回 / 按条件驳回」  
- 不做异步任务队列与进度百分比条  
- 不改变单条通过、勾选批量通过/驳回的现有行为  
