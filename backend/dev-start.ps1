# DevotionalAI Frontend - Local Development Startup Script
# This script starts Docker Compose, runs smoke tests, and displays results
# Usage: .\dev-start.ps1

param(
    [string]$Action = "start",          # start, test, stop, logs, clean
    [string]$Backend = "http://localhost:8000",
    [string]$Frontend = "http://localhost:3000",
    [switch]$Headless = $false,          # Run headless browser tests
    [switch]$SkipTests = $false,         # Skip smoke tests after start
    [switch]$Placeholder = $false,       # Force placeholder mode
    [int]$WaitSeconds = 30,              # Seconds to wait for services to be ready
    [switch]$NoDocker = $false           # Skip Docker (assume services already running)
)

function Write-Header {
    param([string]$Text)
    Write-Host ""
    Write-Host "=" * 70 -ForegroundColor Cyan
    Write-Host $Text -ForegroundColor Cyan
    Write-Host "=" * 70 -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Text)
    Write-Host "✓ $Text" -ForegroundColor Green
}

function Write-ErrorMessage {
    param([string]$Text)
    Write-Host "✗ $Text" -ForegroundColor Red
}

function Write-Info {
    param([string]$Text)
    Write-Host "ℹ $Text" -ForegroundColor Yellow
}

function Test-Command {
    param([string]$Cmd)
    $exists = $null -ne (Get-Command $Cmd -ErrorAction SilentlyContinue)
    return $exists
}

function Wait-For-Service {
    param(
        [string]$Url,
        [int]$MaxWait = 30,
        [string]$ServiceName = "Service"
    )
    
    $elapsed = 0
    $interval = 2
    
    Write-Info "$ServiceName starting... waiting for $Url"
    
    while ($elapsed -lt $MaxWait) {
        try {
            $response = Invoke-WebRequest -Uri $Url -TimeoutSec 2 -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) {
                Write-Success "$ServiceName is ready"
                return $true
            }
        } catch {
            # Service not ready yet
        }
        
        Start-Sleep -Seconds $interval
        $elapsed += $interval
        Write-Host "  waiting... ($elapsed/$MaxWait seconds)" -ForegroundColor Gray
    }
    
    Write-ErrorMessage "$ServiceName did not start within $MaxWait seconds"
    return $false
}

# ============================================================================
# MAIN SCRIPT
# ============================================================================

Write-Header "DevotionalAI Frontend - Local Development Setup"

# Validate prerequisites
Write-Info "Checking prerequisites..."

if (-not $NoDocker) {
    if (-not (Test-Command "docker")) {
        Write-ErrorMessage "Docker not found. Please install Docker Desktop."
        exit 1
    }
    Write-Success "Docker found"
}

if (-not (Test-Command "python")) {
    Write-ErrorMessage "Python not found. Please install Python 3.8+"
    exit 1
}
Write-Success "Python found"

# ============================================================================
# ACTION: START
# ============================================================================

