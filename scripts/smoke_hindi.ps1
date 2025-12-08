# smoke_hindi.ps1 - Hindi narration smoke test
# Tests end-to-end Hindi narration via /render API

param(
    [string]$Backend = "http://127.0.0.1:8000",
    [int]$TimeoutSec = 120
)

Write-Host "Hindi Narration Smoke Test" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host ""

# Test payload - Hindi devotional content
$payload = @{
    content_type = "devotional_shorts"
    topic = "Meera Bhakti Path"
    language = "hi"
    voice = "hi_female_soft"
    duration_sec = 60
    scenes = @(
        @{
            narration = "Bhore ki pehli kiran mein Meera mandir mein pravesh karti hai"
            visual = "Temple dawn with soft sunlight"
            duration_sec = 5
        },
        @{
            narration = "Deepak ki lau hilti hai shraddha ka prateek"
            visual = "Flickering diya lamp"
            duration_sec = 5
        }
    )
} | ConvertTo-Json -Depth 10

Write-Host "Step 1: POST /render" -ForegroundColor Yellow
Write-Host "Language: hi, Voice: hi_female_soft" -ForegroundColor Gray
Write-Host ""

try {
    $response = Invoke-RestMethod -Uri "$Backend/render" `
        -Method POST `
        -ContentType "application/json" `
        -Body $payload `
        -TimeoutSec 30
    
    $jobId = $response.job_id
    Write-Host "✅ Job created: $jobId" -ForegroundColor Green
    Write-Host ""
} catch {
    Write-Host "❌ Failed to create job" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

Write-Host "Step 2: Poll status" -ForegroundColor Yellow
$elapsed = 0
$interval = 2
$status = $null

while ($elapsed -lt $TimeoutSec) {
    try {
        $status = Invoke-RestMethod -Uri "$Backend/render/$jobId/status" `
            -Method GET `
            -TimeoutSec 10
        
        $state = $status.status
        $progress = $status.progress
        
        Write-Host "  Status: $state, Progress: $($progress)%" -ForegroundColor Gray
        
        if ($state -eq "success") {
            Write-Host "✅ Job completed successfully" -ForegroundColor Green
            Write-Host ""
            break
        } elseif ($state -in @("failed", "error")) {
            Write-Host "❌ Job failed: $($status.error)" -ForegroundColor Red
            exit 1
        }
        
        Start-Sleep -Seconds $interval
        $elapsed += $interval
    } catch {
        Write-Host "⚠️  Status check failed: $($_.Exception.Message)" -ForegroundColor Yellow
        Start-Sleep -Seconds $interval
        $elapsed += $interval
    }
}

if ($elapsed -ge $TimeoutSec) {
    Write-Host "❌ Timeout after ${TimeoutSec}s" -ForegroundColor Red
    exit 1
}

Write-Host "Step 3: Validate Hindi Audio Metadata" -ForegroundColor Yellow

if ($status.audio) {
    $audio = $status.audio
    Write-Host "  Language:     $($audio.language)" -ForegroundColor Cyan
    Write-Host "  Voice:        $($audio.voice)" -ForegroundColor Cyan
    Write-Host "  Provider:     $($audio.provider)" -ForegroundColor Cyan
    Write-Host "  LUFS:         $($audio.lufs) LU" -ForegroundColor Cyan
    Write-Host "  Ducking:      $($audio.ducking_db) dB" -ForegroundColor Cyan
    Write-Host "  Stretch Used: $($audio.stretch_used)" -ForegroundColor Cyan
    Write-Host ""
    
    # Validate expected values
    $errors = @()
    if ($audio.language -ne "hi") {
        $errors += "Expected language=hi, got $($audio.language)"
    }
    if ($audio.provider -notin @("azure", "elevenlabs", "fallback")) {
        $errors += "Invalid provider: $($audio.provider)"
    }
    if ([Math]::Abs($audio.lufs + 16) -gt 2) {
        $errors += "LUFS out of range: $($audio.lufs) (expected -16 ±2 LU)"
    }
    
    if ($errors.Count -gt 0) {
        Write-Host "⚠️  Validation warnings:" -ForegroundColor Yellow
        $errors | ForEach-Object { Write-Host "  - $_" -ForegroundColor Yellow }
        Write-Host ""
    } else {
        Write-Host "✅ Audio metadata validated" -ForegroundColor Green
        Write-Host ""
    }
    
    # Show per-scene durations
    if ($audio.files.per_scene) {
        Write-Host "  Per-Scene Audio:" -ForegroundColor Gray
        for ($i = 0; $i -lt $audio.files.per_scene.Count; $i++) {
            Write-Host "    Scene $($i+1): $($audio.files.per_scene[$i])" -ForegroundColor Gray
        }
        Write-Host ""
    }
} else {
    Write-Host "⚠️  No audio metadata in response" -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "Step 4: Check Video Artifact" -ForegroundColor Yellow

if ($status.final_video_url) {
    $videoUrl = $status.final_video_url
    Write-Host "  Video URL: $videoUrl" -ForegroundColor Cyan
    
    try {
        $head = Invoke-WebRequest -Uri $videoUrl -Method HEAD -TimeoutSec 10
        $size = [math]::Round($head.Headers['Content-Length'][0] / 1MB, 2)
        $type = $head.Headers['Content-Type'][0]
        
        Write-Host "  Size: ${size} MB" -ForegroundColor Cyan
        Write-Host "  Type: $type" -ForegroundColor Cyan
        Write-Host ""
        
        if ($type -eq "video/mp4") {
            Write-Host "✅ Video artifact accessible" -ForegroundColor Green
        } else {
            Write-Host "⚠️  Unexpected content type: $type" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "⚠️  Video not yet accessible: $($_.Exception.Message)" -ForegroundColor Yellow
    }
} else {
    Write-Host "⚠️  No final_video_url in response" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=================================" -ForegroundColor Cyan
Write-Host "✅ Smoke Test Complete" -ForegroundColor Green
Write-Host "Job ID: $jobId" -ForegroundColor Gray
Write-Host ""

# Return structured result for automation
$result = @{
    job_id = $jobId
    status = $status.status
    video_url = $status.final_video_url
    audio = $status.audio
}

$result | ConvertTo-Json -Depth 10 | Write-Output
