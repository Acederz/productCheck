# 操作员统计按批次切换

日期：2026-11-09  
状态：已确认

## 问题

「我的任务」顶部统计固定取**全系统最新导入批次**。操作员在最新批次没有任务时统计全为 0，误以为数据丢失（如 xiaoyakang 836 条在倒数第 2 批）。

## 方案

- 统计条原「批次 xxx」文字改为下拉框，只列**分给当前操作员任务**的已完成批次，按批次 ID 倒序
- 选项文案：`批次号 · 文件名`（批次号本身含北京时间，避免 UTC 时间显示偏差）
- 默认选中**该操作员最近被分配的批次**
- 切换只刷新 4 个统计数字；下方任务列表与筛选不变
- 无任何分配批次时不显示下拉框，统计为 0

## 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/tasks/my/batches` | 当前操作员有任务的批次：`[{id, batch_no, file_name}]`，倒序；仅操作员 |
| GET | `/api/tasks/my/stats?batch_id=` | `batch_id` 可选；不传取该操作员最近批次；批次无其任务则返回 0（不报错、不泄露） |

统计口径不变：待处理 = 待处理 + 已驳回；已提交 = 待审核；已通过 = 已通过。

## 代码

- 新建 `backend/app/services/my_batch_stats_service.py`：`list_assigned_batches(user_id)`、`get_batch_stats(user_id, batch_id=None)`
- `backend/app/api/tasks.py`：新增 `/my/batches`，`/my/stats` 改用服务
- `backend/app/config.py`：新增 `TestingConfig`（内存 SQLite），单测不写共享 MySQL
- 前端 `api/tasks.js`、`views/operator/MyTasks.vue`

## Out

不改下方任务列表；不改管理员页面。
