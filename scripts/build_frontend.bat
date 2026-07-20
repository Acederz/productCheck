@echo off
chcp 65001 >nul
cd /d "%~dp0..\frontend"

where npm >nul 2>&1
if errorlevel 1 (
  echo ERROR: npm not found. Install Node.js 18+ first.
  exit /b 1
)

echo STEP: npm install
call npm install
if errorlevel 1 exit /b 1

echo STEP: npm run build
call npm run build
if errorlevel 1 exit /b 1

echo.
echo DONE: frontend\dist built.
echo Next: git add frontend/dist && git commit && git push
echo Server: git pull in /home/topuser/productCheck (no Node.js needed)
