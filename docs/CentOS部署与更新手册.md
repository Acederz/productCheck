# CentOS 部署与代码更新手册

适用架构：**Nginx（静态前端 + 反代） + uWSGI（WSGI 跑 Flask） + MySQL 8.0**

本文面向：第一次把本项目部署到 CentOS，以及以后改代码、发版本时怎么更新。

---

## 一、整体架构（先看懂再动手）

```
浏览器
  │
  ▼
Nginx :5173
  ├─ /           → 前端静态文件 frontend/dist
  └─ /api/       → 反代到 127.0.0.1:5174
                      │
                      ▼
                 uWSGI（WSGI）
                      │
                      ▼
                   Flask 后端
                      │
                      ▼
                   MySQL 8.0
```

| 组件 | 作用 |
|------|------|
| Nginx | 对外提供网页；把 `/api` 转给后端 |
| uWSGI | 用 WSGI 协议跑 Flask（生产不要用 `python run.py`） |
| systemd | 开机自启、崩溃重启后端 |
| MySQL | 业务数据 |
| storage/ | 上传 Excel、导出文件存放目录 |

仓库里已准备好的部署文件：

```
deploy/
├── env.production.example          # 生产环境变量模板
├── nginx/product_check.conf        # Nginx 配置样例
├── uwsgi/product_check.ini         # uWSGI 配置
├── systemd/product-check.service   # systemd 服务样例
├── scripts/check_env.sh            # 环境依赖检查脚本
└── scripts/deploy_update.sh        # 一键更新脚本
backend/wsgi.py                     # uWSGI / Gunicorn 共用入口
```

---

## 二、服务器准备（CentOS 7 / 8 / Stream）

> 下文默认安装路径：`/home/topuser/productCheck`  
> 运行用户：`root`  
> Nginx 已安装时，可跳过下文中的 Nginx 安装步骤。

### 2.0 检查必要程序是否已安装（部署前先跑一遍）

在项目根目录执行一键检查脚本：

```bash
cd /home/topuser/productCheck
chmod +x deploy/scripts/check_env.sh
bash deploy/scripts/check_env.sh
```

或手动逐条验证（复制整段到终端即可）：

```bash
echo "===== Git ====="
git --version

echo "===== Python（需 ≥3.10）====="
python3.11 --version 2>/dev/null || python3 --version
python3 -c "import sys; assert sys.version_info[:2] >= (3,10), 'Python 版本过低'"
python3 -m pip --version
python3 -m venv --help >/dev/null && echo "venv OK" || echo "venv 缺失"

echo "===== Node.js（需 ≥18）====="
node -v
npm -v

echo "===== MySQL ====="
mysql --version
systemctl is-active mysqld || systemctl is-active mysql

echo "===== Nginx ====="
nginx -v
systemctl is-active nginx

echo "===== 编译工具（可选）====="
gcc --version | head -n 1

echo "===== curl（健康检查用）====="
curl --version | head -n 1
```

| 组件 | 最低要求 | 未安装时安装命令（CentOS 8/Stream） |
|------|----------|-------------------------------------|
| Git | 任意较新版本 | `dnf -y install git` |
| Python | 3.10+ | `dnf -y install python3.11 python3.11-devel python3-pip` |
| venv | 内置模块 | `dnf -y install python3.11`（或对应版本 venv 包） |
| Node.js | 18+（仅本机构建需要） | Windows 本机安装；服务器可不装 |
| MySQL | 8.0+ | `dnf -y install mysql-server && systemctl enable --now mysqld` |
| Nginx | 任意较新版本 | 你已安装，可跳过 |
| gcc | 编译部分 Python 包 | `dnf -y install gcc openssl-devel libffi-devel` |
| curl | 健康检查 | `dnf -y install curl` |

全部 `[OK]` 后再继续部署。若有 `[FAIL]`，按上表补装后重新检查。

### 2.1 基础软件（缺什么装什么）

