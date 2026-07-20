#!/usr/bin/env bash
# 检查 productCheck 生产部署所需程序是否已安装
# 用法：bash deploy/scripts/check_env.sh

set -u

APP_DIR="${APP_DIR:-/home/topuser/productCheck}"
VENV="${APP_DIR}/.venv"
PASS=0
WARN=0
FAIL=0

ok()   { echo "[OK]   $*"; PASS=$((PASS + 1)); }
warn() { echo "[WARN] $*"; WARN=$((WARN + 1)); }
fail() { echo "[FAIL] $*"; FAIL=$((FAIL + 1)); }

echo "========== productCheck 环境检查 =========="
echo "项目目录: ${APP_DIR}"
echo

# --- 基础命令 ---
if command -v git >/dev/null 2>&1; then
  ok "Git: $(git --version)"
else
  fail "Git 未安装（需要 git clone / 更新代码）"
fi

if command -v gcc >/dev/null 2>&1; then
  ok "GCC: $(gcc --version | head -n 1)"
else
  warn "GCC 未安装（部分 Python 包编译可能需要）"
fi

# --- Python ---
PY=""
for cmd in python3.11 python3.10 python3 python; do
  if command -v "$cmd" >/dev/null 2>&1; then
    ver=$("$cmd" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")' 2>/dev/null || echo "")
    if [[ -n "$ver" ]]; then
      major=$("$cmd" -c 'import sys; print(sys.version_info.major)' 2>/dev/null)
      minor=$("$cmd" -c 'import sys; print(sys.version_info.minor)' 2>/dev/null)
      if [[ "$major" -eq 3 && "$minor" -ge 10 ]]; then
        PY="$cmd"
        ok "Python: $cmd ($ver，满足 ≥3.10)"
        break
      fi
    fi
  fi
done
if [[ -z "$PY" ]]; then
  fail "Python 3.10+ 未找到"
fi

if command -v pip3 >/dev/null 2>&1 || [[ -n "$PY" && "$PY" -m pip --version >/dev/null 2>&1 ]]; then
  if [[ -n "$PY" ]]; then
    ok "pip: $($PY -m pip --version 2>/dev/null | head -n 1)"
  else
    ok "pip3: $(pip3 --version 2>/dev/null | head -n 1)"
  fi
else
  fail "pip 未安装"
fi

if [[ -n "$PY" ]] && "$PY" -m venv --help >/dev/null 2>&1; then
  ok "venv 模块可用"
else
  fail "python venv 不可用（需 python3-venv / python3.11-venv）"
fi

# --- Node / npm ---
if command -v node >/dev/null 2>&1; then
  node_ver=$(node -v 2>/dev/null | sed 's/^v//')
  node_major=$(echo "$node_ver" | cut -d. -f1)
  if [[ "$node_major" -ge 18 ]]; then
    ok "Node.js: v${node_ver}（满足 ≥18）"
  else
    warn "Node.js: v${node_ver}（建议 ≥18）"
  fi
else
  fail "Node.js 未安装（前端构建需要）"
fi

if command -v npm >/dev/null 2>&1; then
  ok "npm: $(npm -v)"
else
  fail "npm 未安装"
fi

# --- MySQL ---
if command -v mysql >/dev/null 2>&1; then
  ok "MySQL 客户端: $(mysql --version | head -n 1)"
else
  fail "mysql 客户端未安装"
fi

if systemctl is-active mysqld >/dev/null 2>&1 || systemctl is-active mysql >/dev/null 2>&1; then
  ok "MySQL 服务运行中"
elif systemctl list-unit-files 2>/dev/null | grep -qE 'mysqld|mysql'; then
  warn "MySQL 已安装但服务未运行（systemctl start mysqld）"
else
  fail "MySQL 服务未检测到"
fi

# --- Nginx ---
if command -v nginx >/dev/null 2>&1; then
  ok "Nginx: $(nginx -v 2>&1)"
else
  fail "Nginx 未安装"
fi

if systemctl is-active nginx >/dev/null 2>&1; then
  ok "Nginx 服务运行中"
else
  warn "Nginx 已安装但服务未运行"
fi

# --- curl（健康检查） ---
if command -v curl >/dev/null 2>&1; then
  ok "curl: $(curl --version | head -n 1)"
else
  warn "curl 未安装（健康检查脚本需要，建议安装）"
fi

# --- 项目虚拟环境与 Gunicorn ---
if [[ -d "$VENV" ]]; then
  ok "虚拟环境存在: ${VENV}"
  if [[ -x "${VENV}/bin/gunicorn" ]]; then
    ok "Gunicorn: $("${VENV}/bin/gunicorn" --version 2>&1 | head -n 1)"
  else
    warn "虚拟环境中 Gunicorn 未安装（pip install -r backend/requirements.txt）"
  fi
else
  warn "虚拟环境不存在: ${VENV}（首次部署需 python -m venv .venv）"
fi

# --- 项目目录 ---
for d in "$APP_DIR" "${APP_DIR}/backend" "${APP_DIR}/frontend" "${APP_DIR}/logs"; do
  if [[ -d "$d" ]]; then
    ok "目录存在: $d"
  else
    warn "目录不存在: $d"
  fi
done

if [[ -f "${APP_DIR}/frontend/dist/index.html" ]]; then
  ok "前端已构建: frontend/dist/index.html"
else
  warn "前端未构建（需 cd frontend && npm run build）"
fi

if [[ -f "${APP_DIR}/backend/.env" ]]; then
  ok "后端配置存在: backend/.env"
else
  warn "backend/.env 不存在（从 deploy/env.production.example 复制）"
fi

# --- systemd 服务 ---
if systemctl list-unit-files 2>/dev/null | grep -q '^product-check.service'; then
  if systemctl is-active product-check >/dev/null 2>&1; then
    ok "product-check 服务运行中"
    if curl -fsS "http://127.0.0.1:5000/api/health" >/dev/null 2>&1; then
      ok "后端健康检查 /api/health 正常"
    else
      warn "product-check 已运行但 /api/health 无响应"
    fi
  else
    warn "product-check 服务已安装但未运行"
  fi
else
  warn "product-check systemd 服务未安装"
fi

echo
echo "========== 汇总 =========="
echo "通过: ${PASS}  警告: ${WARN}  失败: ${FAIL}"
if [[ "$FAIL" -gt 0 ]]; then
  echo "结论: 缺少必要组件，请先安装后再部署。"
  exit 1
elif [[ "$WARN" -gt 0 ]]; then
  echo "结论: 基础环境可用，但有待完善项。"
  exit 0
else
  echo "结论: 环境检查全部通过。"
  exit 0
fi
