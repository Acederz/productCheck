# Push project to GitHub (PowerShell)
# Usage:
#   .\scripts\push_to_github.ps1 -RepoUrl "https://github.com/Acedez/productCheck.git"
#   .\scripts\push_to_github.ps1 -RepoUrl "https://github.com/Acedez/productCheck.git" -Message "init"

param(
    [Parameter(Mandatory = $true)]
    [string]$RepoUrl,

    [string]$Message = "chore: init project"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "INFO: Project dir = $ProjectRoot" -ForegroundColor Cyan

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: git not found. Install from https://git-scm.com/download/win" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path ".git")) {
    Write-Host "STEP: git init" -ForegroundColor Yellow
    git init
    git branch -M main
}

Write-Host "STEP: git add (node_modules, .venv, .env, dist are ignored)" -ForegroundColor Yellow
git add .
git status -s

$confirm = Read-Host "Push to $RepoUrl ? [Y/N]"
if ($confirm -notmatch '^[Yy]$') {
    Write-Host "Cancelled." -ForegroundColor Gray
    exit 0
}

git diff --cached --quiet 2>$null
$hasStagedChanges = ($LASTEXITCODE -ne 0)
if ($hasStagedChanges) {
    Write-Host "STEP: git commit" -ForegroundColor Yellow
    git commit -m $Message
} else {
    Write-Host "INFO: No changes to commit, push only." -ForegroundColor Gray
}

$remotes = @(git remote)
if ($remotes -contains 'origin') {
    Write-Host "STEP: git remote set-url origin" -ForegroundColor Yellow
    git remote set-url origin $RepoUrl
} else {
    Write-Host "STEP: git remote add origin" -ForegroundColor Yellow
    git remote add origin $RepoUrl
}

Write-Host "STEP: git push -u origin main" -ForegroundColor Yellow
git push -u origin main

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: push failed. Check GitHub login or run: git pull origin main --rebase" -ForegroundColor Red
    exit 1
}

Write-Host "DONE: Pushed to $RepoUrl" -ForegroundColor Green
