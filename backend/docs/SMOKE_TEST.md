# Safe Smoke Test (Non-destructive)

This document explains how to run the safe smoke test for the DevotionalAI platform. The test verifies backend endpoints, storage, and job queuing without calling external image/TTS APIs.

Prerequisites
- Docker and Docker Compose (optional if you run services manually)
- Python 3.9+ and `pip` for running the smoke test script locally
- The services running locally via `docker compose up --build` (see instructions below)

Important: The smoke test avoids external API calls. Ensure `ELEVENLABS_API_KEY` and `OPENAI_API_KEY` are NOT set in your environment while running the smoke test to prevent accidental API usage.

Steps
1. Start services

```powershell
cd platform
docker compose up --build
```

Wait until the backend is ready at `http://localhost:8000` (check `docker compose logs backend`).

2. Run smoke test

Open a new terminal and run:

```powershell
python platform/tests/smoke_test.py
```

What the test does
- Registers a temporary user (unique email with timestamp)
- Creates a new project via API
- Writes placeholder 4K PNG images (`scene_{n}.png`) and short silent MP3s (`scene_{n}.mp3`) into the local storage folder used by the backend (default `./storage/{user}/{project}/...`)
- Writes simple .srt subtitle files
- Queues a video stitching job via the API (the job is created but will only be executed if workers are running)
- Verifies preview endpoints for image and audio return HTTP 200
- Fetches job status via `/api/v1/jobs/{job_id}`

Expected results
- The script prints the project id and job id
- `preview` endpoints return 200 for the placeholder image and audio
- Job status should exist and show `queued` or `running` (if workers are running)

Notes & Troubleshooting
- If your backend is configured to use S3 (`USE_S3=true`), the script writes to local storage and the backend will not find the files. Prefer `USE_S3=false` during local smoke tests.
- Make sure the `LOCAL_STORAGE_PATH` environment variable matches the backend config if you changed it.
- The test requires `pydub` and `Pillow`. Install with:

```powershell
pip install pillow pydub requests
```

- The test will not call ElevenLabs or OpenAI. If keys are set, no external calls are made by this script, but workers may attempt calls if you run them; keep keys unset to be safe.

Next steps
- After the smoke test, you can start the Celery workers (`worker_tts`, `worker_images`, `worker_default`) via Docker Compose to let the queued jobs run for real.
- If you want an end-to-end run (actual image/TTS generation), set `OPENAI_API_KEY` and `ELEVENLABS_API_KEY` in a safe environment and ensure you consent to API usage and cost.
