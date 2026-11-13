# 北京时间显示 + 导入结果反馈

日期：2026-11-13  
状态：已确认

## 一、时间统一显示北京时间

- 问题：库内 `datetime.utcnow()` 存 UTC，接口 `isoformat()` 原样返回，页面/导出比北京时间慢 8 小时
- 方案：库内仍存 UTC（不迁移）；新增 `app/utils/time_utils.py` 的 `fmt_beijing(dt)`，无时区视为 UTC，固定 +8 小时，格式 `YYYY-MM-DD HH:MM:SS`
- 替换所有 API 时间输出（models/task、models/user、api/approved、api/rules、api/skip_field_rules、services/log_service、services/task_service）与导出 Excel `_fmt_time`

## 二、导入结果反馈

- `import_batches` 新增 `fail_reason VARCHAR(500) NULL`，`ensure_schema` 自动补列
- 服务 `import_excel` 返回 `(batch, summary)`，`summary` 含 `warning_rows`、`assigned_rows`
- 失败统一抛 `ImportBatchError(message, batch, unexpected)`：
  - 预期失败（文件为空 / 表头错误 / 文件无法读取）：批次 `failed` + `fail_reason`，HTTP 400
  - 意外异常：先回滚本次导入数据，再单独写一条 `failed` 批次（原因「服务器异常：…」），写 `app.log`，HTTP 500
  - 失败响应 `data` 为批次字典，前端据此展示
- 前端：
  - 导入后弹结果框（成功 / 部分失败 / 失败），需手动关闭；部分失败可下载错误报告
  - 状态列中文标签：导入成功、部分失败、导入失败、导入中；失败原因悬停查看
  - 上传请求不走拦截器自动弹错（`silent`），避免与结果框重复；上传超时放宽到 10 分钟

## 测试

内存 SQLite：时间换算、成功、部分失败、表头错误、文件无法读取、意外异常回滚并留失败记录、API 失败返回批次数据。

## 上线

`git pull` 后执行 `python manage.py ensure-schema` 再重启。
