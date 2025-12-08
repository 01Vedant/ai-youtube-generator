#!/usr/bin/env pwsh
# Backend Server Startup Script
# Run from platform/backend directory

$ErrorActionPreference = "Stop"

# Change to backend directory
Set-Location $PSScriptRoot

# Set environment variables
$env:SIMULATE_RENDER = "1"
$env:PYTHONPATH = $PWD

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Starting Backend Server" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Working Directory: $PWD"
Write-Host "PYTHONPATH: $env:PYTHONPATH"
Write-Host "SIMULATE_RENDER: $env:SIMULATE_RENDER"
Write-Host ""

# Start server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
