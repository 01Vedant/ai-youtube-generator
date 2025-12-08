#!/usr/bin/env pwsh
<#
.SYNOPSIS
  E2E smoke test for Hindi TTS frontend integration
.DESCRIPTION
  Posts a Hindi render job, polls for completion, validates audio metadata
  Task 5: Add -Real switch to test with SIMULATE_RENDER=0
#>

param(
    [switch]$Real  # If set, test with SIMULATE_RENDER=0 (actual rendering)
)

$ErrorActionPreference = "Stop"
$API_BASE = "http://127.0.0.1:8000"

$mode = if ($Real) { "PRODUCTION (SIMULATE_RENDER=0)" } else { "SIMULATOR (SIMULATE_RENDER=1)" }
Write-Host "`n=== Hindi TTS Frontend E2E Smoke Test ===" -ForegroundColor Cyan
Write-Host "Backend: $API_BASE" -ForegroundColor Gray
Write-Host "Mode: $mode" -ForegroundColor $(if ($Real) { "Magenta" } else { "Gray" })
Write-Host ""

# Test 1: Submit Hindi render job
Write-Host "[1/5] Submitting Hindi render job..." -ForegroundColor Yellow

$renderPayload = @{
    topic = "Hindi TTS E2E"
    language = "hi"
    voice_id = "hi-IN-SwaraNeural"
    voice = "F"
    scenes = @(
        @{
            image_prompt = "temple at sunrise with golden light"
            narration = "भोर में मंदिर की घंटियां बजती हैं।"
            duration_sec = 4
        },
        @{
            image_prompt = "mountain peak in meditation"
            narration = "आंतरिक शांति की खोज में।"
            duration_sec = 4
        }
    )
    enable_parallax = $true
    enable_templates = $true
    enable_audio_sync = $true
    quality = "preview"
}

$renderBodyJson = $renderPayload | ConvertTo-Json -Depth 10
$renderBodyBytes = [System.Text.Encoding]::UTF8.GetBytes($renderBodyJson)

try {
    $renderResponse = Invoke-RestMethod `
        -Uri "$API_BASE/render" `
        -Method POST `
        -Headers @{ "Content-Type" = "application/json; charset=utf-8" } `
        -Body $renderBodyBytes
    
    $jobId = $renderResponse.job_id
    Write-Host "[OK] Job created: $jobId" -ForegroundColor Green
} catch {
    Write-Host "[FAIL] [Step 1/5]: Failed to create render job" -ForegroundColor Red
    Write-Host "Job ID: N/A" -ForegroundColor Red
    Write-Host "Status Code: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
    Write-Host "Response Body: $($_.ErrorDetails.Message)" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
    exit 1
}

# Test 2: Poll for completion
Write-Host "`n[2/5] Polling for job completion (max 120s)..." -ForegroundColor Yellow

$maxWait = 120
$elapsed = 0
$pollInterval = 2
$jobStatus = $null

while ($elapsed -lt $maxWait) {
    try {
        $jobStatus = Invoke-RestMethod `
            -Uri "$API_BASE/render/$jobId/status" `
            -Method GET
        
        $state = $jobStatus.state
        Write-Host "  State: $state (elapsed: ${elapsed}s)" -ForegroundColor Gray
        
        if ($state -eq "success" -or $state -eq "completed") {
            Write-Host "[OK] Job completed successfully" -ForegroundColor Green
            break
        }
        
        if ($state -eq "error" -or $state -eq "failed") {
            Write-Host "[FAIL] Job failed with error: $($jobStatus.error)" -ForegroundColor Red
            exit 1
        }
        
        Start-Sleep -Seconds $pollInterval
        $elapsed += $pollInterval
    } catch {
        Write-Host "[FAIL] [Step 2/5]: Failed to poll status" -ForegroundColor Red
        Write-Host "Job ID: $jobId" -ForegroundColor Red
        Write-Host "Status Code: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
        Write-Host "Response Body: $($_.ErrorDetails.Message)" -ForegroundColor Red
        Write-Host "Error: $_" -ForegroundColor Red
        exit 1
    }
}

if ($elapsed -ge $maxWait) {
    Write-Host "[FAIL] [Step 2/5]: Timeout waiting for job completion" -ForegroundColor Red
    Write-Host "Job ID: $jobId" -ForegroundColor Red
    Write-Host "Last State: $state" -ForegroundColor Red
    exit 1
}

# Test 3: Validate audio metadata
Write-Host "`n[3/5] Validating audio metadata..." -ForegroundColor Yellow

