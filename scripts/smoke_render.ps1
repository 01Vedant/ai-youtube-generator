<#
.SYNOPSIS
    E2E smoke test for video rendering pipeline
#>

$ErrorActionPreference = "Stop"

$API_BASE = "http://127.0.0.1:8000"
$FRONTEND_BASE = "http://localhost:5173"
$MAX_POLL_ATTEMPTS = 60
$POLL_INTERVAL_SEC = 2

Write-Host ""
Write-Host "[SMOKE TEST] Starting E2E Smoke Test" -ForegroundColor Cyan
Write-Host ("=" * 70) -ForegroundColor Cyan

# Step 1: Check backend
Write-Host ""
Write-Host "[1/5] Checking backend status..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "$API_BASE/healthz" -Method GET -ErrorAction Stop
    Write-Host "[OK] Backend is running" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Backend is not running. Please start it first:" -ForegroundColor Red
    Write-Host "  cd platform; uvicorn backend.app.main:app --reload" -ForegroundColor Yellow
    exit 1
}

# Step 2: Create render plan
Write-Host ""
Write-Host "[2/5] Creating render plan..." -ForegroundColor Yellow
$renderPlan = @{
    topic = "Bhagavad Gita Wisdom"
    language = "en"
    voice = "F"
    fast_path = $true
    proxy = $true
    scenes = @(
        @{
            image_prompt = "Krishna on the battlefield with Arjuna, golden divine light"
            narration = "In the moment of despair, Krishna counsels Arjuna with divine wisdom"
            duration_sec = 4
        },
        @{
            image_prompt = "Arjuna with bow and arrow, determined expression, epic battlefield"
            narration = "Arjuna rises with newfound clarity and purpose from teachings"
            duration_sec = 4
        }
    )
} | ConvertTo-Json -Depth 10

Write-Host "  Plan: 2 scenes, 8 seconds total" -ForegroundColor Gray

# Step 3: Submit render job
Write-Host ""
Write-Host "[3/5] Submitting render job..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod `
        -Uri "$API_BASE/render" `
        -Method POST `
        -Headers @{ "Content-Type" = "application/json" } `
        -Body $renderPlan `
        -ErrorAction Stop
    
    $jobId = $response.job_id
    Write-Host "[OK] Job created: $jobId" -ForegroundColor Green
    Write-Host "  Status: $($response.status)" -ForegroundColor Gray
} catch {
    Write-Host "[ERROR] Failed to create render job" -ForegroundColor Red
    Write-Host "  $_" -ForegroundColor Red
    exit 1
}

# Step 4: Poll until completed
Write-Host ""
Write-Host "[4/5] Polling job status..." -ForegroundColor Yellow
$attempts = 0
$completed = $false

while ($attempts -lt $MAX_POLL_ATTEMPTS -and -not $completed) {
    $attempts++
    Start-Sleep -Seconds $POLL_INTERVAL_SEC
    
    try {
        $status = Invoke-RestMethod `
            -Uri "$API_BASE/render/$jobId/status" `
            -Method GET `
            -ErrorAction Stop
        
        $state = $status.state
        $progress = $status.progress_pct
        $step = $status.step
        
        Write-Host "  [$attempts] State: $state | Step: $step | Progress: $progress%" -ForegroundColor Gray
        
        if ($state -eq "completed" -or $state -eq "success") {
            Write-Host "[OK] Job completed!" -ForegroundColor Green
            
            if ($status.final_video_url) {
                Write-Host "  Video URL: $($status.final_video_url)" -ForegroundColor Green
                
                # Verify video file
                $videoCheckUrl = "$API_BASE/debug/video/$jobId"
                try {
                    $videoDebug = Invoke-RestMethod -Uri $videoCheckUrl -Method GET -ErrorAction Stop
                    Write-Host "  Video exists: $($videoDebug.exists) ($($videoDebug.size_mb) MB)" -ForegroundColor Gray
                } catch {
                    Write-Host "  [WARN] Could not verify video" -ForegroundColor Yellow
                }
            } else {
                Write-Host "  [WARN] No video URL" -ForegroundColor Yellow
            }
            
            $completed = $true
            break
        } elseif ($state -eq "error" -or $state -eq "failed") {
            Write-Host "[ERROR] Job failed: $($status.error)" -ForegroundColor Red
            exit 1
        }
    } catch {
        Write-Host "  [WARN] Status check failed: $_" -ForegroundColor Yellow
    }
}

if (-not $completed) {
    Write-Host "[ERROR] Job timeout after $MAX_POLL_ATTEMPTS attempts" -ForegroundColor Red
    exit 1
}

# Step 5: Open in browser
Write-Host ""
Write-Host "[5/5] Opening render status page..." -ForegroundColor Yellow
$renderUrl = "$FRONTEND_BASE/render/$jobId"

try {
    Start-Process $renderUrl
    Write-Host "[OK] Browser opened" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Failed to open browser" -ForegroundColor Red
    Write-Host "  Please open: $renderUrl" -ForegroundColor Yellow
}

# Summary
Write-Host ""
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host "[SUCCESS] Smoke test completed!" -ForegroundColor Green
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host ""
Write-Host "Job ID: $jobId" -ForegroundColor White
Write-Host "Frontend: $renderUrl" -ForegroundColor White
Write-Host "Status API: $API_BASE/render/$jobId/status" -ForegroundColor White
Write-Host "Debug API: $API_BASE/debug/video/$jobId" -ForegroundColor White
Write-Host ""
Write-Host "Test the video player in your browser!" -ForegroundColor Green
Write-Host ""
