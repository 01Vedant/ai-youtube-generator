# Public Demo Runbook

## Prereqs
- Windows + PowerShell (5.1+)
- Docker Desktop
- Python 3.12
- Optional: Node 20 for frontend

## Start Stack
```powershell
./dev-up.ps1
```

## Health Check
- Open `http://localhost:8000/docs`
- `GET http://localhost:8000/health/ready` should return 200
- MinIO console: `http://localhost:9001` (minioadmin / minioadmin)

## Create Demo User + Login
PowerShell:
```powershell
$base = "http://127.0.0.1:8000"; $email = "demo@local.test"; $password = "demo123!"
try { Invoke-RestMethod -Uri "$base/auth/login" -Method POST -ContentType "application/json" -Body (ConvertTo-Json @{ email=$email; password=$password }) | Set-Variable tokens } catch { $tokens = $null }
if (-not $tokens) { Invoke-RestMethod -Uri "$base/auth/register" -Method POST -ContentType "application/json" -Body (ConvertTo-Json @{ email=$email; password=$password }) | Out-Null; $tokens = Invoke-RestMethod -Uri "$base/auth/login" -Method POST -ContentType "application/json" -Body (ConvertTo-Json @{ email=$email; password=$password }) }
$ACCESS_TOKEN = $tokens.access_token
Write-Host "ACCESS_TOKEN=$ACCESS_TOKEN"
```

## Submit Demo Render
```powershell
./scripts/demo_submit.ps1 -Email demo@local.test -Password demo123! -BaseUrl http://127.0.0.1:8000
```

## Run Worker (if not auto-started via compose)
```powershell
docker compose -f docker-compose.dev.yml logs -f worker
```

## Track Job
- API docs: `http://localhost:8000/docs` → try `GET /render/{job_id}/status`
- Frontend: open Render Status page if available

## Share & Export
- Create share link → open `/s/{shareId}`
- Trigger mock YouTube export → open returned URL

## Cleanup
```powershell
./dev-down.ps1
```

## Troubleshooting
- 429 QUOTA: log in as Pro or reset usage row in SQLite.
- S3 URL errors: ensure `docker compose up` — bucket bootstrap runs at API start.
- PowerShell policy: `Set-ExecutionPolicy -Scope Process Bypass -Force`.
