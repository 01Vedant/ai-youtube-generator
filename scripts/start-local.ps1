# scripts/start-local.ps1
# One-command local runner, health checks, and smoke test for backend/frontend

$ErrorActionPreference = "Stop"
$env:PATH = "C:/Users/vedant.sharma/Documents/node-v24.11.1-win-x64;" + $env:PATH
Write-Host "[INFO] Node version:"
try { & node -v } catch { Write-Host "Node not found in PATH"; exit 1 }
Write-Host "[INFO] npm version:"
try { & npm -v } catch { Write-Host "npm not found in PATH"; exit 1 }

# 1) Setup portable Node
. "$PSScriptRoot\setup-node.ps1"

$repoRoot = Split-Path $PSScriptRoot -Parent
$backendDir = "$repoRoot\backend\backend"

# 2) Start FastAPI backend in new PowerShell window
$env:PYTHONPATH = "$backendDir"
$backendCmd = "python -m uvicorn app.main:app --port 8000 --reload"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$backendDir'; $backendCmd" -WindowStyle Normal
Start-Sleep -Seconds 3

# 3) Build frontend
powershell -ExecutionPolicy Bypass -File "$PSScriptRoot\build-frontend.ps1"

# 4) Serve frontend in new PowerShell window
$serveCmd = "powershell -ExecutionPolicy Bypass -File '$PSScriptRoot\serve-frontend.ps1'"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $serveCmd -WindowStyle Normal
Start-Sleep -Seconds 3

# 5) Health checks
function Test-Status {
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8000/status" -UseBasicParsing -TimeoutSec 10
        $json = $resp.Content | ConvertFrom-Json
        if ($json.version) { Write-Host "✅ Backend /status: version=$($json.version)"; return $true }
        else { Write-Host "❌ Backend /status: missing version"; return $false }
    } catch { Write-Host "❌ Backend /status: $($_.Exception.Message)"; return $false }
}

function Test-Robots {
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8000/public/robots.txt" -UseBasicParsing -TimeoutSec 10
        if ($resp.StatusCode -eq 200 -and $resp.Headers["Content-Type"] -like "text/plain*") {
            Write-Host "✅ /public/robots.txt: 200 text/plain"
            return $true
        } else {
            Write-Host "❌ /public/robots.txt: $($resp.StatusCode) $($resp.Headers["Content-Type"])"
            return $false
        }
    } catch { Write-Host "❌ /public/robots.txt: $($_.Exception.Message)"; return $false }
}

function Test-Render {
    if ($env:SIMULATE_RENDER -ne "1") { Write-Host "(SIMULATE_RENDER not set, skipping render smoke)"; return $true }
    try {
        $body = @{ script = "test"; duration_sec = 6 } | ConvertTo-Json
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8000/render" -Method POST -Body $body -ContentType "application/json" -UseBasicParsing -TimeoutSec 10
        $job = $resp.Content | ConvertFrom-Json
        $jobId = $job.job_id
        Write-Host "[Render] Started job: $jobId"
        $success = $false
        for ($i=0; $i -lt 60; $i++) {
            Start-Sleep -Seconds 1
            $poll = Invoke-WebRequest -Uri "http://127.0.0.1:8000/render/$jobId" -UseBasicParsing -TimeoutSec 10
            $status = $poll.Content | ConvertFrom-Json
            if ($status.status -eq "success") {
                Write-Host "✅ Render success: $($status.artifacts | ConvertTo-Json)"
                $success = $true
                break
            } elseif ($status.status -eq "error") {
                Write-Host "❌ Render error: $($status.error)"
                break
            }
        }
        if (-not $success) { Write-Host "❌ Render did not complete in 60s" }
        return $success
    } catch { Write-Host "❌ Render smoke: $($_.Exception.Message)"; return $false }
}

$okStatus = Test-Status
$okRobots = Test-Robots
$okRender = Test-Render

# 6) Final summary
Write-Host "----- FINAL SUMMARY -----"
if ($okStatus) { Write-Host "✅ Backend /status OK" } else { Write-Host "❌ Backend /status FAILED" }
if ($okRobots) { Write-Host "✅ /public/robots.txt OK" } else { Write-Host "❌ /public/robots.txt FAILED" }
if ($okRender) { Write-Host "✅ Render smoke OK" } else { Write-Host "❌ Render smoke FAILED" }

# 7) Open browser
Start-Process "http://localhost:5173"
