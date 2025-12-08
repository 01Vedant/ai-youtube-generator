# test_cors.ps1 - Quick CORS connectivity test

Write-Host "CORS Connectivity Test" -ForegroundColor Cyan
Write-Host "======================" -ForegroundColor Cyan
Write-Host ""

$backend = "http://127.0.0.1:8000"

Write-Host "Test 1: Backend Health Check" -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "$backend/healthz" -Method GET -TimeoutSec 5
    Write-Host "  Status: OK" -ForegroundColor Green
    Write-Host "  Response: $($health | ConvertTo-Json -Compress)" -ForegroundColor Gray
} catch {
    Write-Host "  Status: FAILED" -ForegroundColor Red
    Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
Write-Host ""

Write-Host "Test 2: CORS Configuration" -ForegroundColor Yellow
try {
    $cors = Invoke-RestMethod -Uri "$backend/debug/cors" -Method GET -TimeoutSec 5
    Write-Host "  Allowed Origins: $($cors.origins -join ', ')" -ForegroundColor Green
    Write-Host "  Allow Credentials: $($cors.allow_credentials)" -ForegroundColor Green
    
    $expectedOrigins = @("http://localhost:5173", "http://127.0.0.1:5173")
    $hasCorrectOrigins = $expectedOrigins | ForEach-Object { $cors.origins -contains $_ } | Where-Object { $_ -eq $false } | Measure-Object | Select-Object -ExpandProperty Count
    
    if ($hasCorrectOrigins -eq 0 -and $cors.allow_credentials -eq $true) {
        Write-Host "  Validation: PASSED" -ForegroundColor Green
    } else {
        Write-Host "  Validation: FAILED (missing expected origins or credentials not enabled)" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "  Status: FAILED" -ForegroundColor Red
    Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
Write-Host ""

Write-Host "Test 3: Create Mock Job (Render Endpoint)" -ForegroundColor Yellow
$payload = @{
    topic = "CORS Test"
    language = "en"
    voice = "F"
    scenes = @(
        @{
            image_prompt = "Beautiful temple"
            narration = "Testing CORS connectivity"
            duration_sec = 3
        }
    )
} | ConvertTo-Json -Depth 10

try {
    $result = Invoke-RestMethod -Uri "$backend/render" `
        -Method POST `
        -ContentType "application/json" `
        -Body $payload `
        -TimeoutSec 10
    
    $jobId = $result.job_id
    Write-Host "  Job Created: $jobId" -ForegroundColor Green
    
    # Test status polling
    Write-Host ""
    Write-Host "Test 4: Status Polling" -ForegroundColor Yellow
    $status = Invoke-RestMethod -Uri "$backend/render/$jobId/status" `
        -Method GET `
        -TimeoutSec 10
    
    Write-Host "  Job State: $($status.state)" -ForegroundColor Green
    Write-Host "  Progress: $($status.progress_pct)%" -ForegroundColor Green
    
} catch {
    Write-Host "  Status: FAILED" -ForegroundColor Red
    Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
Write-Host ""

Write-Host "======================" -ForegroundColor Cyan
Write-Host "All Tests PASSED" -ForegroundColor Green
Write-Host ""
