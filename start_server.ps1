# Start server script
Set-Location "c:\Users\vedant.sharma\Documents\ai-youtube-generator\platform\backend"
$env:SIMULATE_RENDER = "1"
$env:API_KEY_ADMIN = "dev-admin-key"
$env:API_KEY_CREATOR = "dev-creator-key"

Write-Host "Starting Bhakti Video Generator API Server..."
Write-Host "Working Directory: $PWD"
Write-Host "SIMULATE_RENDER=$env:SIMULATE_RENDER"
Write-Host ""

uvicorn app.main:app --host 127.0.0.1 --port 8000
