#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Development server restart helper
.DESCRIPTION
  Stops any running backend processes and starts fresh uvicorn server
#>

$ErrorActionPreference = "Stop"

Write-Host "`n=== Restarting Backend Server ===" -ForegroundColor Cyan

# Stop existing Python/uvicorn processes
Write-Host "Stopping existing processes..." -ForegroundColor Yellow
Stop-Process -Name python,uvicorn -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

# Navigate to backend directory
Set-Location "c:\Users\vedant.sharma\Documents\ai-youtube-generator\platform\backend"

# Set environment variables
$env:SIMULATE_RENDER = "1"
$env:DEV_FAST = "1"
$env:API_KEY_ADMIN = "dev-admin-key"
$env:API_KEY_CREATOR = "dev-creator-key"

Write-Host "Starting uvicorn server..." -ForegroundColor Green
Write-Host "Working Directory: $PWD" -ForegroundColor Gray
Write-Host "SIMULATE_RENDER=$env:SIMULATE_RENDER" -ForegroundColor Gray
Write-Host "DEV_FAST=$env:DEV_FAST`n" -ForegroundColor Gray

# Start server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
