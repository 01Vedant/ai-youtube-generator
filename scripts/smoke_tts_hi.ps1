# smoke_tts_hi.ps1 - Hindi TTS Integration Smoke Test

param(
    [string]$Backend = "http://127.0.0.1:8000",
    [int]$TimeoutSec = 120
)

Write-Host "Hindi TTS Smoke Test" -ForegroundColor Cyan
Write-Host "====================" -ForegroundColor Cyan
Write-Host ""

# Test payload with Hindi narration
$payload = @{
    topic = "Hindi TTS Test"
    language = "hi"
    voice_id = "hi-IN-SwaraNeural"
    scenes = @(
        @{
            image_prompt = "Beautiful sunrise"
            narration = "सूर्योदय की सुंदरता देखिए।"
            duration_sec = 4
        },
        @{
            image_prompt = "Temple bells"
            narration = "मंदिर की घंटियां बज रही हैं।"
            duration_sec = 4
        }
    )
} | ConvertTo-Json -Depth 10

Write-Host "Step 1: POST /render with Hindi content" -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$Backend/render" `
        -Method POST `
        -ContentType "application/json" `
        -Body $payload `
        -TimeoutSec 30
    
    $jobId = $response.job_id
    Write-Host "  Job created: $jobId" -ForegroundColor Green
    Write-Host ""
} catch {
    Write-Host "  FAILED to create job" -ForegroundColor Red
    Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host "Step 2: Poll /render/$jobId/status" -ForegroundColor Yellow
$elapsed = 0
$interval = 2
$status = $null

while ($elapsed -lt $TimeoutSec) {
    try {
        $status = Invoke-RestMethod -Uri "$Backend/render/$jobId/status" `
            -Method GET `
            -TimeoutSec 10
        
        $state = $status.state
        $progress = $status.progress_pct
        
        Write-Host "  Status: $state, Progress: $($progress)%" -ForegroundColor Gray
        
        if ($state -eq "success") {
            Write-Host "  Job completed successfully" -ForegroundColor Green
            Write-Host ""
            break
        } elseif ($state -in @("failed", "error")) {
            Write-Host "  Job failed: $($status.error)" -ForegroundColor Red
            exit 1
        }
        
        Start-Sleep -Seconds $interval
        $elapsed += $interval
    } catch {
        Write-Host "  Status check failed: $($_.Exception.Message)" -ForegroundColor Yellow
        Start-Sleep -Seconds $interval
        $elapsed += $interval
    }
}

if ($elapsed -ge $TimeoutSec) {
    Write-Host "  Timeout after ${TimeoutSec}s" -ForegroundColor Red
    exit 1
}

Write-Host "Step 3: Validate Audio Metadata" -ForegroundColor Yellow

# Check job_summary.json
$summaryPath = "$Backend/artifacts/$jobId/job_summary.json"
try {
    $summary = Invoke-RestMethod -Uri $summaryPath -Method GET -TimeoutSec 10
    
    if ($summary.audio) {
        $audio = $summary.audio
        Write-Host "  Language: $($audio.lang)" -ForegroundColor Cyan
        Write-Host "  Voice ID: $($audio.voice_id)" -ForegroundColor Cyan
        Write-Host "  Provider: $($audio.provider)" -ForegroundColor Cyan
        Write-Host "  Paced: $($audio.paced)" -ForegroundColor Cyan
        Write-Host "  Total Duration: $($audio.total_duration_sec)s" -ForegroundColor Cyan
        Write-Host ""
        
        # Validate expected values
        $errors = @()
        if ($audio.lang -ne "hi") {
            $errors += "Expected lang=hi, got $($audio.lang)"
        }
        if ($audio.provider -notin @("edge", "mock")) {
            $errors += "Invalid provider: $($audio.provider)"
        }
        
        if ($errors.Count -gt 0) {
            Write-Host "  Validation warnings:" -ForegroundColor Yellow
            $errors | ForEach-Object { Write-Host "    - $_" -ForegroundColor Yellow }
            Write-Host ""
        } else {
            Write-Host "  Audio metadata validated" -ForegroundColor Green
            Write-Host ""
        }
    } else {
        Write-Host "  WARNING: No audio metadata in job_summary.json" -ForegroundColor Yellow
        Write-Host ""
    }
} catch {
    Write-Host "  WARNING: Could not fetch job_summary.json: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "Step 4: Check Audio Files" -ForegroundColor Yellow

# HEAD check for scene audio files
$audioChecks = @()
for ($i = 1; $i -le 2; $i++) {
    $audioUrl = "$Backend/artifacts/$jobId/audio/scene_$i.wav"
    try {
        $head = Invoke-WebRequest -Uri $audioUrl -Method HEAD -TimeoutSec 5
        $size = [math]::Round($head.Headers['Content-Length'][0] / 1KB, 2)
        Write-Host "  Scene $i audio: ${size} KB" -ForegroundColor Green
        $audioChecks += @{ scene = $i; status = "ok"; size_kb = $size }
    } catch {
        Write-Host "  Scene $i audio: NOT FOUND" -ForegroundColor Red
        $audioChecks += @{ scene = $i; status = "missing" }
    }
}
Write-Host ""

Write-Host "Step 5: Check Final Video" -ForegroundColor Yellow

if ($status.final_video_url) {
    $videoUrl = "$Backend$($status.final_video_url)"
    try {
        $head = Invoke-WebRequest -Uri $videoUrl -Method HEAD -TimeoutSec 10
        $size = [math]::Round($head.Headers['Content-Length'][0] / 1MB, 2)
        $type = $head.Headers['Content-Type'][0]
        
        Write-Host "  Video URL: $videoUrl" -ForegroundColor Cyan
        Write-Host "  Size: ${size} MB" -ForegroundColor Cyan
        Write-Host "  Type: $type" -ForegroundColor Cyan
        Write-Host ""
        
        if ($type -eq "video/mp4") {
            Write-Host "  Video artifact accessible" -ForegroundColor Green
        } else {
            Write-Host "  Unexpected content type: $type" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  Video not accessible: $($_.Exception.Message)" -ForegroundColor Red
    }
} else {
    Write-Host "  No final_video_url in response" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "====================" -ForegroundColor Cyan
Write-Host "Smoke Test Complete" -ForegroundColor Green
Write-Host "Job ID: $jobId" -ForegroundColor Gray
Write-Host ""

# Return structured result
$result = @{
    job_id = $jobId
    status = $status.state
    video_url = $status.final_video_url
    audio_metadata = $status.audio
    audio_files_checked = $audioChecks
}

$result | ConvertTo-Json -Depth 10 | Write-Output
