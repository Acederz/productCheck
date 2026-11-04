# 应用报错文件日志 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将接口未捕获异常与 API 内 500 异常写入 `storage/logs/app.log`，日志含中文操作名、用户、方法路径与完整堆栈，便于排错。

**Architecture:** 新建 `app_logging.py` 负责滚动文件 Handler 与 `log_request_exception`；`create_app` 调用 `setup_logging` 并注册全局 `Exception` 处理器；现有 `except Exception` 的 API 在返回 500 前调用辅助函数。业务 4xx / `ValueError` 不写文件。

**Tech Stack:** Flask、Python `logging` + `RotatingFileHandler`、unittest

## Global Constraints

- 日志目录默认：`STORAGE_PATH/logs`（即项目 `storage/logs/`）
- Logger 名：`product_check`
- 主文件：`app.log`；约 10MB × 10 备份
- 不记录 Authorization、密码、完整请求体
- 不改操作日志表 / 不做错误日志页面
- 未经用户明确要求不 git commit

---

### Task 1: app_logging 核心 + 单测

**Files:**
- Create: `backend/app/utils/app_logging.py`
- Create: `backend/tests/test_app_logging.py`
- Modify: `backend/app/config.py`（增加 LOG_DIR / LOG_MAX_BYTES / LOG_BACKUP_COUNT 默认）
- Modify: `backend/app/__init__.py`（setup_logging + 全局 errorhandler）

**Interfaces:**
- Produces: `setup_logging(app) -> None`
- Produces: `log_request_exception(operation: str, exc: BaseException) -> None`
- Produces: `LOGGER_NAME = "product_check"`

- [x] **Step 1: 写失败单测**（临时目录配置 LOG_DIR，测 setup 建文件、log_request_exception 写入操作名与堆栈、全局异常路由写「未捕获异常」）
- [x] **Step 2: 跑测确认失败**
- [x] **Step 3: 实现 app_logging + create_app 接线 + config 默认值**
- [x] **Step 4: 跑测通过**

---

### Task 2: API except Exception 补操作名

**Files:**
- Modify: `backend/app/api/imports.py`
- Modify: `backend/app/api/rules.py`
- Modify: `backend/app/api/skip_field_rules.py`
- Modify: `backend/app/api/users.py`

**Interfaces:**
- Consumes: `log_request_exception(operation, exc)`

操作名：
- 导入 Excel / 按批次删除 / 导入分类规则 / 导入无需填写字段规则 / 删除操作员

- [x] **Step 1: 各 except Exception 分支先 log 再 fail**
- [x] **Step 2: 跑 `test_app_logging` + 相关既有单测冒烟**

---

### Task 3: 文档

**Files:**
- Modify: `docs/常用命令速查.md`（或 README 一小段）：日志路径与查看方式
- Modify: `README.md` 当前进度/文档区一句说明

- [x] **Step 1: 补充查看 `storage/logs/app.log` 说明**
- [x] **Step 2: 验证启动后目录存在（可选手动）**

## Spec coverage

| Spec 项 | Task |
|---------|------|
| storage/logs + 滚动 | 1 |
| 字段：操作/用户/路径/堆栈 | 1 |
| 全局未捕获 | 1 |
| API 500 补操作名 | 2 |
| 4xx 不写 | 1（测试断言） |
| 文档 | 3 |
| 不记录密码/body | 1 |

## Open

- 提交：用户未要求则不做 commit
