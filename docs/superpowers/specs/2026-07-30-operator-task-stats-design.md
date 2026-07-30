# 操作员「我的任务」填写统计

日期：2026-07-30  
状态：已确认

## 范围

管理员最近一次 `status=completed` 的导入批次中，当前操作员被分配到的任务。

## 指标

| 字段 | 含义 |
|------|------|
| total | 该批分给自己的全部条数 |
| pending | 待处理 + 已驳回 |
| submitted | 待审核 |
| approved | 已通过 |

## 接口

`GET /api/tasks/my/stats`（仅操作员）

返回示例：`{ batch_id, batch_no, total, pending, submitted, approved }`；无批次时数字为 0。