#### 推荐：本机构建前端（服务器无需 Node.js）

`frontend/dist` 已纳入 Git。在 **Windows 本机** 构建后提交推送，服务器 `git pull` 即可，**不必在 CentOS 安装 Node.js**。

**本机（Windows）每次改前端后：**

```bat
scripts\build_frontend.bat
git add frontend/dist
git commit -m "build: update frontend dist"
git push
```

**服务器更新：**

```bash
cd /home/topuser/productCheck
git pull
# 默认 deploy_update.sh 已跳过 npm build；仅后端变更时需：
systemctl restart product-check
# 或一键：bash deploy/scripts/deploy_update.sh
```

---

#### （可选）在服务器安装 Node.js 18

仅当你希望在服务器上执行 `npm run build` 时才需要安装，见下方 NodeSource / nvm 步骤。

```bash
# 1. 安装依赖
sudo yum install -y curl ca-certificates gcc-c++ make

# 2. 添加 NodeSource 18 源并安装
curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
sudo yum install -y nodejs

# 3. 验证（应显示 v18.x 或更高）
node -v
npm -v
```

若 NodeSource 安装失败，可用 **nvm**（用户级安装，同样可用）：

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
source ~/.bashrc
nvm install 18
nvm use 18
node -v
npm -v
```

> **说明**：默认采用本机构建 + Git 同步 `frontend/dist`，服务器可不装 Node。

#### CentOS 7 其它基础软件

```bash
sudo yum -y update
sudo yum -y install epel-release
sudo yum -y install git gcc openssl-devel libffi-devel curl
# MySQL、Python 3.10+ 请按实际环境安装（CentOS 7 默认 python3 可能较旧）
# Nginx 已安装可跳过
```

#### CentOS 8 / Stream

```bash
# CentOS 8 / Stream
sudo dnf -y update
sudo dnf -y install epel-release
sudo dnf -y install git mysql-server \
  python3.11 python3.11-devel python3-pip \
  gcc openssl-devel libffi-devel
# Nginx 已安装可跳过；若未安装：sudo dnf -y install nginx

curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
sudo dnf -y install nodejs
```

启动并设置开机自启：

```bash
sudo systemctl enable --now mysqld
sudo systemctl enable --now nginx
```

### 2.2 准备项目目录

以 **root** 部署，项目放在 `/home/topuser/productCheck`：

```bash
mkdir -p /home/topuser/productCheck /home/topuser/productCheck/logs /home/topuser/backup
```

### 2.3 MySQL 初始化

首次安装 MySQL 8 后，按提示改 root 密码（若系统提示 `mysql_secure_installation` 则执行一次）。

```bash
sudo mysql -uroot -p
```

```sql
CREATE DATABASE product_check
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER 'product_admin'@'localhost' IDENTIFIED BY '这里换成强密码';
GRANT ALL PRIVILEGES ON product_check.* TO 'product_admin'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

---

## 三、首次部署（完整步骤）

### 3.1 上传 / 拉取代码

**方式 A：Git（推荐）**

```bash
mkdir -p /home/topuser
cd /home/topuser
git clone https://github.com/Acederz/productCheck productCheck
cd /home/topuser/productCheck
```

**方式 B：本机打包上传**

在开发机打包（排除无关目录）：

```bash
# Windows PowerShell 示例思路：用 git archive 或手动压缩
# 不要带上 .venv、node_modules、frontend/dist（服务器上重建）
```

上传到服务器后解压到 `/home/topuser/productCheck` 即可。

### 3.2 配置后端环境变量

```bash
cd /home/topuser/productCheck
cp deploy/env.production.example backend/.env
vi backend/.env
```

至少改这些：

| 项 | 说明 |
|----|------|
| `FLASK_ENV` | 必须为 `production` |
| `SECRET_KEY` / `JWT_SECRET_KEY` | 换成随机长字符串（不要用示例值） |
| `MYSQL_*` | 与上面创建的库、账号一致 |
| `ADMIN_PASSWORD` | 首次建库管理员密码，登录后请再改 |

