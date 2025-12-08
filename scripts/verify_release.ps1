<#
  Verify Release Script (Windows PowerShell 5.1+)
  Runs backend tests, optional API health, frontend typecheck/lint, optional e2e and docker sanity.
  Fail-fast for backend pytest failures; prints a summary at the end.
#>

$ErrorActionPreference = 'Stop'

function Section($title) {
  Write-Host "`n==== $title ====" -ForegroundColor Cyan
}

function TryStep($label, [ScriptBlock]$action) {
  try {
    & $action
    return @{ label = $label; ok = $true; msg = 'OK' }
  } catch {
    Write-Host "[$label] Failed: $($_.Exception.Message)" -ForegroundColor Red
    return @{ label = $label; ok = $false; msg = $_.Exception.Message }
  }
}

$results = @()
$backendOk = $true

# 1) Backend quick tests
Section 'Backend: Pytest'
$results += TryStep 'backend-pytest' {
  Push-Location "platform/backend"
  try {
    $env:PYTHONPATH = $PWD
    python -m pytest -q
  } finally {
    Pop-Location
  }
}
if (-not ($results[-1].ok)) { $backendOk = $false }

# 2) Health endpoints (optional)
Section 'API Health (optional)'
$results += TryStep 'api-health' {
  try {
    $resp = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health/live" -Method GET -TimeoutSec 5
    Write-Host "API live: $($resp.status)" -ForegroundColor Green
  } catch {
    Write-Host 'API not running – skipped' -ForegroundColor Yellow
    throw $_
  }
}

# 3) Frontend typecheck/lint (if Node present)
Section 'Frontend: Typecheck & Lint'
$results += TryStep 'frontend-typecheck-lint' {
  Push-Location "platform/frontend"
  try {
    $npm = Get-Command npm -ErrorAction SilentlyContinue
    if (-not $npm) {
      Write-Host 'Node/npm not installed – skipped' -ForegroundColor Yellow
      return
    }
    npm run typecheck
    npm run lint
  } finally { Pop-Location }
}

# 4) Playwright e2e (optional)
Section 'E2E: Playwright (optional)'
$results += TryStep 'e2e-playwright' {
  Push-Location "platform/frontend"
  try {
    $npx = Get-Command npx -ErrorAction SilentlyContinue
    if (-not $npx) {
      Write-Host 'npx not available – skipped' -ForegroundColor Yellow
      return
    }
    try { npx playwright install --with-deps } catch { Write-Host 'Playwright install skipped/failed' -ForegroundColor Yellow }
    npm run e2e
  } finally { Pop-Location }
}

# 5) Docker dev sanity (optional)
Section 'Docker Compose (optional)'
$results += TryStep 'docker-compose-config' {
  $docker = Get-Command docker -ErrorAction SilentlyContinue
  if (-not $docker) {
    Write-Host 'Docker not installed – skipped' -ForegroundColor Yellow
    return
  }
  docker compose -f docker-compose.dev.yml config | Out-Null
}

# 6) Summary
Section 'Summary'
foreach ($r in $results) {
  $mark = if ($r.ok) { '✅' } else { '⚠️' }
  Write-Host ("{0} {1}: {2}" -f $mark, $r.label, $r.msg)
}

if (-not $backendOk) {
  Write-Host "Backend pytest failed – exiting with nonzero code." -ForegroundColor Red
  exit 1
}

Write-Host "All critical checks passed or were skipped where optional." -ForegroundColor Green
exit 0