if ($Action -eq "start" -or $Action -eq "") {
    Write-Header "Starting DevotionalAI Stack"
    
    if (-not $NoDocker) {
        Write-Info "Starting Docker Compose..."
        Push-Location "platform"
        
        try {
            # Build and start services
            Write-Host "Running: docker compose up --build -d" -ForegroundColor Gray
            & docker compose up --build -d 2>&1 | Out-String | Write-Host
            
            if ($LASTEXITCODE -ne 0) {
                Write-ErrorMessage "Docker Compose failed to start"
                exit 1
            }
            
            Write-Success "Docker Compose started"
        } finally {
            Pop-Location
        }
        
        # Wait for services
        Write-Info "Waiting for services to be ready..."
        
        if (-not (Wait-For-Service "$Backend/api/v1/status" $WaitSeconds "Backend")) {
            Write-ErrorMessage "Backend failed to start"
            Write-Host "Check logs with: docker compose logs backend"
            exit 1
        }
        
        if (-not (Wait-For-Service "$Frontend/" $WaitSeconds "Frontend")) {
            Write-ErrorMessage "Frontend failed to start"
            Write-Host "Check logs with: docker compose logs frontend"
            exit 1
        }
    }
    
    Write-Success "All services ready"
    
    # ========================================================================
    # RUN SMOKE TESTS (unless skipped)
    # ========================================================================
    
    if (-not $SkipTests) {
        Write-Header "Running Smoke Tests"
        
        # Set environment variables
        $env:REACT_APP_PLACEHOLDER_MODE = if ($Placeholder) { "true" } else { "false" }
        $env:REACT_APP_API_BASE = "/api/v1"
        
        # Frontend API smoke test
        Write-Info "Running Frontend API smoke test..."
        Write-Host "Command: python platform/tests/frontend_smoke_test.py --host $Backend --json-report" -ForegroundColor Gray
        
        & python platform/tests/frontend_smoke_test.py --host $Backend --json-report
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Frontend API smoke test passed"
            
            if (Test-Path "smoke_test_report.json") {
                Write-Host ""
                Write-Host "Report saved to: smoke_test_report.json" -ForegroundColor Cyan
                $report = Get-Content "smoke_test_report.json" | ConvertFrom-Json
                Write-Host "  Job ID: $($report.job_id)" -ForegroundColor Gray
                Write-Host "  Project ID: $($report.project_id)" -ForegroundColor Gray
                Write-Host "  Duration: $($report.duration_seconds)s" -ForegroundColor Gray
            }
        } else {
            Write-ErrorMessage "Frontend API smoke test failed"
        }
        
        # Optional: Headless browser test
        if ($Headless) {
            Write-Info ""
            Write-Info "Running headless browser test (experimental)..."
            
            # Check for playwright
            try {
                & python -m pip show playwright | Out-Null
                if ($LASTEXITCODE -ne 0) {
                    Write-Info "Installing Playwright (one-time setup)..."
                    & python -m pip install playwright --quiet
                    & python -m playwright install --quiet
                }
                
                Write-Host "Command: python platform/tests/headless_browser_test.py --host $Frontend --backend $Backend --json-report" -ForegroundColor Gray
                & python platform/tests/headless_browser_test.py --host $Frontend --backend $Backend --json-report
                
                if ($LASTEXITCODE -eq 0) {
                    Write-Success "Headless browser test passed"
                } else {
                    Write-ErrorMessage "Headless browser test failed (non-critical)"
                }
            } catch {
                Write-Info "Playwright not available (skipping headless tests)"
            }
        }
    }
    
    # ========================================================================
    # SUCCESS OUTPUT
    # ========================================================================
    
    Write-Header "🎉 Local Development Environment Ready!"
    
    Write-Host ""
    Write-Host "Access points:" -ForegroundColor Cyan
    Write-Host "  Dashboard:     $Frontend" -ForegroundColor Gray
    Write-Host "  API Docs:      $Backend/docs" -ForegroundColor Gray
    Write-Host "  API Health:    $Backend/api/v1/health" -ForegroundColor Gray
    
    Write-Host ""
    Write-Host "Configuration:" -ForegroundColor Cyan
    Write-Host "  Placeholder Mode: $(if ($Placeholder) { 'ON' } else { 'OFF' })" -ForegroundColor Gray
    Write-Host "  Environment:      development" -ForegroundColor Gray
    
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Open $Frontend in your browser" -ForegroundColor Gray
    Write-Host "  2. Click '✨ Create Story' button" -ForegroundColor Gray
    Write-Host "  3. Fill in Title and Description" -ForegroundColor Gray
    Write-Host "  4. Watch JobProgressCard with live updates" -ForegroundColor Gray
    Write-Host "  5. Download final video when ready" -ForegroundColor Gray
    
    Write-Host ""
    Write-Host "Useful commands:" -ForegroundColor Cyan
    Write-Host "  Logs:        .\dev-start.ps1 logs" -ForegroundColor Gray
    Write-Host "  Stop:        .\dev-start.ps1 stop" -ForegroundColor Gray
    Write-Host "  Test again:  .\dev-start.ps1 test" -ForegroundColor Gray
    Write-Host "  Clean reset: .\dev-start.ps1 clean" -ForegroundColor Gray
    
    Write-Host ""
    Write-Success "Ready to use! 🚀"
    Write-Host ""
}

# ============================================================================
# ACTION: TEST
# ============================================================================

elseif ($Action -eq "test") {
    Write-Header "Running Smoke Tests"
    
    $env:REACT_APP_PLACEHOLDER_MODE = if ($Placeholder) { "true" } else { "false" }
    $env:REACT_APP_API_BASE = "/api/v1"
    
    & python platform/tests/frontend_smoke_test.py --host $Backend --json-report
    
    if ($Headless) {
        Write-Host ""
        & python platform/tests/headless_browser_test.py --host $Frontend --backend $Backend --json-report
    }
}

# ============================================================================
# ACTION: STOP
# ============================================================================

elseif ($Action -eq "stop") {
    if (-not $NoDocker) {
        Write-Header "Stopping DevotionalAI Stack"
        Push-Location "platform"
        try {
            & docker compose down
            Write-Success "Services stopped"
        } finally {
            Pop-Location
        }
    }
}

# ============================================================================
# ACTION: LOGS
# ============================================================================

elseif ($Action -eq "logs") {
    if (-not $NoDocker) {
        Write-Header "Docker Compose Logs"
        Push-Location "platform"
        try {
            & docker compose logs -f
        } finally {
            Pop-Location
        }
    }
}

# ============================================================================
# ACTION: CLEAN
# ============================================================================

elseif ($Action -eq "clean") {
    Write-Header "Cleaning Up"
    
    if (-not $NoDocker) {
        Push-Location "platform"
        try {
            Write-Host "Stopping services..." -ForegroundColor Yellow
            & docker compose down -v
            Write-Success "Services and volumes removed"
        } finally {
            Pop-Location
        }
    }
    
    # Remove test artifacts
    $artifacts = @(
        "smoke_test_report.json",
        "browser_test_report.json"
    )
    
    foreach ($artifact in $artifacts) {
        if (Test-Path $artifact) {
            Remove-Item $artifact -Force
            Write-Success "Removed $artifact"
        }
    }
}

else {
    Write-ErrorMessage "Unknown action: $Action"
    Write-Host "Valid actions: start, test, stop, logs, clean" -ForegroundColor Gray
    exit 1
}

Write-Host ""