### 3.3 Python 虚拟环境与依赖

```bash
cd /home/topuser/productCheck
python3.11 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r backend/requirements.txt
```

### 3.4 初始化数据库表

```bash
cd /home/topuser/productCheck/backend
source ../.venv/bin/activate
python manage.py init-db
```

成功后可用默认管理员登录（见 `.env` 中 `ADMIN_USERNAME` / `ADMIN_PASSWORD`）。

### 3.5 前端静态文件（本机构建，已随 Git 同步）

默认方案：**不在服务器构建**。`git clone` 后应已有 `frontend/dist`，Nginx 直接托管即可。

若仓库中尚无 dist，在 Windows 本机执行：

```bat
scripts\build_frontend.bat
git add frontend/dist
git commit -m "build: frontend dist"
git push
```

然后在服务器 `git pull`。

### 3.6 配置 uWSGI（systemd）

#### 3.6.1 使用系统 uWSGI（本项目默认：`/usr/local/python312/bin/uwsgi`）

**前提：虚拟环境必须用同一套 Python 3.12 创建**，否则 uWSGI 加载不到 `.venv` 里的包。

```bash
# 1）确认系统 uwsgi
/usr/local/python312/bin/uwsgi --version
/usr/local/python312/bin/python3 --version

# 2）若还没有 .venv，或以前用别的 python 建的，请重建（会清空原 venv）
cd /home/topuser/productCheck
# 备份后重建（可选：先 mv .venv .venv.bak）
/usr/local/python312/bin/python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r backend/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 3）确认 Flask 等在 venv 中
python -c "import flask; print(flask.__version__)"
```

**uWSGI 配置文件位置：**

`/home/topuser/productCheck/deploy/uwsgi/product_check.ini`

关键项说明：

| 配置项 | 值 | 含义 |
|--------|-----|------|
| `chdir` | `.../backend` | 工作目录，才能找到 `wsgi.py` |
| `module` | `wsgi:app` | 加载 `wsgi.py` 里的 `app` |
| `virtualenv` | `.../.venv` | 使用项目虚拟环境里的依赖 |
| `http-socket` | `127.0.0.1:5174` | 给 Nginx 反代用 |

**systemd 启动命令：**

```
ExecStart=/usr/local/python312/bin/uwsgi --ini /home/topuser/productCheck/deploy/uwsgi/product_check.ini
```

#### 3.6.2 启动服务

```bash
mkdir -p /home/topuser/productCheck/logs

# 先手动试跑（确认能起来再交给 systemd）
cd /home/topuser/productCheck/backend
/usr/local/python312/bin/uwsgi --ini /home/topuser/productCheck/deploy/uwsgi/product_check.ini
# 另开一个终端：curl http://127.0.0.1:5174/api/health
# 成功后 Ctrl+C 结束手动进程

# 安装 systemd
cp /home/topuser/productCheck/deploy/systemd/product-check.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now product-check
systemctl status product-check

curl http://127.0.0.1:5174/api/health
# 日志：tail -f /home/topuser/productCheck/logs/uwsgi.log
```

### 3.7 配置 Nginx（已安装 Nginx 时）

```bash
sudo cp /home/topuser/productCheck/deploy/nginx/product_check.conf /etc/nginx/conf.d/
# 配置里 root 已指向 /home/topuser/productCheck/frontend/dist
# 若有域名，编辑 server_name
sudo nginx -t
sudo systemctl reload nginx
```

浏览器访问：`http://服务器IP:5173/`  
接口健康检查：`http://服务器IP:5173/api/health`（经 Nginx）或 `http://127.0.0.1:5174/api/health`（直连 uWSGI）

### 3.8 防火墙（若开了 firewalld）

```bash
# 对外开放前端端口 5173（后端 5174 建议只本机访问，不必开防火墙）
firewall-cmd --permanent --add-port=5173/tcp
firewall-cmd --reload
```

