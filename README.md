# 市场数据分类管理平台

Flask 后端 + Vue 3 前端 + MySQL 8.0，用于市场商品数据的导入、分类填写、审核与导出。

## 项目结构

```
productCheck/
├── backend/          # Flask API（含 wsgi.py）
├── frontend/         # Vue 3 前端
├── deploy/           # CentOS 生产部署样例（Nginx / systemd / 更新脚本）
├── docs/             # 运行与部署手册
├── storage/          # 上传文件与导出文件
├── scripts/          # 启动脚本
├── 需求相关/          # 需求与设计文档
└── package.json      # 一键启动（dev）
```

## 环境要求

- Python 3.10+
- Node.js 18+
- MySQL 8.0+

> **Windows 第一次运行？** 请阅读详细图文流程：  
> **[docs/Windows首次运行手册.md](docs/Windows首次运行手册.md)**（含虚拟环境、MySQL 配置、启动与排错）

## 快速开始

### 1. 安装依赖

```bat
REM 创建并激活虚拟环境（Windows 推荐）
python -m venv .venv
.venv\Scripts\Activate.ps1

REM 后端 Python 依赖
pip install -r backend\requirements.txt

REM 前端依赖（根目录 + frontend）
npm install
cd frontend && npm install && cd ..
```

### 2. 配置数据库

```bash
# 复制环境变量模板
copy backend\.env.example backend\.env
```

编辑 `backend/.env`，填写 MySQL 连接信息：

```
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=你的密码
MYSQL_DATABASE=product_check
```

先在 MySQL 中创建数据库：

```sql
CREATE DATABASE product_check DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 3. 初始化数据库表

```bat
REM 需先激活 .venv
cd backend
python manage.py init-db
cd ..
```

默认管理员账号见 `.env` 中 `ADMIN_USERNAME` / `ADMIN_PASSWORD`（默认 `admin` / `admin123`）。

### 4. 一键启动（只需 1 个终端）

```bat
REM 项目根目录，且已激活 .venv
REM Windows 建议用 scripts\dev.bat（已设置 UTF-8，避免中文日志乱码）
npm run dev
```

或 Windows 双击 / 运行：

```bash
scripts\dev.bat
```

- 后端 API：http://127.0.0.1:5000
- 前端页面：http://127.0.0.1:5173
- 健康检查：http://127.0.0.1:5000/api/health

## 当前进度

**第一期功能已全部完成**，可进行完整业务流程测试。

| 模块 | 功能 |
|------|------|
| 登录/用户 | 管理员创建账号、停用、重置密码 |
| 数据导入 | Excel 导入、错误报告 |
| 分类规则 | 规则 Excel 导入、级联查询 |
| 任务流程 | 分配、填表、暂存、提交、审核（操作员列表：主图/文描图灯箱/产品属性展示；审核中心：同款筛选分页 + 单条通过/驳回） |
| 正式数据 | 审核通过入库、历史版本 |
| 导出 | 任务/正式库按条件导出 Excel |
| 日志 | 操作日志、字段变更查询 |
| 系统设置 | 操作员导出开关 |

## 主要 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/health | 健康检查 |
| POST | /api/auth/login | 登录 |
| POST | /api/imports | 导入商品 Excel |
| POST | /api/rules/import | 导入分类规则 |
| POST | /api/tasks/assign | 批量分配 |
| POST | /api/tasks/submit | 提交审核 |
| POST | /api/reviews/approve | 审核通过 |
| GET | /api/export/tasks | 导出任务 Excel |
| GET | /api/export/approved | 导出正式库 Excel |
| GET | /api/logs/operations | 操作日志 |

详细设计见 `需求相关/系统设计.md`。

## 生产部署简述

CentOS 推荐：**Nginx + uWSGI（WSGI）+ MySQL**。

默认部署路径：`/home/topuser/productCheck`，运行用户：`root`。

完整步骤与发版更新请看：

**[docs/CentOS部署与更新手册.md](docs/CentOS部署与更新手册.md)**

摘要：

1. 服务器配置 `backend/.env`（`FLASK_ENV=production`）并 `python manage.py init-db`
2. **本机** `scripts\build_frontend.bat` 构建前端，`frontend/dist` 随 Git 同步（服务器无需 Node.js）
3. systemd 启动 uWSGI：`deploy/uwsgi/product_check.ini`（监听 `127.0.0.1:5000`）
4. Nginx 托管 `frontend/dist`，反代 `/api` 到 uWSGI
5. 日常更新：`deploy/scripts/deploy_update.sh`（默认跳过服务器 npm build）
6. 部署前环境检查：`deploy/scripts/check_env.sh`

配置样例目录：`deploy/nginx/`、`deploy/systemd/`。

## 文档

- [Windows 首次运行手册](docs/Windows首次运行手册.md)
- [CentOS 部署与更新手册](docs/CentOS部署与更新手册.md)
- [需求说明](需求相关/需求说明.md)
- [需求确认问题](需求相关/需求确认问题.md)
- [系统设计](需求相关/系统设计.md)

## 推送到 GitHub

`.gitignore` 已排除：`node_modules`、`.venv`、`backend/.env`、上传/导出文件等。  
`frontend/dist` **会提交到 Git**（本机构建，服务器无需 Node.js）。

**本机构建前端：**

```bat
scripts\build_frontend.bat
```

**一键上传（Windows，推荐 PowerShell）：**

```powershell
# 先在 GitHub 创建空仓库，再执行：
.\scripts\push_to_github.ps1 -RepoUrl "https://github.com/你的用户名/productCheck.git"
```

或使用批处理（纯英文输出，避免编码问题）：

```bat
scripts\push_to_github.bat https://github.com/你的用户名/productCheck.git
```

**手动命令：**

```bat
cd c:\Users\acederz\Documents\worksoft\pythonProject\productCheck
git init
git branch -M main
git add .
git commit -m "chore: 初始化项目"
git remote add origin https://github.com/你的用户名/productCheck.git
git push -u origin main
```
