#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Verify all code quality checks (FE + BE)
.DESCRIPTION
    Runs TypeScript type checking, ESLint, and Python tests
    Returns green PASS or red FAIL summary
#>

$ErrorActionPreference = "Continue"
$script:failures = @()

function Test-Step {
    param(
        [string]$Name,
        [scriptblock]$Command
    )
    
    Write-Host "`n▶ $Name..." -ForegroundColor Cyan
    
    try {
        & $Command
        if ($LASTEXITCODE -ne 0) {
            $script:failures += $Name
            Write-Host "  ✗ FAILED" -ForegroundColor Red
            return $false
        }
        Write-Host "  ✓ PASSED" -ForegroundColor Green
        return $true
    }
    catch {
        $script:failures += $Name
        Write-Host "  ✗ ERROR: $_" -ForegroundColor Red
        return $false
    }
}

Write-Host "═══════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  BHAKTI VIDEO GENERATOR - VERIFY ALL" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════" -ForegroundColor Yellow

# Frontend checks
Push-Location platform/frontend

Test-Step "Frontend TypeScript Check" {
    npm run typecheck 2>&1 | Out-Null
}

Test-Step "Frontend ESLint" {
    npm run lint 2>&1 | Out-Null
}

Pop-Location

# Backend checks
Push-Location platform/backend

Test-Step "Backend Python Tests" {
    pytest -q 2>&1 | Out-Null
}

Pop-Location

# Summary
Write-Host "`n═══════════════════════════════════════" -ForegroundColor Yellow
if ($script:failures.Count -eq 0) {
    Write-Host "  ✓ ALL CHECKS PASSED" -ForegroundColor Green
    Write-Host "═══════════════════════════════════════" -ForegroundColor Yellow
    exit 0
}
else {
    Write-Host "  ✗ FAILURES: $($script:failures.Count)" -ForegroundColor Red
    Write-Host "═══════════════════════════════════════" -ForegroundColor Yellow
    foreach ($fail in $script:failures) {
        Write-Host "    - $fail" -ForegroundColor Red
    }
    exit 1
}
