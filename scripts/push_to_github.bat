@echo off
setlocal EnableDelayedExpansion

REM Push project to GitHub (safe ASCII batch, no encoding issues)
REM Usage: scripts\push_to_github.bat https://github.com/USER/REPO.git [commit message]

set "REPO_URL=%~1"
set "COMMIT_MSG=%~2"
if "%COMMIT_MSG%"=="" set "COMMIT_MSG=chore: init project"

if "%REPO_URL%"=="" goto usage

cd /d "%~dp0\.."
echo [INFO] Project dir: %CD%

where git >nul 2>&1
if errorlevel 1 (
  echo [ERROR] git not found. Install from https://git-scm.com/download/win
  exit /b 1
)

if not exist ".git" (
  echo [STEP] git init
  git init
  git branch -M main
)

echo [STEP] git add
git add .
git status -s

echo.
set /p CONFIRM=Push to %REPO_URL% ? [Y/N]:
if /I not "!CONFIRM!"=="Y" (
  echo Cancelled.
  exit /b 0
)

git diff --cached --quiet
if errorlevel 1 (
  echo [STEP] git commit
  git commit -m "%COMMIT_MSG%"
) else (
  echo [INFO] No changes to commit, push only.
)

git remote get-url origin >nul 2>&1
if errorlevel 1 (
  echo [STEP] git remote add origin
  git remote add origin "%REPO_URL%"
) else (
  echo [STEP] git remote set-url origin
  git remote set-url origin "%REPO_URL%"
)

echo [STEP] git push -u origin main
git push -u origin main
if errorlevel 1 (
  echo [ERROR] push failed. Check login or run: git pull origin main --rebase
  exit /b 1
)

echo [DONE] Pushed to %REPO_URL%
exit /b 0

:usage
echo.
echo Usage:
echo   scripts\push_to_github.bat https://github.com/USER/REPO.git
echo   scripts\push_to_github.bat https://github.com/USER/REPO.git "your commit message"
echo.
echo Create an empty repo on GitHub first (no README, no .gitignore).
exit /b 1
