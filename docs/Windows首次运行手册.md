# Windows 首次运行手册（虚拟环境）

> 适用系统：Windows 10 / 11  
> 项目路径示例：`C:\Users\你的用户名\Documents\worksoft\pythonProject\productCheck`

本手册从零开始，带你完成：**环境检查 → Python 虚拟环境 → MySQL 配置 → 初始化数据库 → 启动项目 → 第一次登录使用**。

---

## 一、运行前需要准备的软件

| 软件 | 最低版本 | 用途 | 如何检查是否已安装 |
|------|----------|------|-------------------|
| Python | 3.10+ | 后端 Flask | 打开 CMD，输入 `python --version` |
| Node.js | 18+ | 前端 Vue | 输入 `node --version` |
| npm | 随 Node 安装 | 前端依赖、一键启动 | 输入 `npm --version` |
| MySQL | 8.0+ | 数据库 | 服务管理器中查看 MySQL80 是否运行 |

若 `python` 命令无效，可尝试 `py --version`（Windows 常用 Python 启动器）。

---

## 二、打开项目目录

1. 按 `Win + R`，输入 `cmd` 或打开 **PowerShell**
2. 进入项目根目录（请改成你的实际路径）：

```bat
cd /d C:\Users\acederz\Documents\worksoft\pythonProject\productCheck
```

3. 确认能看到 `backend`、`frontend`、`package.json` 文件夹/文件：

```bat
dir
```

---

## 三、创建并启用 Python 虚拟环境（重要）

虚拟环境可以把本项目的 Python 依赖与系统其他项目隔离开，**推荐必须使用**。

### 3.1 创建虚拟环境（只需做一次）

在项目根目录执行：

```bat
python -m venv .venv
```

执行成功后，会出现 `.venv` 文件夹。

### 3.2 激活虚拟环境（每次新开终端都要做）

**方式 A：CMD（命令提示符）**

```bat
.venv\Scripts\activate.bat
```

**方式 B：PowerShell**

```powershell
.venv\Scripts\Activate.ps1
```

若 PowerShell 提示“无法加载，因为在此系统上禁止运行脚本”，先执行（只需一次）：

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

然后再执行 `Activate.ps1`。

**激活成功的标志**：命令行前面会出现 `(.venv)`，例如：

```
(.venv) C:\...\productCheck>
```

### 3.3 安装后端 Python 依赖（只需做一次）

确保已激活 `(.venv)`，然后执行：

```bat
pip install -r backend\requirements.txt
```

国内网络慢时可用清华源（可选）：

```bat
pip install -r backend\requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

---

## 四、配置 MySQL 数据库

### 4.1 确认 MySQL 服务已启动

1. 按 `Win + R`，输入 `services.msc`
2. 找到 **MySQL80**（或你的 MySQL 服务名）
3. 状态应为 **正在运行**；若未运行，右键 → **启动**

### 4.2 创建数据库

用 **MySQL 命令行**、**Navicat** 或 **MySQL Workbench** 连接本机 MySQL，执行：

```sql
CREATE DATABASE product_check
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

### 4.3 配置项目环境变量文件

在项目根目录执行：

```bat
copy backend\.env.example backend\.env
```

用记事本或 VS Code 打开 `backend\.env`，修改以下内容：

```ini
# MySQL 连接（改成你的实际账号密码）
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=你的MySQL密码
MYSQL_DATABASE=product_check

# 首次初始化时自动创建的管理员账号
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
```

> 说明：`ADMIN_PASSWORD` 可在首次登录后通过「用户管理」修改；生产环境务必改成强密码。

---

## 五、初始化数据库表和管理员账号（只需做一次）

**必须先激活虚拟环境** `(.venv)`，然后执行：

```bat
cd backend
python manage.py init-db
cd ..
```

看到类似输出表示成功：

```
数据库初始化完成，默认管理员: admin
```

此步骤会：
- 在 MySQL 中创建所有业务表（用户、任务、规则、日志等）
- 创建默认管理员账号 `admin` / `admin123`（与 `.env` 一致）
- 写入默认系统配置

---

## 六、安装前端依赖（只需做一次）

在项目根目录执行（**不需要**激活 Python 虚拟环境，但需要 Node.js）：

```bat
npm install
cd frontend
npm install
cd ..
```

---

## 七、启动项目（每次开发使用）

### 7.1 启动前检查清单

- [ ] MySQL 服务正在运行
- [ ] `backend\.env` 已配置且密码正确
- [ ] 已执行过 `init-db`（首次）
- [ ] **当前终端已激活** `(.venv)`
- [ ] 前端依赖已 `npm install`（首次）

### 7.2 一键启动（推荐，只需 1 个终端）

在项目根目录、且已激活 `(.venv)` 的情况下：

```bat
npm run dev
```

或双击运行：

```bat
scripts\dev.bat
```

> 注意：`dev.bat` 不会自动激活虚拟环境。若未先激活 `.venv`，后端可能找不到依赖。**建议始终在激活虚拟环境后再运行 `npm run dev`。**

### 7.3 启动成功的标志

终端中应出现类似输出：