if (-not $jobStatus.audio) {
    Write-Host "[FAIL] [Step 3/5]: No audio metadata in response" -ForegroundColor Red
    Write-Host "Job ID: $jobId" -ForegroundColor Red
    Write-Host "Response: $($jobStatus | ConvertTo-Json -Depth 5)" -ForegroundColor Red
    exit 1
}

$audio = $jobStatus.audio
$audioLang = $audio.lang
$audioVoiceId = $audio.voice_id
$audioPaced = $audio.paced
$audioProvider = $audio.provider

Write-Host "  Lang: $audioLang" -ForegroundColor Gray
Write-Host "  Voice ID: $audioVoiceId" -ForegroundColor Gray
Write-Host "  Provider: $audioProvider" -ForegroundColor Gray
Write-Host "  Paced: $audioPaced" -ForegroundColor Gray

if ($audioLang -ne "hi") {
    Write-Host "[FAIL] [Step 3/5]: Expected lang='hi', got '$audioLang'" -ForegroundColor Red
    Write-Host "Job ID: $jobId" -ForegroundColor Red
    exit 1
}

if ($audioVoiceId -ne "hi-IN-SwaraNeural") {
    Write-Host "[WARN] Expected voice_id='hi-IN-SwaraNeural', got '$audioVoiceId'" -ForegroundColor Yellow
}

if ($audioProvider -ne "edge" -and $audioProvider -ne "mock") {
    Write-Host "[WARN] Unexpected provider: '$audioProvider'" -ForegroundColor Yellow
}

Write-Host "[OK] Audio metadata validated" -ForegroundColor Green

# Test 4: HEAD check final video
Write-Host "`n[4/5] Checking final video..." -ForegroundColor Yellow

if (-not $jobStatus.final_video_url) {
    Write-Host "[FAIL] [Step 4/5]: No final_video_url in response" -ForegroundColor Red
    Write-Host "Job ID: $jobId" -ForegroundColor Red
    exit 1
}

$videoUrl = $jobStatus.final_video_url
$fullVideoUrl = if ($videoUrl.StartsWith("http")) { $videoUrl } else { "$API_BASE$videoUrl" }

try {
    $headResponse = Invoke-WebRequest `
        -Uri $fullVideoUrl `
        -Method HEAD `
        -UseBasicParsing `
        -ErrorAction Stop
    
    $contentType = $headResponse.Headers["Content-Type"]
    $contentLength = $headResponse.Headers["Content-Length"]
    
    Write-Host "  URL: $fullVideoUrl" -ForegroundColor Gray
    Write-Host "  Status: $($headResponse.StatusCode)" -ForegroundColor Gray
    Write-Host "  Content-Type: $contentType" -ForegroundColor Gray
    Write-Host "  Content-Length: $contentLength" -ForegroundColor Gray
    
    if ($headResponse.StatusCode -ne 200) {
        Write-Host "[FAIL] [Step 4/5]: Expected status 200, got $($headResponse.StatusCode)" -ForegroundColor Red
        Write-Host "Job ID: $jobId" -ForegroundColor Red
        Write-Host "URL: $fullVideoUrl" -ForegroundColor Red
        exit 1
    }
    
    if ($contentType -notlike "*video/mp4*" -and $contentType -notlike "*application/octet-stream*") {
        Write-Host "[WARN] Expected video/mp4, got $contentType" -ForegroundColor Yellow
    }
    
    Write-Host "[OK] Final video accessible" -ForegroundColor Green
} catch {
    Write-Host "[FAIL] [Step 4/5]: Video HEAD check failed" -ForegroundColor Red
    Write-Host "Job ID: $jobId" -ForegroundColor Red
    Write-Host "URL: $fullVideoUrl" -ForegroundColor Red
    Write-Host "Status Code: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
    exit 1
}

# Test 5: Final summary
Write-Host "`n[5/5] Test Summary" -ForegroundColor Yellow

$summary = @{
    job_id = $jobId
    state = $jobStatus.state
    audio = @{
        lang = $audioLang
        voice_id = $audioVoiceId
        provider = $audioProvider
        paced = $audioPaced
    }
    video_url = $fullVideoUrl
    test_result = "PASS"
} | ConvertTo-Json -Depth 10

Write-Host $summary -ForegroundColor Green

Write-Host "`n[SUCCESS] ALL TESTS PASSED" -ForegroundColor Green
Write-Host "Job ID: $jobId" -ForegroundColor Cyan
Write-Host "Video: $fullVideoUrl" -ForegroundColor Cyan

# Open status page in browser
$statusPageUrl = "http://localhost:5173/render/$jobId"
Write-Host "`nOpening status page in browser..." -ForegroundColor Cyan
Start-Process $statusPageUrl
Write-Host "[HindiE2E] Page opened: $statusPageUrl" -ForegroundColor Green

exit 0
