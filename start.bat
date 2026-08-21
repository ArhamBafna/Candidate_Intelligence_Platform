@echo off
title Candidate Intelligence Platform Launcher
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "& ([ScriptBlock]::Create((Get-Content -Path '%~f0' | Select-Object -Skip 6 | Out-String)))"
exit
rem --- PURE POWERSHELL CODE STARTS BELOW ---

$ErrorActionPreference = "Stop"
$root = (Get-Location).Path

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

function Test-PortOpen([string]$hostName, [int]$port) {
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $iar = $tcp.BeginConnect($hostName, $port, $null, $null)
        $wait = $iar.AsyncWaitHandle.WaitOne(300, $false)
        if ($wait -and $tcp.Connected) {
            $tcp.EndConnect($iar)
            $tcp.Close()
            return $true
        }
        $tcp.Close()
        return $false
    } catch {
        return $false
    }
}

$backendRunning = Test-PortOpen "127.0.0.1" 8000
if (-not $backendRunning) {
    Write-Host "`n[3/4] Starting FastAPI backend on http://127.0.0.1:8000..." -ForegroundColor Yellow
    Start-Process powershell -WorkingDirectory $root -ArgumentList "-NoExit", "-Command", "Write-Host '--- FastAPI Backend [Port 8000] ---' -ForegroundColor Cyan; uv run uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload"
} else {
    Write-Host "`n[3/4] FastAPI backend already running on port 8000." -ForegroundColor Green
}

$frontendRunning = Test-PortOpen "127.0.0.1" 5173
if (-not $frontendRunning) {
    Write-Host "`n[4/4] Starting Vite Frontend on http://localhost:5173..." -ForegroundColor Yellow
    Start-Process powershell -WorkingDirectory "$root\ui" -ArgumentList "-NoExit", "-Command", "Write-Host '--- Vite Frontend [Port 5173] ---' -ForegroundColor Cyan; npm run dev"
} else {
    Write-Host "`n[4/4] Vite frontend already running on port 5173." -ForegroundColor Green
}

Write-Host "`nWaiting for servers to be ready..." -ForegroundColor Gray
for ($i = 0; $i -lt 15; $i++) {
    try {
        $res = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($res.StatusCode -eq 200) { break }
    } catch {}
    Start-Sleep -Seconds 1
}
Start-Sleep -Seconds 1

Write-Host "`nOpening http://localhost:5173 in browser..." -ForegroundColor Cyan
Start-Process "http://localhost:5173"

Write-Host "`n=======================================================" -ForegroundColor Green
Write-Host " Candidate Intelligence Platform is now running!" -ForegroundColor Green
Write-Host " - Frontend UI: http://localhost:5173" -ForegroundColor Green
Write-Host " - Backend API: http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "=======================================================" -ForegroundColor Green
Start-Sleep -Seconds 1
