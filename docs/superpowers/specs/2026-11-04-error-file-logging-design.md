# 应用报错文件日志

日期：2026-11-04  
状态：已确认（用户选方案 A：仅写文件）

## 背景

项目已有数据库「操作日志」（业务留痕，页面可查），但**几乎没有**面向排错的文件日志：

- `create_app` 未配置 logging Handler
- 接口里大量 `except Exception` 只把短文案返回前端，不落盘堆栈
- 全库仅个别 `current_app.logger.warning`

换电脑 / 服务器上出问题后，难以对照「哪个操作、哪个用户、哪个接口」失败。

## 目标

在 `storage/logs/` 写入可读的错误日志文件，使维护者打开文件即可定位：

- 什么时间、哪次请求、哪个中文操作名
- 谁（用户名 / ID；未登录写匿名）
- 异常类型、错误信息、完整堆栈

## 非目标（Out）

- 不做管理员「错误日志」后台页面
- 不新建错误日志数据库表
- 不改造现有操作日志（`operation_logs` / 字段变更日志）
- 不为每个成功请求写 INFO 进出流水（避免刷屏）
- 业务校验失败（如「请上传 Excel」）默认**不写文件**

## 方案（方案 1）

应用启动时配置滚动文件日志 + 全局未捕获异常处理器；各 API 在捕获 `Exception` 返回 500 前调用统一辅助函数，带上中文「操作名」。

### 存放位置

| 项 | 约定 |
|----|------|
| 目录 | `storage/logs/`（相对项目根；与 `STORAGE_PATH` 下并列，创建 `create_app` 时 `mkdir`） |
| 主文件 | `app.log` |
| 滚动 | `RotatingFileHandler`：单文件约 10MB，备份约 10 个（`app.log.1` …） |
| Git | 已由 `storage/` 整体忽略，无需改 `.gitignore` |

开发与生产共用同一套文件日志；控制台可保留 Flask 默认输出，文件以 ERROR/WARNING 为主。

### 日志行内容（必含）

单行可读摘要 + 多行堆栈，建议格式示例：

```text
2026-11-04 11:20:01 ERROR [product_check] 操作=导入Excel | 用户=admin(id=1) | POST /api/imports | Query=- | Body摘要=- | 异常=ValueError: xxx
Traceback (most recent call last):
  ...
```

字段说明：

| 字段 | 来源 |
|------|------|
| 时间 | logging 格式化 |
| 级别 | ERROR（未捕获 / 500）；必要时 WARNING |
| 操作 | 调用方传入的中文名，如「导入 Excel」「按批次删除」；全局处理器无操作名时用「未捕获异常」 |
| 用户 | `g.current_user` 的 username + id；无则 `匿名` |
| 方法+路径 | `request.method` + `request.path` |
| Query | `request.query_string` 解码后截断（如最长 200 字符），无则 `-` |
| Body 摘要 | **默认不记录**请求体（避免密码、大文件进日志）；仅记「有/无 body」或 content-type 可选 |
| 异常 | `type(exc).__name__` + `str(exc)` |
| 堆栈 | `exc_info=True` 或 `traceback` |

安全约束：不记录 `Authorization`、密码字段、完整上传文件内容。

### 何时写入

| 场景 | 级别 | 说明 |
|------|------|------|
| 未捕获异常（Flask `errorhandler(Exception)` 或等价） | ERROR | 返回统一 500 JSON；文件写满堆栈 |
| API 内 `except Exception` 后返回 500 | ERROR | 写日志后再 `fail(...)`，须传操作名 |
| `ValueError` / 业务 4xx | 默认不写 | 与现网「只提示用户」一致 |
| 现有个别 `logger.warning`（如删文件失败） | 可保留 | 继续走同一 logger |

可选增强（本期不做除非实现时顺手）：HTTP 4xx 由全局处理器忽略，不刷文件。

### 代码结构

| 单元 | 职责 |
|------|------|
| `backend/app/utils/app_logging.py`（新建） | `setup_logging(app)`；`log_request_exception(operation, exc)` |
| `backend/app/__init__.py` | `create_app` 中调用 `setup_logging`；注册全局异常处理 |
| 已有 `except Exception` 的 API | `imports` / `rules` / `skip_field_rules` / `users` 等：捕获后先 `log_request_exception` |
| `config.py` | 可选：`LOG_DIR`、`LOG_MAX_BYTES`、`LOG_BACKUP_COUNT`（有默认值即可，不必进 `.env`） |

原则：KISS——一个 logger 名（如 `product_check`），一个文件 Handler；业务代码只调一个辅助函数。

### 覆盖的操作名（首批）

至少覆盖当前会 `except Exception` 并 500 的接口：

- 导入 Excel
- 按批次删除
- 导入分类规则
- 导入无需填写字段规则
- 删除操作员

全局处理器覆盖其余漏网未捕获异常（操作名写「未捕获异常」）。

### 文档

- README 或 `docs/常用命令速查.md` 增加一行：日志路径 `storage/logs/app.log`、如何查看
- 不新增前端说明

### 测试

- 单元/集成：mock 或临时日志目录，触发一次故意异常，断言文件中出现操作名、路径、堆栈关键字
- 不依赖真实 MySQL 亦可测 `log_request_exception` 纯函数侧（若拆出格式化）

## 验收标准

1. 启动应用后存在 `storage/logs/`（或配置的 LOG_DIR）
2. 人为制造一次导入/删除等 500，打开 `app.log` 能看到中文操作名、用户、方法路径、堆栈
3. 正常业务校验失败（缺文件等）不因此把 `app.log` 刷满
4. 与页面「操作日志」互不影响

## 风险

- 日志含用户名与路径：仅内网运维查看，可接受
- 多进程（uWSGI workers）写同一滚动文件：本期可接受；若出现交错损坏再改为按进程分文件（Out）
