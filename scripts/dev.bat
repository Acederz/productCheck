@echo off
REM UTF-8 代码页，避免 Flask 中文访问日志在 Windows 终端乱码
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
echo 正在启动市场数据分类管理平台（后端 + 前端）...
npm run dev
