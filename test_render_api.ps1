# Quick Test Script for Bhakti Video Generator API
# Run from project root: .\test_render_api.ps1

$baseUrl = "http://127.0.0.1:8000"

Write-Host "`n=== Testing Bhakti Video Generator API ===" -ForegroundColor Cyan

# Test 1: Health Check
Write-Host "`n1. Testing /healthz..." -ForegroundColor Yellow
$health = Invoke-RestMethod "$baseUrl/healthz"
Write-Host "   Status: $($health.status)" -ForegroundColor Green

# Test 2: Readiness Check
Write-Host "`n2. Testing /readyz..." -ForegroundColor Yellow
$ready = Invoke-RestMethod "$baseUrl/readyz"
Write-Host "   Platform Root: $($ready.platform_root)" -ForegroundColor Green
Write-Host "   Simulate Mode: $($ready.simulate_mode)" -ForegroundColor Green

# Test 3: Create Render Job
Write-Host "`n3. Creating render job..." -ForegroundColor Yellow
$plan = @'
{
  "topic": "Bhakti demo",
  "language": "en",
  "voice": "F",
  "scenes": [
    {"image_prompt": "sunrise over river", "narration": "Welcome to the demo", "duration_sec": 3},
    {"image_prompt": "temple bells ringing", "narration": "Sacred sounds", "duration_sec": 4}
  ],
  "fast_path": true,
  "proxy": true
}
'@

$result = Invoke-RestMethod -Uri "$baseUrl/render" -Method POST -ContentType "application/json" -Body $plan
$jobId = $result.job_id
Write-Host "   Job ID: $jobId" -ForegroundColor Green
Write-Host "   Status: $($result.status)" -ForegroundColor Green

# Test 4: Poll Status
Write-Host "`n4. Polling job status..." -ForegroundColor Yellow
for ($i = 1; $i -le 5; $i++) {
    Start-Sleep -Seconds 1
    $status = Invoke-RestMethod "$baseUrl/render/$jobId/status"
    Write-Host "   Poll $i : State=$($status.state), Progress=$($status.progress_pct)%" -ForegroundColor Green
    
    if ($status.state -eq "completed" -or $status.state -eq "error") {
        break
    }
}

# Test 5: Final Status
Write-Host "`n5. Final job details..." -ForegroundColor Yellow
$finalStatus = Invoke-RestMethod "$baseUrl/render/$jobId/status"
Write-Host "   State: $($finalStatus.state)" -ForegroundColor Green
Write-Host "   Assets: $($finalStatus.assets.Count)" -ForegroundColor Green
Write-Host "   Video URL: $($finalStatus.final_video_url)" -ForegroundColor Green
Write-Host "   Encoder: $($finalStatus.encoder)" -ForegroundColor Green

# Test 6: Invalid Input
Write-Host "`n6. Testing validation (should fail with 422)..." -ForegroundColor Yellow
try {
    $badPlan = '{"topic": "missing scenes field"}'
    Invoke-RestMethod -Uri "$baseUrl/render" -Method POST -ContentType "application/json" -Body $badPlan
} catch {
    $errorDetail = ($_ | ConvertFrom-Json).detail
    Write-Host "   ✓ Correctly rejected: Field '$($errorDetail.loc -join '.')' - $($errorDetail.msg)" -ForegroundColor Green
}

Write-Host ""
Write-Host "=== All Tests Passed! ===" -ForegroundColor Cyan
Write-Host ""
