$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
if (-not $root) { $root = (Get-Location).Path }

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host " Candidate Intelligence Platform Launcher " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

Write-Host "`n[1/4] Checking Python environment (uv sync)..." -ForegroundColor Yellow
uv sync

Write-Host "`n[2/4] Checking UI dependencies..." -ForegroundColor Yellow
if (-not (Test-Path "$root\ui\node_modules")) {
    Push-Location "$root\ui"
    npm install
    Pop-Location
} else {
    Write-Host "UI packages ready." -ForegroundColor Green
}

Write-Host "`n[3/4] Starting FastAPI backend on http://127.0.0.1:8000..." -ForegroundColor Yellow
Start-Process powershell -WorkingDirectory $root -ArgumentList "-NoExit", "-Command", "Write-Host '--- FastAPI Backend [Port 8000] ---' -ForegroundColor Cyan; uv run uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload"

Write-Host "`n[4/4] Starting Vite Frontend on http://localhost:5173..." -ForegroundColor Yellow
Start-Process powershell -WorkingDirectory "$root\ui" -ArgumentList "-NoExit", "-Command", "Write-Host '--- Vite Frontend [Port 5173] ---' -ForegroundColor Cyan; npm run dev"

Write-Host "`nWaiting for servers to start..." -ForegroundColor Gray
for ($i = 0; $i -lt 15; $i++) {
    try {
        $res = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($res.StatusCode -eq 200) { break }
    } catch {}
    Start-Sleep -Seconds 1
}
Start-Sleep -Seconds 2

Write-Host "`nOpening http://localhost:5173 in browser..." -ForegroundColor Cyan
Start-Process "http://localhost:5173"

Write-Host "`n=======================================================" -ForegroundColor Green
Write-Host " Candidate Intelligence Platform is now running!" -ForegroundColor Green
Write-Host " - Frontend UI: http://localhost:5173" -ForegroundColor Green
Write-Host " - Backend API: http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "=======================================================" -ForegroundColor Green
