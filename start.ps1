# Candidate Intelligence Platform (CIP) Startup Script
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
if (-not $ScriptDir) { $ScriptDir = Get-Location }
Set-Location $ScriptDir

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host " Candidate Intelligence Platform Launcher " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# 1. Sync Python Dependencies
Write-Host "`n[1/4] Checking Python environment (uv sync)..." -ForegroundColor Yellow
uv sync

# 2. Check UI Dependencies
Write-Host "`n[2/4] Checking UI dependencies..." -ForegroundColor Yellow
if (-not (Test-Path "$ScriptDir\ui\node_modules")) {
    Write-Host "Installing UI node_modules..." -ForegroundColor Gray
    Push-Location "$ScriptDir\ui"
    npm install
    Pop-Location
} else {
    Write-Host "UI packages already installed." -ForegroundColor Green
}

# 3. Start Backend API in a new window
Write-Host "`n[3/4] Starting FastAPI backend on http://127.0.0.1:8000..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$ScriptDir'; Write-Host '--- FastAPI Backend (Port 8000) ---' -ForegroundColor Cyan; uv run uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload"

# 4. Start Frontend UI in a new window
Write-Host "`n[4/4] Starting Vite Frontend on http://localhost:5173..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$ScriptDir\ui'; Write-Host '--- Vite Frontend (Port 5173) ---' -ForegroundColor Cyan; npm run dev"

# Wait for backend & frontend to initialize
Write-Host "`nWaiting for servers to start..." -ForegroundColor Gray
$backendReady = $false
for ($i = 0; $i -lt 15; $i++) {
    try {
        $res = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($res.StatusCode -eq 200) {
            $backendReady = $true
            break
        }
    } catch {}
    Start-Sleep -Seconds 1
}

Start-Sleep -Seconds 2

# Open browser
Write-Host "`nOpening http://localhost:5173 in browser..." -ForegroundColor Cyan
Start-Process "http://localhost:5173"

Write-Host "`n=======================================================" -ForegroundColor Green
Write-Host " Candidate Intelligence Platform is now running!" -ForegroundColor Green
Write-Host " - Frontend UI: http://localhost:5173" -ForegroundColor Green
Write-Host " - Backend API: http://127.0.0.1:8000 (Docs: http://127.0.0.1:8000/docs)" -ForegroundColor Green
Write-Host "=======================================================" -ForegroundColor Green
