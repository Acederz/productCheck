#!/usr/bin/env bash
# 生产环境代码更新脚本（在服务器上执行）
# 用法：
#   sudo bash deploy/scripts/deploy_update.sh
#   sudo bash deploy/scripts/deploy_update.sh main
#
# 环境变量可覆盖：APP_DIR / APP_USER / SERVICE_NAME

set -euo pipefail

APP_DIR="${APP_DIR:-/home/topuser/productCheck}"
APP_USER="${APP_USER:-root}"
VENV="${APP_DIR}/.venv"
SERVICE_NAME="${SERVICE_NAME:-product-check}"
BRANCH="${1:-}"

echo "==> 项目目录: ${APP_DIR}"
cd "${APP_DIR}"

# 以应用用户执行一段命令（root 时直接执行）
run_as_app() {
  if [[ "${APP_USER}" == "root" ]] || [[ "$(id -un)" == "${APP_USER}" ]]; then
    bash -lc "$*"
  else
    sudo -u "${APP_USER}" -H bash -lc "$*"
  fi
}

echo "==> 拉取最新代码"
if [[ -d .git ]]; then
  if [[ -z "${BRANCH}" ]]; then
    BRANCH="$(run_as_app "cd '${APP_DIR}' && git rev-parse --abbrev-ref HEAD")"
  fi
  run_as_app "cd '${APP_DIR}' && git fetch --all --prune && git checkout '${BRANCH}' && git pull --ff-only origin '${BRANCH}'"
else
  echo "未检测到 git 仓库，跳过拉取（请自行同步代码后再运行本脚本）"
fi

echo "==> 更新后端依赖"
run_as_app "cd '${APP_DIR}' && source '${VENV}/bin/activate' && pip install -r backend/requirements.txt"

# 默认不在服务器构建前端（frontend/dist 由 Windows 本机构建后提交到 Git）
# 若服务器已装 Node 且要在服务器构建：SKIP_FRONTEND_BUILD=0 bash deploy/scripts/deploy_update.sh
SKIP_FRONTEND_BUILD="${SKIP_FRONTEND_BUILD:-1}"
if [[ "${SKIP_FRONTEND_BUILD}" == "1" ]]; then
  echo "==> 跳过服务器前端构建（使用 Git 中的 frontend/dist）"
  if [[ ! -f "${APP_DIR}/frontend/dist/index.html" ]]; then
    echo "警告: frontend/dist/index.html 不存在，请在本机执行 scripts/build_frontend.bat 后提交推送"
  fi
else
  echo "==> 构建前端（服务器本地 npm build）"
  run_as_app "cd '${APP_DIR}/frontend' && npm install && npm run build"
fi

echo "==> 检查存储与日志目录权限"
run_as_app "cd '${APP_DIR}' && mkdir -p storage/uploads storage/exports logs && chmod -R u+rwX storage logs"

echo "==> 重载后端服务"
if command -v systemctl >/dev/null 2>&1; then
  if [[ "$(id -u)" -eq 0 ]]; then
    systemctl restart "${SERVICE_NAME}"
    systemctl --no-pager --full status "${SERVICE_NAME}" | head -n 20
  else
    echo "当前非 root，请手动执行: sudo systemctl restart ${SERVICE_NAME}"
  fi
fi

echo "==> 健康检查"
sleep 1
curl -fsS "http://127.0.0.1:5000/api/health" && echo || echo "健康检查失败，请查看 journalctl -u ${SERVICE_NAME}"

echo "==> 更新完成"
