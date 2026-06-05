#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Start all Octet dev services: Docker infra, FastAPI backend, Vite frontend.
  Each service opens in its own PowerShell window so logs stay separate.
  Run from the repo root.
#>

$root = $PSScriptRoot

Write-Host "Starting Docker infrastructure (PostgreSQL + Redis)..." -ForegroundColor Cyan
docker compose -f "$root\infra\docker-compose.dev.yml" up -d

Write-Host "Waiting for containers to be healthy..." -ForegroundColor Cyan
$timeout = 30
$elapsed = 0
do {
    Start-Sleep -Seconds 2
    $elapsed += 2
    $status = docker compose -f "$root\infra\docker-compose.dev.yml" ps --format json 2>$null |
        ConvertFrom-Json -ErrorAction SilentlyContinue
    $allHealthy = $status | Where-Object { $_.Health -notin @('healthy', '') } | Measure-Object
    if ($allHealthy.Count -eq 0) { break }
} while ($elapsed -lt $timeout)

Write-Host "Starting FastAPI backend..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    '-NoExit',
    '-Command',
    "cd '$root\apps\api'; .\.venv\Scripts\Activate.ps1; uvicorn app.main:app --reload --port 8000"
)

Write-Host "Starting Vite frontend..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    '-NoExit',
    '-Command',
    "cd '$root'; pnpm dev"
)

Write-Host ""
Write-Host "All services started." -ForegroundColor Green
Write-Host "  Frontend : http://localhost:5173" -ForegroundColor Green
Write-Host "  Backend  : http://localhost:8000" -ForegroundColor Green
Write-Host "  API docs : http://localhost:8000/docs" -ForegroundColor Green
