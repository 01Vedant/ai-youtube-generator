# Frontend Smoke Test Guide

This guide walks you through running a safe, local frontend smoke test that verifies the full job lifecycle without external APIs.

## What the Frontend Smoke Test Verifies

✅ User registration and authentication (JWT token acquisition)
✅ Create Story API endpoint (`POST /api/v1/projects/create_from_title`)
✅ Job polling and status updates (simulates `JobProgressCard` polling)
✅ Scene data and placeholder asset availability
✅ Placeholder image and audio rendering (SVG, PNG, MP3)
✅ Job completion and final video download link availability
✅ No external API calls (OpenAI, ElevenLabs, Replicate, Runway)

## Prerequisites

1. **Docker Compose running locally:**
   ```powershell
   cd platform
   docker compose up --build
   ```
   Wait for services to be ready:
   - Backend API: `http://localhost:8000`
   - Frontend: `http://localhost:3000`
   - PostgreSQL, Redis, Celery workers running

2. **Backend environment variables:**
   ```
   USE_S3=false
   OPENAI_API_KEY=  (can be empty)
   ELEVENLABS_API_KEY=  (can be empty)
   ```
   The smoke test does NOT call these APIs.

3. **Python 3.8+ with requests library:**
   ```powershell
   pip install requests
   ```

## Running the Frontend Smoke Test

### Quick Start

From the repository root:

```powershell
python platform/tests/frontend_smoke_test.py
```

Expected output:
```
[2025-12-03T...] ============================================================
[2025-12-03T...] FRONTEND SMOKE TEST - LOCAL WORKFLOW VERIFICATION
[2025-12-03T...] ============================================================
[2025-12-03T...] Backend: http://localhost:8000
[2025-12-03T...] Registering user: smoke_test_1234567890@test.local
[2025-12-03T...] ✓ User registered: user_12345
[2025-12-03T...] Logging in: smoke_test_1234567890@test.local
[2025-12-03T...] ✓ Logged in. Token: eyJhbGciOiJIUzI1NiIsInR5cCI...
[2025-12-03T...] Creating story via /projects/create_from_title
[2025-12-03T...] ✓ Story created. Job ID: job_abc123, Project ID: proj_xyz789
[2025-12-03T...] Polling job status every 2s (max 10 polls)
[2025-12-03T...] Poll 1: status=queued, progress=10%, scenes=0
[2025-12-03T...] Poll 2: status=processing, progress=30%, scenes=3
[2025-12-03T...] Poll 3: status=completed, progress=100%, scenes=3
[2025-12-03T...] ✓ Job completed after 3 polls
[2025-12-03T...] Verifying placeholder assets
[2025-12-03T...] ✓ image_svg: /static/placeholders/placeholder_4k.svg (2048 bytes)
[2025-12-03T...] ✓ image_png: /static/placeholders/placeholder_4k.png (1024 bytes)
[2025-12-03T...] ✓ audio_mp3: /static/placeholders/placeholder_silent.mp3 (77 bytes)
[2025-12-03T...] Checking final video availability
[2025-12-03T...] ✓ Final video URL available: /storage/projects/proj_xyz789/final_video.mp4
[2025-12-03T...] ============================================================
[2025-12-03T...] SMOKE TEST COMPLETE
[2025-12-03T...] ============================================================
```

### Advanced Options

**Custom backend host:**
```powershell
python platform/tests/frontend_smoke_test.py --host http://your-backend:8000
```

**JSON report output:**
```powershell
python platform/tests/frontend_smoke_test.py --json-report
```

Output includes:
- `user_id`: Test user created
- `job_id`: Job ID from Create Story API
- `project_id`: Project ID from Create Story API
- `polling_history`: Each poll's status, progress, scenes count
- `placeholders`: Verification of placeholder assets (SVG, PNG, MP3)
- `final_video_url`: Download link if available
- `success`: True if all steps passed

**Save report to file:**
```powershell
python platform/tests/frontend_smoke_test.py --json-report > smoke_test_report.json
```

## What Happens During the Test

1. **User Registration** → Creates a new test user with unique email
2. **Login** → Acquires JWT token for subsequent API calls
3. **Create Story** → Calls `POST /api/v1/projects/create_from_title` with test payload
   - Returns `job_id` and `project_id`
   - Backend queues job for story generation (no external APIs)
4. **Job Polling** → Simulates `JobProgressCard` behavior
   - Polls `GET /api/v1/jobs/{job_id}` every 2 seconds
   - Verifies `status`, `progress_percent`, and `scenes` fields
   - Confirms each scene has expected fields (title, duration, image_prompt, etc.)
5. **Placeholder Verification** → Checks that static assets are served
   - SVG/PNG image placeholders accessible at `/static/placeholders/placeholder_4k.*`
   - Silent MP3 accessible at `/static/placeholders/placeholder_silent.mp3`
6. **Final Video Check** → Fetches project details to confirm download link

## Interpreting Results

### Success ✓
All steps complete with `success: true` in the report.
- Frontend can create stories, poll jobs, and access placeholders.
- Job lifecycle flows correctly from `queued` → `processing` → `completed`.
- Placeholders render without errors.

### Partial Success (Some Warnings)
- If placeholder assets return 404, check `platform/frontend/public/static/placeholders/` exists.
- If job polling times out (stays in `queued` for >20 seconds), Celery workers may not be running.
  - Check: `docker compose logs worker_default`

### Failure ✗
- If registration/login fails, backend auth may be misconfigured.
- If Create Story API returns error, check backend logs: `docker compose logs backend`
- If polling fails repeatedly, Redis/Celery connection may be down.

## Testing in the Browser

After the smoke test passes, you can manually test the frontend UI:

1. Open `http://localhost:3000` in your browser.
2. Sign up with any email/password.
3. Click **✨ Create Story** button (in Dashboard header or Sidebar).
4. Fill in:
   - Title: "My Devotional Story"
   - Description: "Testing the frontend UI"
5. Click **Start Story**.
6. Watch the **JobProgressCard** update with:
   - Progress bar (0% → 100%)
   - Scene previews with placeholder images and silent audio
   - Final download link when job completes

The placeholders will automatically be replaced with real assets when the backend generates them.

## Troubleshooting

### Test fails with "Backend not reachable"
```powershell
docker compose ps
# Ensure 'backend' service shows as "Up"
docker compose logs backend
```

### Test fails with "User registration error"
```powershell
# Check PostgreSQL is running
docker compose ps postgres
# Check backend database connection
docker compose logs backend | grep -i database
```

### Job stuck in "queued" status
```powershell
# Check Celery workers are running
docker compose ps worker_tts worker_images worker_default
# Check Redis connection
docker compose logs redis
```

### Placeholder assets return 404
```powershell
# Verify files exist
ls platform/frontend/public/static/placeholders/
# If missing, regenerate:
python tools/generate_silent_mp3.py
```

## Next Steps

- Once smoke test passes locally, you can:
  - Deploy to Render.com: See `platform/docs/DEPLOYMENT_GUIDE.md`
  - Run with real API keys (OpenAI, ElevenLabs) to generate production assets
  - Scale to multiple users and projects
  - Add more story templates in `platform/templates/`

## Additional Resources

- Backend API docs: `http://localhost:8000/docs` (interactive Swagger UI)
- Frontend code: `platform/frontend/src/`
- Component locations:
  - `CreateStoryModal.jsx` — Modal for story input
  - `JobProgressCard.jsx` — Job status polling and scene previews
  - `ScenePreview.jsx` — Individual scene thumbnail + audio player
- Backend story generation: `platform/backend/workers/story_worker.py`
