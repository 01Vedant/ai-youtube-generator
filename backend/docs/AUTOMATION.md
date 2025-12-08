# Automation & Testing Guide

This guide covers all automation workflows for testing and verifying the DevotionalAI Frontend locally.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Frontend API Smoke Test](#frontend-api-smoke-test)
3. [Headless Browser Test](#headless-browser-test)
4. [Placeholder Mode Toggle](#placeholder-mode-toggle)
5. [Development Startup Script](#development-startup-script)
6. [CI/CD Integration](#cicd-integration)
7. [Troubleshooting](#troubleshooting)

---

## Quick Start

Get the entire local development environment running with tests in 3 minutes:

### Option A: Using PowerShell Script (Windows)

```powershell
cd platform
.\dev-start.ps1
```

This will:
- ✓ Start Docker Compose (backend, frontend, Redis, workers)
- ✓ Wait for services to be ready
- ✓ Run frontend API smoke test
- ✓ Display summary and access points

### Option B: Using Docker Compose Directly (Any OS)

```bash
cd platform
docker compose up --build
```

Then in another terminal:

```bash
# Run frontend API smoke test
python tests/frontend_smoke_test.py

# Or run with JSON report
python tests/frontend_smoke_test.py --json-report
```

---

## Frontend API Smoke Test

Verifies the complete user workflow **without external APIs**.

### What It Tests

- User registration and authentication
- Create Story API endpoint (`POST /api/v1/projects/create_from_title`)
- Job polling simulation (`GET /api/v1/jobs/{job_id}`)
- Placeholder asset availability (SVG, PNG, MP3)
- Final video download link

### Basic Usage

```bash
# Run with default settings (localhost:8000)
python platform/tests/frontend_smoke_test.py

# Run against different backend
python platform/tests/frontend_smoke_test.py --host http://backend.example.com

# Save JSON report
python platform/tests/frontend_smoke_test.py --json-report

# Save to specific file
python platform/tests/frontend_smoke_test.py --json-report --output custom_report.json
```

### Output

**Console Output** (real-time):
```
============================================================
FRONTEND SMOKE TEST - LOCAL WORKFLOW VERIFICATION
============================================================
Backend: http://localhost:8000
Start time: 2024-12-03T14:32:10.123456

STEP 1: User Registration & Authentication
------------------------------------------------------------
[2024-12-03T14:32:10.234567] Registering user: smoke_test_1234567890@test.local
[2024-12-03T14:32:10.567890] ✓ User registered: user_abc123xyz
[2024-12-03T14:32:11.234567] Logging in: smoke_test_1234567890@test.local
[2024-12-03T14:32:11.567890] ✓ Logged in. Token: eyJhbGciOiJIUzI1NiI...

STEP 2: Create Story Project
------------------------------------------------------------
[2024-12-03T14:32:12.123456] Creating story via /projects/create_from_title
[2024-12-03T14:32:12.567890] ✓ Story created. Job ID: job_def456uvw, Project ID: proj_ghi789
...

STEP 5: Verify Final Video Download Link
------------------------------------------------------------
[2024-12-03T14:32:35.123456] Checking final video availability
[2024-12-03T14:32:35.567890] ✓ Final video URL available: /storage/.../final_video.mp4

============================================================
✓ TEST SUMMARY
============================================================
Duration: 27.3s
User ID: user_abc123xyz
Project ID: proj_ghi789
Job ID: job_def456uvw
Job Status: completed
Polling Cycles: 10
Final Progress: 100%
Placeholders: ✓ All OK
Final Video: ✓ Available
============================================================
```

**JSON Report** (`smoke_test_report.json`):
```json
{
  "start_time": "2024-12-03T14:32:10.123456",
  "end_time": "2024-12-03T14:32:37.456789",
  "duration_seconds": 27.3,
  "success": true,
  "user_id": "user_abc123xyz",
  "project_id": "proj_ghi789",
  "job_id": "job_def456uvw",
  "token_acquired": true,
  "polling_history": [
    {
      "poll": 1,
      "status": "processing",
      "progress_percent": 10,
      "scenes_count": 3,
      "timestamp": "2024-12-03T14:32:13.123456"
    },
    {
      "poll": 2,
      "status": "processing",
      "progress_percent": 20,
      "scenes_count": 3,
      "timestamp": "2024-12-03T14:32:15.234567"
    }
  ],
  "placeholders": {
    "image_svg": {
      "status": "ok",
      "size": 1234,
      "content_type": "image/svg+xml",
      "url": "http://localhost:8000/static/placeholders/placeholder_4k.svg"
    },
    "audio_mp3": {
      "status": "ok",
      "size": 77,
      "content_type": "audio/mpeg",
      "url": "http://localhost:8000/static/placeholders/placeholder_silent.mp3"
    }
  },
  "placeholders_all_ok": true,
  "final_video_url": "/storage/videos/final_video.mp4"
}
```

### Interpreting Results

| Result | Meaning | Next Steps |
|--------|---------|-----------|
| `success: true` | Full workflow succeeded | Ready for deployment / API key integration |
| `success: false` | One or more steps failed | Check "errors" field; see troubleshooting |
| `placeholders_all_ok: true` | All assets serving correctly | UI will render properly |
| `final_video_url: null` | Video not yet complete | Expected during development; wait for job completion |

---

## Headless Browser Test

Automates browser verification of UI components **without manual clicking**.

### What It Tests

- Dashboard page loads and renders
- Create Story button is clickable
- Modal form appears and accepts input
- JobProgressCard displays during polling
- Placeholder images render (SVG or PNG)
- Audio elements present in ScenePreview
- Layout responsive across mobile, tablet, desktop

### Requirements

```bash
# Install Playwright (one-time setup)
pip install playwright
playwright install
```

### Basic Usage

```bash
# Run in headless mode (no visible browser)
python platform/tests/headless_browser_test.py

# Run with browser window visible (useful for debugging)
python platform/tests/headless_browser_test.py --headed

# Run against different frontend
python platform/tests/headless_browser_test.py --host http://frontend.example.com

# Save JSON report
python platform/tests/headless_browser_test.py --json-report

# All options
python platform/tests/headless_browser_test.py --host http://localhost:3000 --backend http://localhost:8000 --json-report --headed
```

### Output

**Console Output**:
```
============================================================
HEADLESS BROWSER SMOKE TEST - UI COMPONENT VERIFICATION
============================================================
Frontend: http://localhost:3000
Backend: http://localhost:8000
Headless: True

[2024-12-03T14:35:10.123456] [INFO] Launching browser...
[2024-12-03T14:35:12.567890] [INFO] Running: Navigate to Dashboard
[2024-12-03T14:35:13.234567] [SUCCESS] Navigate to Dashboard
  Found progress component: .progress-bar
[2024-12-03T14:35:14.567890] [SUCCESS] Verify JobProgressCard
  Found 5 images on page
  Placeholder image: /static/placeholders/placeholder_4k.svg
[2024-12-03T14:35:15.123456] [SUCCESS] Verify Placeholder Images
  Found 1 audio elements
[2024-12-03T14:35:16.567890] [SUCCESS] Verify Placeholder Audio

============================================================
✓ BROWSER TEST SUMMARY
============================================================
Steps Passed: 8/8
Placeholders Found: 1
============================================================
```

**JSON Report** (`browser_test_report.json`):
```json
{
  "start_time": "2024-12-03T14:35:10.123456",
  "end_time": "2024-12-03T14:35:20.567890",
  "success": true,
  "steps": [
    {
      "name": "Navigate to Dashboard",
      "status": "ok",
      "result": {"url": "http://localhost:3000/"},
      "timestamp": "2024-12-03T14:35:13.234567"
    },
    {
      "name": "Verify Dashboard UI",
      "status": "ok",
      "result": {"dashboard_found": true, "create_story_button_found": true},
      "timestamp": "2024-12-03T14:35:14.123456"
    }
  ],
  "placeholders_found": [
    {
      "src": "/static/placeholders/placeholder_4k.svg",
      "alt": "Scene 1"
    }
  ],
  "errors": []
}
```

---

## Placeholder Mode Toggle

Control whether the frontend uses **placeholder assets or real assets**.

### Use Cases

| Use Case | Mode | Behavior |
|----------|------|----------|
| Local testing (no API keys) | `PLACEHOLDER_MODE=true` | Always show placeholders |
| Development with API keys | `PLACEHOLDER_MODE=false` | Show real assets when available, fallback to placeholders |
| Production | `PLACEHOLDER_MODE=false` | Always show real assets (backend responsible) |
| Demo / Showcase | `PLACEHOLDER_MODE=true` | Consistent placeholder appearance |

### Configuration

**Option A: Environment Variable (Frontend .env.local)**

```bash
# Force placeholder mode
REACT_APP_PLACEHOLDER_MODE=true

# Or use real assets if available
REACT_APP_PLACEHOLDER_MODE=false
```

**Option B: dev-start.ps1 Script**

```powershell
# Start in placeholder mode
.\dev-start.ps1 -Placeholder

# Start in normal mode (real assets if available)
.\dev-start.ps1
```

### Checking Current Mode

In browser console:

```javascript
import api from './src/services/api.js';
api.getCurrentMode();
// Output: { placeholder_mode: true, api_base: "/api/v1", env: "development" }
```

Or check via Network tab:
- With `PLACEHOLDER_MODE=true`: All image requests are `/static/placeholders/placeholder_4k.svg`
- With `PLACEHOLDER_MODE=false`: Image requests vary based on backend response

---

## Development Startup Script

Complete automation for local development setup.

### Features

- Starts Docker Compose (backend, frontend, Redis, workers)
- Waits for services to be healthy
- Automatically runs smoke tests
- Provides clear status and next steps
- Safe cleanup without data loss

### Usage

```powershell
cd platform

# Start with tests (default)
.\dev-start.ps1

# Start in placeholder mode
.\dev-start.ps1 -Placeholder

# Start without tests (just start services)
.\dev-start.ps1 -SkipTests

# Start with headless browser tests
.\dev-start.ps1 -Headless

# Run tests only (if services already running)
.\dev-start.ps1 -Action test

# View logs in real-time
.\dev-start.ps1 -Action logs

# Stop all services
.\dev-start.ps1 -Action stop

# Clean reset (stop + remove volumes + clean artifacts)
.\dev-start.ps1 -Action clean
```

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `-Action` | `start` | Action: start, test, stop, logs, clean |
| `-Backend` | `http://localhost:8000` | Backend API URL |
| `-Frontend` | `http://localhost:3000` | Frontend URL |
| `-Headless` | `false` | Run headless browser tests |
| `-SkipTests` | `false` | Skip smoke tests after start |
| `-Placeholder` | `false` | Force placeholder mode |
| `-WaitSeconds` | `30` | Seconds to wait for services to start |
| `-NoDocker` | `false` | Skip Docker (assume services running) |

### Output Example

```
======================================================================
DevotionalAI Frontend - Local Development Setup
======================================================================
ℹ Checking prerequisites...
✓ Docker found
✓ Python found

======================================================================
Starting DevotionalAI Stack
======================================================================
ℹ Starting Docker Compose...
✓ Docker Compose started
ℹ Waiting for services to be ready...
✓ Backend is ready
✓ Frontend is ready

======================================================================
Running Smoke Tests
======================================================================
ℹ Running Frontend API smoke test...
✓ Frontend API smoke test passed
Report saved to: smoke_test_report.json
  Job ID: job_def456uvw
  Project ID: proj_ghi789
  Duration: 27.3s

======================================================================
🎉 Local Development Environment Ready!
======================================================================

Access points:
  Dashboard:     http://localhost:3000
  API Docs:      http://localhost:8000/docs
  API Health:    http://localhost:8000/api/v1/health

Configuration:
  Placeholder Mode: OFF
  Environment:      development

Next steps:
  1. Open http://localhost:3000 in your browser
  2. Click '✨ Create Story' button
  3. Fill in Title and Description
  4. Watch JobProgressCard with live updates
  5. Download final video when ready

Useful commands:
  Logs:        .\dev-start.ps1 logs
  Stop:        .\dev-start.ps1 stop
  Test again:  .\dev-start.ps1 test
  Clean reset: .\dev-start.ps1 clean

✓ Ready to use! 🚀
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Frontend Smoke Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  frontend-smoke-test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Start backend
        run: |
          cd platform
          docker-compose up -d backend workers
          sleep 10
      
      - name: Run frontend smoke test
        run: |
          pip install requests
          python platform/tests/frontend_smoke_test.py --json-report
      
      - name: Upload test report
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: smoke-test-report
          path: smoke_test_report.json
      
      - name: Check test result
        run: |
          python -c "import json; \
          report = json.load(open('smoke_test_report.json')); \
          exit(0 if report.get('success') else 1)"
```

### GitLab CI Example

```yaml
frontend-smoke-test:
  stage: test
  image: python:3.11
  services:
    - postgres:15
    - redis:7
  script:
    - pip install requests
    - cd platform
    - docker-compose up -d backend workers
    - sleep 10
    - python tests/frontend_smoke_test.py --json-report
  artifacts:
    reports:
      performance: smoke_test_report.json
    paths:
      - smoke_test_report.json
    when: always
  allow_failure: false
```

---

## Frontend Smoke Test CI

This repository includes an automated GitHub Actions workflow that runs the safe frontend smoke tests and related verification steps.

- **Workflow location:** `.github/workflows/frontend-smoke-test.yml`
- **Description:** Runs the safe frontend API smoke tests (`platform/tests/frontend_smoke_test.py`), executes `platform/verify_setup.py` to produce a verification summary, and optionally runs headless browser tests (`platform/tests/headless_browser_test.py`) using Playwright. The workflow is configured to use placeholder mode by default to avoid external API calls.

### Artifacts Generated

- `platform/smoke_test_report.json` — JSON report from the frontend API smoke test
- `platform/browser_test_report.json` — JSON report from the headless browser test (if run)
- `platform/verify_setup_output.txt` — Plain-text verification output from `verify_setup.py`
- `platform/ci-logs/*` — Docker/service logs collected during the CI run (backend, frontend, workers)

### How to view CI status

- See the **CI / Frontend Smoke Test** badge at the top of `platform/README.md`. Replace the placeholder `OWNER/REPO` in the badge URL with your GitHub owner and repository name to render the badge correctly.

### Instructions

1. Push your changes to a branch on GitHub (e.g., `main` or open a pull request). The workflow will run automatically.
2. Open the GitHub Actions tab for the repository, select the latest **Frontend Smoke Tests (Safe)** run, and inspect the job logs.
3. In the Actions run page, under "Artifacts", download the `frontend-smoke-test-artifacts` bundle to review:
  - `smoke_test_report.json`
  - `browser_test_report.json` (may be absent if headless tests were skipped)
  - `verify_setup_output.txt`
  - `ci-logs/*`

### Notes

- The workflow forces placeholder mode by default (`REACT_APP_PLACEHOLDER_MODE=true`) to ensure no external AI APIs are invoked during CI runs. If you need to run with real APIs in CI, update the workflow to supply secure secrets and remove the placeholder environment variable.
- The badge in `platform/README.md` uses a placeholder `OWNER/REPO`. Replace this with your repository path (for example, `myorg/ai-youtube-generator`) to display the CI status badge correctly.


---

## Troubleshooting

### Frontend API Smoke Test Issues

#### "Connection refused" to backend

**Symptom:**
```
ERROR: API call failed: POST /api/v1/auth/register - Connection refused
```

**Solutions:**
1. Verify backend is running: `docker ps | grep backend`
2. Check backend logs: `docker compose logs backend`
3. Wait longer for startup: `python tests/frontend_smoke_test.py --host http://localhost:8000` (wait 30s first)
4. Try explicit wait: Add 30s delay before running test

#### "User registration failed" with 422/validation error

**Symptom:**
```
✗ Registration failed: HTTP 422 Unprocessable Entity
```

**Solutions:**
1. Check backend validation rules in `platform/backend/app/schemas.py`
2. Ensure request body matches expected schema
3. Check for duplicate email (test uses timestamp, should be unique)
4. Verify database is initialized: `docker compose exec backend python -m alembic upgrade head`

#### "Job never completes" (polling timeout)

**Symptom:**
```
Poll 10: status=processing, progress=50%, scenes=3
✗ Job status never reached completed
```

**Solutions:**
1. Increase max polls: `python tests/frontend_smoke_test.py --max-polls 20`
2. Check worker logs: `docker compose logs celery`
3. Verify all workers are running: `docker compose ps` (should see celery, celery-beat)
4. Check Redis connection: `docker compose exec redis redis-cli ping` (should return PONG)

#### "Placeholders not found" (404 errors)

**Symptom:**
```
✗ image_svg: /static/placeholders/placeholder_4k.svg - HTTP 404 Not Found
```

**Solutions:**
1. Verify placeholder files exist: `ls -la platform/frontend/public/static/placeholders/`
2. Check frontend logs: `docker compose logs frontend`
3. Clear browser cache and rebuild: `docker compose up --build frontend`
4. Manually verify URLs: `curl http://localhost:8000/static/placeholders/placeholder_4k.svg`

### Headless Browser Test Issues

#### "Playwright not installed"

**Symptom:**
```
ERROR: playwright not installed. Install with: pip install playwright
```

**Solution:**
```bash
pip install playwright
playwright install
```

#### "Browser failed to launch"

**Symptom:**
```
ERROR: Browser launch failed - No such file or directory
```

**Solution:**
```bash
# Re-install browser binaries
playwright install --with-deps
```

#### "Frontend not loading / 404 on first navigation"

**Symptom:**
```
ERROR: Navigation failed - HTTP 404
```

**Solution:**
1. Verify frontend is running: `docker ps | grep frontend`
2. Check frontend logs: `docker compose logs frontend`
3. Wait for frontend to build: Give it 60s on first run
4. Try manual access first: Visit `http://localhost:3000` in browser

#### "Modal not appearing" or "Form fields not found"

**Symptom:**
```
✗ Verify Modal Appears - Modal or form fields not found after 5s
```

**Solution:**
1. Add `--headed` flag to see browser during test: `python tests/headless_browser_test.py --headed`
2. Check if Create Story button exists but modal trigger broken
3. Verify modal CSS/JavaScript loaded: Open DevTools in headed mode
4. Increase wait timeout in test

### Docker Compose Issues

#### Services won't start

**Symptom:**
```
Error response from daemon: driver failed programming external connectivity on endpoint...
```

**Solutions:**
1. Stop all containers: `docker compose down -v`
2. Remove unused volumes: `docker volume prune`
3. Restart Docker daemon
4. Try again: `docker compose up --build`

#### Port conflicts

**Symptom:**
```
listen tcp 0.0.0.0:8000: bind: address already in use
```

**Solutions:**
1. Find what's using port: `netstat -ano | findstr :8000` (Windows) or `lsof -i :8000` (Mac/Linux)
2. Kill process or use different ports: `docker compose up -e API_PORT=8001`
3. Or stop conflicting service manually

#### Out of disk space

**Symptom:**
```
No space left on device
```

**Solution:**
```bash
# Clean up Docker resources
docker system prune -a
docker volume prune
```

---

## Next Steps

- **Deploy to Render:** See `platform/docs/DEPLOYMENT_GUIDE.md`
- **Add API Keys:** Configure OpenAI, ElevenLabs, Replicate keys for production quality
- **Performance Testing:** Add load testing with Apache Bench or Locust
- **Security Testing:** Add OWASP scanning and penetration testing
- **Analytics:** Integrate monitoring and usage tracking
