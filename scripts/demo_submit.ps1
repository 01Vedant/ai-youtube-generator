<#
Logs in (or registers) and submits the bundled demo plan.
Usage:
  ./scripts/demo_submit.ps1 -Email demo@local.test -Password demo123! -BaseUrl http://127.0.0.1:8000
#>
param(
  [string]$Email = "demo@local.test",
  [SecureString]$Password,
  [string]$BaseUrl = "http://127.0.0.1:8000"
)

# Convert default password if not provided
function Json($obj) { return ($obj | ConvertTo-Json -Depth 6) }

try {
  # Convert SecureString to plain text for API calls
  $plainPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto([System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($Password))
  
  Write-Host "== Auth: login/register ==" -ForegroundColor Cyan
  $tokens = $null
  try {
    $tokens = Invoke-RestMethod -Uri "$BaseUrl/auth/login" -Method POST -ContentType "application/json" -Body (Json @{ email=$Email; password=$plainPassword })
  } catch {
    Write-Host "Login failed, attempting register…" -ForegroundColor Yellow
    Invoke-RestMethod -Uri "$BaseUrl/auth/register" -Method POST -ContentType "application/json" -Body (Json @{ email=$Email; password=$plainPassword }) | Out-Null
    $tokens = Invoke-RestMethod -Uri "$BaseUrl/auth/login" -Method POST -ContentType "application/json" -Body (Json @{ email=$Email; password=$plainPassword })
  }
  $access = $tokens.access_token
  if (-not $access) { throw "No access token returned" }

  Write-Host "== Read demo plan ==" -ForegroundColor Cyan
  $planPath = Join-Path $PSScriptRoot "..\platform\demo\demo_plan.json"
  if (-not (Test-Path $planPath)) { throw "Missing demo_plan.json at $planPath" }
  $planRaw = Get-Content -Path $planPath -Raw

  Write-Host "== Submit render ==" -ForegroundColor Cyan
  $headers = @{ Authorization = "Bearer $access"; "Content-Type" = "application/json" }
  $resp = Invoke-RestMethod -Uri "$BaseUrl/render" -Method POST -Headers $headers -Body $planRaw
  $jobId = $resp.job_id
  if (-not $jobId) { throw "No job_id returned" }
  Write-Host "job_id: $jobId" -ForegroundColor Green

  $outDir = Join-Path $PSScriptRoot "..\platform\demo"
  if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir | Out-Null }
  $lastPath = Join-Path $outDir "last_job.txt"
  Set-Content -Path $lastPath -Value $jobId

  Write-Host "== Open Render Status (if frontend running) ==" -ForegroundColor Cyan
  $statusUrl = "http://localhost:5173/render/$jobId"
  try { Start-Process $statusUrl | Out-Null } catch { Write-Host "Could not open browser (non-fatal)" -ForegroundColor Yellow }

} catch {
  Write-Error $_.Exception.Message
  exit 1
}

Write-Host "Demo job submitted successfully." -ForegroundColor Green
exit 0
