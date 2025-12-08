# Task 5: Parallel smoke test for Hindi TTS with Edge provider
# Fire 3 Hindi jobs in parallel and verify all use provider="edge" and paced=true

param(
    [string]$ApiUrl = "http://127.0.0.1:8000"
)

Write-Host "=== Parallel Hindi TTS Smoke Test ===" -ForegroundColor Cyan
Write-Host "Testing 3 jobs in parallel with different voices and durations" -ForegroundColor Cyan
Write-Host ""

# Job configurations (simplified text to avoid encoding issues)
$jobs = @(
    @{
        name = "Swara-Short"
        payload = @{
            language = "hi"
            voice_id = "hi-IN-SwaraNeural"
            scenes = @(
                @{ image_prompt = "temple sunrise"; narration = "Test narration one"; duration_sec = 5 },
                @{ image_prompt = "mountain meditation"; narration = "Test narration two"; duration_sec = 5 }
            )
        }
    },
    @{
        name = "Diya-Medium"
        payload = @{
            language = "hi"
            voice_id = "hi-IN-DiyaNeural"
            scenes = @(
                @{ image_prompt = "yoga pose"; narration = "Test narration three"; duration_sec = 6 },
                @{ image_prompt = "peaceful lake"; narration = "Test narration four"; duration_sec = 6 },
                @{ image_prompt = "ancient wisdom"; narration = "Test narration five"; duration_sec = 5 }
            )
        }
    },
    @{
        name = "Swara-Long"
        payload = @{
            language = "hi"
            voice_id = "hi-IN-SwaraNeural"
            scenes = @(
                @{ image_prompt = "Krishna teaching"; narration = "Test narration six"; duration_sec = 7 },
                @{ image_prompt = "karma yoga"; narration = "Test narration seven"; duration_sec = 6 },
                @{ image_prompt = "dharma path"; narration = "Test narration eight"; duration_sec = 6 },
                @{ image_prompt = "peace within"; narration = "Test narration nine"; duration_sec = 5 }
            )
        }
    }
)

# Submit jobs
$jobIds = @()
foreach ($job in $jobs) {
    try {
        $response = Invoke-RestMethod -Uri "$ApiUrl/render" -Method POST -Body ($job.payload | ConvertTo-Json -Depth 10) -ContentType "application/json"
        $jobId = $response.job_id
        $jobIds += @{ id = $jobId; name = $job.name }
        Write-Host "[SUBMITTED] $($job.name): $jobId" -ForegroundColor Green
    } catch {
        Write-Host "[ERROR] Failed to submit $($job.name): $_" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "=== Waiting for jobs to complete ===" -ForegroundColor Cyan

# Poll until all complete (max 60s)
$timeout = 60
$elapsed = 0
$results = @()

while ($elapsed -lt $timeout) {
    Start-Sleep -Seconds 2
    $elapsed += 2
    
    $allComplete = $true
    foreach ($job in $jobIds) {
        if ($job.complete) { continue }
        
        try {
            $status = Invoke-RestMethod -Uri "$ApiUrl/render/$($job.id)/status" -Method GET
            
            if ($status.state -eq "completed") {
                $job.complete = $true
                $job.status = $status
                
                $provider = $status.audio.provider
                $paced = $status.audio.paced
                $duration_ms = $status.audio.duration_ms
                $scene_count = $status.audio.scenes.Count
                
                $results += @{
                    name = $job.name
                    job_id = $job.id
                    provider = $provider
                    paced = $paced
                    duration_ms = $duration_ms
                    scenes = $scene_count
                }
                
                Write-Host "[COMPLETE] $($job.name): provider=$provider, paced=$paced, duration=$($duration_ms)ms, scenes=$scene_count" -ForegroundColor Green
            } elseif ($status.state -eq "error") {
                Write-Host "[FAILED] $($job.name): $($status.error)" -ForegroundColor Red
                $allComplete = $false
                break
            } else {
                $allComplete = $false
            }
        } catch {
            Write-Host "[ERROR] Failed to check status for $($job.name): $_" -ForegroundColor Red
            $allComplete = $false
        }
    }
    
    if ($allComplete) {
        break
    }
}

Write-Host ""
Write-Host "=== Results Matrix ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Job Name          | Job ID (last 8) | Provider | Paced | Duration (ms) | Scenes" -ForegroundColor Yellow
Write-Host "--------------------------------------------------------------------------------" -ForegroundColor Yellow

foreach ($result in $results) {
    $jobIdShort = $result.job_id.Substring($result.job_id.Length - 8)
    $providerColor = if ($result.provider -eq "edge") { "Green" } else { "Red" }
    $pacedColor = if ($result.paced -eq $true) { "Green" } else { "Yellow" }
    
    Write-Host ("{0,-17} | {1,-15} | " -f $result.name, $jobIdShort) -NoNewline
    Write-Host ("{0,-8}" -f $result.provider) -ForegroundColor $providerColor -NoNewline
    Write-Host " | " -NoNewline
    Write-Host ("{0,-5}" -f $result.paced) -ForegroundColor $pacedColor -NoNewline
    Write-Host " | {0,13} | {1,6}" -f $result.duration_ms, $result.scenes
}

Write-Host ""

# Verify all passed
$allEdge = ($results | Where-Object { $_.provider -ne "edge" }).Count -eq 0
$allPaced = ($results | Where-Object { $_.paced -ne $true }).Count -eq 0

if ($allEdge -and $allPaced -and $results.Count -eq 3) {
    Write-Host "✅ ALL TESTS PASSED: All jobs used Edge provider and pacing" -ForegroundColor Green
    exit 0
} else {
    Write-Host "❌ TESTS FAILED:" -ForegroundColor Red
    if (-not $allEdge) {
        Write-Host "  - Not all jobs used Edge provider" -ForegroundColor Red
    }
    if (-not $allPaced) {
        Write-Host "  - Not all jobs were paced" -ForegroundColor Red
    }
    if ($results.Count -ne 3) {
        Write-Host "  - Expected 3 jobs, got $($results.Count)" -ForegroundColor Red
    }
    exit 1
}
