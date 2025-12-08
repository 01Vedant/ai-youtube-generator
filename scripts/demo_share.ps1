<#
Create a public share link for the last demo job and copy full URL.
Usage:
  ./scripts/demo_share.ps1 -BaseUrl http://127.0.0.1:8000 -FrontendUrl http://localhost:5173
#>
param(
  [string]$BaseUrl = "http://127.0.0.1:8000",
  [string]$FrontendUrl = "http://localhost:5173"
)
$ErrorActionPreference = 'Stop'

function ReadLastJob() {
  $path = Join-Path $PSScriptRoot "..\platform\demo\last_job.txt"
  if (-not (Test-Path $path)) { throw "No last_job.txt found. Run demo_submit.ps1 first." }
  return Get-Content -Path $path -Raw
}

try {
  Write-Host "== Read last job ==" -ForegroundColor Cyan
  $jobId = ReadLastJob
  if (-not $jobId) { throw "Empty last_job.txt" }

  Write-Host "== Create share ==" -ForegroundColor Cyan
  # Create a temporary token for simplicity (public share API may require auth depending on setup)
  $email = "demo@local.test"; $password = "demo123!"
  $tokens = Invoke-RestMethod -Uri "$BaseUrl/auth/login" -Method POST -ContentType "application/json" -Body (ConvertTo-Json @{ email=$email; password=$password })
  $access = $tokens.access_token
  if (-not $access) { throw "No access token returned" }
  $headers = @{ Authorization = "Bearer $access"; "Content-Type" = "application/json" }

  $resp = Invoke-RestMethod -Uri "$BaseUrl/shares" -Method POST -Headers $headers -Body (ConvertTo-Json @{ job_id = $jobId })
  $shareId = $resp.share_id
  if (-not $shareId) { throw "No share_id returned" }
  $url = "$FrontendUrl/s/$shareId"

  try {
    Set-Clipboard -Value $url
    Write-Host "Public link copied: $url" -ForegroundColor Green
  } catch {
    Write-Host "Public link: $url" -ForegroundColor Green
  }

} catch {
  Write-Error $_.Exception.Message
  exit 1
}

exit 0
