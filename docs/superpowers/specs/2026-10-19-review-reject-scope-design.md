# 审核中心按范围批量驳回设计

日期：2026-10-19  
状态：已确认，按方案 1 实施

## 背景

审核中心已有「全部审核通过」「按当前条件审核通过」。需对称增加驳回能力。

## 需求结论

1. 入口：审核中心标题栏，与通过按钮并列；**不依赖勾选**。
2. 先查最新待审核条数：`0` 不弹确认；`>0` 二次确认（文案含条数与范围）。
3. 确认时可**选填**统一驳回原因（可空，与单条/勾选驳回一致）。
4. 「全部」忽略筛选；「按当前条件」与列表筛选一致。
5. 仅待审核、仅管理员；服务端先收集 ID 再分批调用现有 `reject_tasks`。

## 方案

与通过相同：`reject-scope-count` + `reject-scope`（方案 1）。

## 接口

均需 `admin_required`。筛选复用 pending / approve-scope 同一套组装。

### `GET /api/reviews/reject-scope-count`

- Query：`scope=all|filtered`；filtered 时筛选与 pending 一致
- 返回：`{ "count": N }`

### `POST /api/reviews/reject-scope`

- Body：`{ "scope", "filters?", "reason?" }`（reason 可空）
- 先收集匹配 ID，再分批 `reject_tasks`
- 返回：`success_count` / `skipped_count` / `total_matched`
- 汇总操作日志：`reject_tasks_scope`

## 前端

- 按钮：「全部驳回」「按当前条件驳回」
- 流程：count → 确认 → 可选填原因弹窗（可空）→ reject-scope（长超时）→ 刷新
