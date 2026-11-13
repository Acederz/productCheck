# 操作员统计按批次切换 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 操作员可在「我的任务」统计条下拉切换自己被分配过的批次，默认最近一个。

**Architecture:** 新服务模块负责「我的批次列表」与「指定批次统计」；tasks API 暴露 `/my/batches` 并让 `/my/stats` 接收 `batch_id`；前端统计条批次文字换成 el-select。

**Tech Stack:** Flask、SQLAlchemy、Vue 3 + Element Plus、unittest（内存 SQLite）

## Global Constraints

- 只列 `status=completed` 且含当前操作员任务的批次
- 传入不属于自己的 `batch_id` 返回全 0，不报错
- 下方任务列表不受影响
- 单测不得写入共享 MySQL

---

### Task 1: 后端服务 + API（TDD）

**Files:**
- Modify: `backend/app/config.py`（TestingConfig）
- Create: `backend/app/services/my_batch_stats_service.py`
- Modify: `backend/app/api/tasks.py`
- Test: `backend/tests/test_my_batch_stats.py`

- [x] 写失败单测：批次列表只含自己且倒序、默认最近批次、指定批次、他人批次返回 0、无批次返回空
- [x] 跑测确认失败
- [x] 实现服务与 API
- [x] 跑测通过

### Task 2: 前端下拉框

**Files:**
- Modify: `frontend/src/api/tasks.js`
- Modify: `frontend/src/views/operator/MyTasks.vue`

- [x] 新增 `myTaskBatchesApi`，`myTaskStatsApi(batchId)`
- [x] 统计条批次文字替换为 el-select，默认最近批次，切换刷新统计
- [x] `npm run build` 通过

### Task 3: 文档

- [x] README 任务流程/API 表补充