```
[backend]  * Running on http://0.0.0.0:5000
[frontend]  Local: http://localhost:5173/
```

### 7.4 访问地址

| 用途 | 地址 |
|------|------|
| **系统首页（用这个）** | http://127.0.0.1:5173 |
| 后端健康检查 | http://127.0.0.1:5000/api/health |
| 后端 API | http://127.0.0.1:5000/api/... |

浏览器打开 http://127.0.0.1:5173 ，应看到登录页。

### 7.5 停止服务

在运行 `npm run dev` 的终端窗口按 `Ctrl + C`。

---

## 八、第一次登录与推荐使用顺序

### 8.1 管理员登录

| 项目 | 默认值 |
|------|--------|
| 账号 | `admin` |
| 密码 | `admin123`（或你在 `.env` 中设置的） |

### 8.2 建议按以下顺序操作（首次）

```
① 分类规则  →  点击「导入规则」（使用项目内样例 Excel，或上传自己的规则文件）
② 用户管理  →  新建操作员账号（如 op1 / op123）
③ 数据导入  →  上传「分类平台表头.xlsx」格式的待分类 Excel
④ 任务管理  →  勾选数据 → 批量分配给操作员
⑤ 操作员登录 →  填写分类 → 提交审核
⑥ 审核中心  →  通过或驳回
⑦ 正式数据  →  查看审核通过的数据
⑧ 数据导出  →  按需导出 Excel
```

样例文件位置：
- 表头模板：`需求相关\分类平台表头.xlsx`
- 分类规则：`需求相关\分类规则全维度拆分_最新版.xlsx`

---

## 九、每次重新开电脑后的最短流程

```bat
# 1. 进入项目目录
cd /d C:\Users\acederz\Documents\worksoft\pythonProject\productCheck

# 2. 激活虚拟环境
.venv\Scripts\activate.bat

# 3. 确认 MySQL 服务已启动（服务管理器）

# 4. 启动
npm run dev
```

浏览器访问：http://127.0.0.1:5173

---

## 十、常见问题排查

### Q1：`pip install` 报错或很慢

- 确认已激活 `(.venv)`
- 使用国内镜像：`-i https://pypi.tuna.tsinghua.edu.cn/simple`
- 升级 pip：`python -m pip install --upgrade pip`

### Q2：`python manage.py init-db` 报数据库连接错误

| 错误现象 | 处理办法 |
|----------|----------|
| `Can't connect to MySQL server` | 检查 MySQL 服务是否启动 |
| `Access denied for user` | 检查 `.env` 中 `MYSQL_USER`、`MYSQL_PASSWORD` |
| `Unknown database` | 先执行第四节 SQL 创建 `product_check` 库 |

### Q3：`npm run dev` 后端启动失败

- 是否已激活 `(.venv)`？
- 是否执行过 `pip install -r backend\requirements.txt`？
- 单独测试后端：

```bat
.venv\Scripts\activate.bat
cd backend
python -X utf8 run.py
```

### Q3.1：终端里中文请求日志变成乱码（如 `field=����`）

原因：Windows 默认代码页是 GBK，Flask 访问日志含中文 URL，经终端捕获后编码不一致。

处理：
1. 优先用 `scripts\dev.bat` 启动（已设置 `chcp 65001` 与 UTF-8 环境变量）
2. 或手动执行：

```bat
chcp 65001
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
npm run dev
```

3. 改完后**重启** `npm run dev`（热重载不够，需停掉再启）

### Q4：前端能开，登录报网络错误

- 确认后端也在运行（终端有 `[backend] Running on`）
- 浏览器访问 http://127.0.0.1:5000/api/health 应返回 JSON

### Q5：端口被占用（5000 或 5173）

```bat
netstat -ano | findstr :5000
netstat -ano | findstr :5173
```

结束占用进程，或修改：
- 后端端口：`backend\run.py` 中 `port=5000`
- 前端端口：`frontend\vite.config.js` 中 `server.port`

### Q6：PowerShell 无法激活虚拟环境

使用 CMD 的 `activate.bat`，或按 3.2 节设置执行策略。

---

## 十一、目录与文件说明（便于理解）

```
productCheck/
├── .venv/                 # Python 虚拟环境（第三节创建）
├── backend/
│   ├── .env               # 你的数据库配置（第四节创建，勿提交到 git）
│   ├── .env.example       # 配置模板
│   ├── requirements.txt   # Python 依赖列表
│   ├── manage.py          # 初始化数据库命令
│   └── run.py             # 后端启动入口
├── frontend/              # Vue 3 前端
├── storage/               # 上传的 Excel、导出文件存放处
├── scripts/dev.bat        # Windows 一键启动脚本
├── package.json           # npm run dev 定义
└── 需求相关/               # 需求文档与 Excel 样例
```

---

## 十二、安全提醒

1. `backend\.env` 含数据库密码，**不要**发给他人或上传到公开仓库
2. 正式使用前请修改默认管理员密码
3. 本手册为**本地开发**流程；上线 Linux 服务器需另行配置 Nginx + Gunicorn

---

*文档版本：v1.0 | 对应项目第一期功能*