### 3.9（可选）HTTPS

有域名后可用 `certbot` 申请证书，再在 Nginx 增加 `listen 443 ssl` 配置。  
内网 IP 访问可先只用 HTTP。

---

## 四、日常运维命令

| 目的 | 命令 |
|------|------|
| 看后端状态 | `systemctl status product-check` |
| 重启后端 | `systemctl restart product-check` |
| 看后端日志 | `journalctl -u product-check -f` |
| 看 uWSGI 日志 | `tail -f /home/topuser/productCheck/logs/uwsgi.log` |
| 重载 Nginx | `nginx -t && systemctl reload nginx` |
| 看 Nginx 错误 | `tail -f /var/log/nginx/product_check_error.log` |

---

## 五、代码更新 / 功能迭代手册

### 5.1 推荐流程（开发 → 测试 → 上线）

```
本机开发（npm run dev）
    → 自测通过
    → git commit / push
    → 服务器拉取并构建
    → 重启 uWSGI（systemctl restart product-check）
    → Nginx 自动拿到新前端（dist 已覆盖）
    → 冒烟验证
```

### 5.2 一键更新（服务器）

脚本：`deploy/scripts/deploy_update.sh`

```bash
# 给执行权限（首次）
chmod +x /home/topuser/productCheck/deploy/scripts/deploy_update.sh

# 以 root 执行（默认运行用户即为 root）
bash /home/topuser/productCheck/deploy/scripts/deploy_update.sh

# 或指定分支
bash /home/topuser/productCheck/deploy/scripts/deploy_update.sh main
```

脚本会依次：

1. `git pull` 拉代码  
2. `pip install -r backend/requirements.txt`  
3. `frontend` 下 `npm install && npm run build`  
4. `systemctl restart product-check`  
5. 请求 `/api/health` 做健康检查  

> **注意**：更新前先备份数据库（见 5.5）。有表结构变更时，按 5.4 处理。

### 5.3 手动更新（更清晰，适合第一次）

```bash
cd /home/topuser/productCheck
source .venv/bin/activate

git pull

# 后端
pip install -r backend/requirements.txt

# 前端
cd frontend && npm install && npm run build && cd ..

systemctl restart product-check
curl http://127.0.0.1:5174/api/health
```

### 5.4 不同类型改动怎么发版

| 改动类型 | 要做什么 |
|----------|----------|
| 只改前端页面 | `frontend` 构建即可；**不必**重启 uWSGI（刷新浏览器强刷 `Ctrl+F5`） |
| 只改后端 Python | `pip install`（如有新依赖）+ **重启** `product-check` |
| 改了 `requirements.txt` | 必须 `pip install -r ...` 再重启 |
| 改了 Nginx 配置 | `nginx -t` 后 `reload nginx` |
| 改了 `.env` | 重启 `product-check` 才会生效 |
| 数据库表结构变更 | 见下文「迁移」；先备份再改 |

**当前项目初始化表结构**主要靠：

```bash
cd /home/topuser/productCheck/backend
source ../.venv/bin/activate
python manage.py init-db
```

`init-db` 适合**空库首次安装**。若生产库已有数据，**不要随意重复破坏性初始化**。  
有新增字段/新表时，推荐任选其一：

1. **Flask-Migrate（推荐后续规范）**  
   在开发环境生成迁移脚本，提交到仓库，生产执行：
   ```bash
   cd /home/topuser/productCheck/backend
   source ../.venv/bin/activate
   export FLASK_APP=wsgi:app
   flask db upgrade
   ```
2. **DBA / 手工 SQL**  
   把变更 SQL 写进发版说明，生产人工执行。

发版说明里应写清楚：本次是否含库表变更、是否要停服、回滚办法。

### 5.5 备份与回滚

**备份数据库（每次发版前建议做）：**

```bash
mysqldump -u product_admin -p product_check \
  --single-transaction --routines --triggers \
  > /home/topuser/backup/product_check_$(date +%F_%H%M).sql
```

