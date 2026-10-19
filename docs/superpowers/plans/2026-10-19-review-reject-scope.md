# Plan: 审核中心按范围批量驳回

镜像「全部/按条件审核通过」，增加对称驳回（原因可空）。

## Scope

- In: `reviews.py`、`review_service.py`、`log_display.py`、`reviews.js`、`ReviewList.vue`、单测、README
- Out: 改勾选批量驳回语义；异步队列

## Action items

[x] 新增 `test_review_reject_scope.py`（count / filtered 驳回 / 服务层 all / 403 / 非法 scope）
[x] `ReviewService.reject_by_scope` + API `reject-scope-count` / `reject-scope`
[x] 前端 API + ReviewList 两按钮与确认/可选原因流程
[x] `log_display` 与 README 同步
[x] 跑 pytest 相关用例（20 passed）