**备份上传文件：**

```bash
tar -czf /home/topuser/backup/storage_$(date +%F_%H%M).tar.gz -C /home/topuser/productCheck storage
```

**代码回滚（Git）：**

```bash
cd /home/topuser/productCheck
git log --oneline -n 10
git checkout <上一版本commit或tag>
# 再执行前端 build + 重启服务（同更新流程）
```

**数据库回滚：** 用备份 SQL 恢复（会覆盖当前数据，需确认）：

```bash
mysql -u product_admin -p product_check < /home/topuser/backup/xxx.sql
```

### 5.6 发版检查清单（建议打印）

- [ ] 已备份数据库与 `storage/`
- [ ] 发版说明已写清：前端 / 后端 / 配置 / 库表是否变更
- [ ] 服务器 `git pull` 成功（或代码已同步）
- [ ] 后端依赖已安装
- [ ] 前端 `npm run build` 成功，`frontend/dist` 有新文件
- [ ] `systemctl restart product-check` 成功
- [ ] `curl /api/health` 正常
- [ ] 浏览器登录管理员 / 操作员各测一遍主流程
- [ ] 导入、分配、填写、审核、导出抽测通过

---

## 六、常见问题

### Q1：页面能开，接口 502

- 看后端是否起来：`systemctl status product-check`
- 看错误日志：`journalctl -u product-check -n 100`
- 确认 Nginx `proxy_pass` 端口与 uWSGI `http-socket` 一致（默认 `127.0.0.1:5174`）
- 看 uWSGI 日志：`tail -f /home/topuser/productCheck/logs/uwsgi.log`
- 浏览器访问前端：`http://服务器IP:5173/`

### Q2：上传 Excel 失败 / 413

- Nginx `client_max_body_size` 要 ≥ `50m`
- 后端 `.env` 与磁盘空间是否足够；`storage/uploads` 是否可写

### Q3：静态页面 404，刷新子路由失败

- 确认 `root` 指向 `frontend/dist`
- 确认有 `location / { try_files ... /index.html; }`

### Q4：中文日志乱码

生产已用 UTF-8 环境变量；查看日志时终端也建议 UTF-8。

### Q5：权限错误 Permission denied

```bash
mkdir -p /home/topuser/productCheck/logs storage/uploads storage/exports
chmod -R u+rwX /home/topuser/productCheck/storage /home/topuser/productCheck/logs
```

### Q6：本机构建前端，服务器只更新 dist

可以。流程：

1. 本机 `cd frontend && npm run build`
2. 把 `frontend/dist` 整目录上传覆盖服务器对应目录
3. 若后端也有改动，仍需重启 uWSGI（`systemctl restart product-check`）

---

## 七、安全建议（上线必看）

1. `.env` 权限：`chmod 600 backend/.env`，不要提交到 Git  
2. `SECRET_KEY` / `JWT_SECRET_KEY` / 数据库密码使用强随机值  
3. 首次登录后修改管理员密码；停用默认弱口令  
4. uWSGI 只绑定 `127.0.0.1:5174`，不要对公网开放 5174；对外只开前端 `5173`
5. 生产环境建议改用非 root 专用账号运行（当前按你的要求使用 root）  
6. 能上 HTTPS 尽量上；内网也建议限制来源 IP  
7. 定期备份数据库与 `storage/`

---

## 八、与 Windows 开发的关系

| 环境 | 怎么跑 |
|------|--------|
| Windows 开发 | `scripts\dev.bat` 或 `npm run dev`（见 [Windows首次运行手册](./Windows首次运行手册.md)） |
| CentOS 生产 | Nginx + uWSGI（本文） |

开发机改代码 → Git → 服务器按第五节更新即可。

---

*文档版本：与仓库同步维护。若安装路径、域名、Python 版本与本文不一致，以服务器实际环境为准，并同步改 systemd / Nginx 配置。*
