# How to Run the Bhakti Video Generator API + Frontend Locally

This guide walks you through setting up and running the production-ready Bhakti Video Generator locally on your machine.

## Prerequisites

- **Python 3.8+** (tested on 3.10+)
- **Node.js 16+** (for frontend)
- **FFmpeg** (for video processing) — install via:
  - **macOS**: `brew install ffmpeg`
  - **Ubuntu/Debian**: `apt-get install ffmpeg`
  - **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html) or `choco install ffmpeg`
- **Git** (for cloning the repo)

## Quick Start (Docker Compose)

The easiest way to run everything is with Docker:

```bash
cd platform
docker-compose up
```

This starts:
- FastAPI backend on `http://localhost:8000`
- React frontend on `http://localhost:3000`
- API available for development

## Manual Setup

### 1. Backend Setup

```bash
# Navigate to backend directory
cd platform/backend

# Create Python virtual environment
python -m venv venv

# Activate (choose based on OS):
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables (create .env file or export):
export OPENAI_API_KEY="your-api-key"  # Optional: for real image generation
export ELEVENLABS_API_KEY="your-api-key"  # Optional: for real TTS
export ENABLE_YOUTUBE_UPLOAD="0"  # Set to 1 to enable YouTube

# Run the FastAPI server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at: **http://localhost:8000**

API docs (Swagger UI): **http://localhost:8000/docs**

### 2. Frontend Setup

In another terminal:

```bash
# Navigate to frontend directory
cd platform/frontend

# Install dependencies
npm install

# Set environment variables
echo "VITE_API_URL=http://localhost:8000" > .env.local

# Start development server
npm run dev
```

The frontend will be available at: **http://localhost:5173** (or the port shown in terminal)

### 3. Run Tests

In a third terminal:

```bash
# Backend smoke test
cd platform
python tests/test_render_api.py

# Output:
# ============================================================
# SMOKE TEST: Render API
# ============================================================
# [1] Health check...
# ✓ API is healthy
# [2] Creating render job...
# ✓ Job created: abc123def456...
# [3] Polling job status...
#   Progress: 10% | State: running | Step: images
#   Progress: 25% | State: running | Step: tts
#   ...
# ✓ Job completed successfully
```

## API Endpoints

### Create a Video Render Job

**Request:**
```bash
curl -X POST http://localhost:8000/render \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Bhakti Yoga Principles",
    "language": "en",
    "voice": "female",
    "length": 30,
    "style": "cinematic",
    "scenes": [
      {
        "prompt": "Ancient temple at sunrise, ultra-detailed, 4K",
        "narration": "Welcome to the teachings of Bhakti Yoga.",
        "duration": 4
      },
      {
        "prompt": "Meditation in peaceful forest",
        "narration": "Through devotion, we find inner peace.",
        "duration": 4
      }
    ]
  }'
```

**Response:**
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "pending",
  "estimated_wait_seconds": 120
}
```

### Poll Job Status

**Request:**
```bash
curl http://localhost:8000/render/a1b2c3d4-e5f6-7890-abcd-ef1234567890/status
```

**Response:**
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "state": "running",
  "step": "stitch",
  "progress_pct": 75.0,
  "assets": {
    "images_count": 2,
    "tts_count": 2,
    "srt_path": "/path/to/subtitles.en.srt"
  },
  "final_video_url": null,
  "youtube_url": null,
  "logs": [
    "Starting job a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "Generating images...",
    "Generated images for scene scene-0",
    "Generating TTS audio...",
    "Generated TTS for scene scene-0"
  ],
  "error": null
}
```

### Get Platform Metrics

**Request:**
```bash
curl http://localhost:8000/metrics
```

**Response:**
```json
{
  "jobs_started": 5,
  "jobs_completed": 4,
  "jobs_failed": 1,
  "total_duration_seconds": 450.25,
  "image_errors": 0,
  "tts_errors": 0,
  "upload_errors": 1,
  "youtube_uploads": 0,
  "success_rate": 80.0
}
```

### Prometheus Metrics Export

**Request:**
```bash
curl http://localhost:8000/metrics/prometheus
```

**Response:**
```
# HELP bhakti_jobs_started Total jobs started
# TYPE bhakti_jobs_started counter
bhakti_jobs_started 5

# HELP bhakti_jobs_completed Total jobs completed successfully
# TYPE bhakti_jobs_completed counter
bhakti_jobs_completed 4
...
```

## Frontend Screenshots & Workflow

### TODO: Add screenshots

1. **Create Video Page** (`http://localhost:5173/create`)
   - [ ] Screenshot showing form with topic, language, voice, length, style inputs
   - [ ] Screenshot showing scene editor with image prompt and narration text areas
   - [ ] Screenshot showing "Create Video" button and form validation

2. **Status Page** (`http://localhost:5173/render/{job_id}`)
   - [ ] Screenshot showing progress bar at 0%, 50%, 100%
   - [ ] Screenshot showing pipeline steps timeline (images → tts → subtitles → stitch → upload)
   - [ ] Screenshot showing real-time logs as job progresses
   - [ ] Screenshot showing final "Video Ready" section with download button

3. **API Response Flow**
   - [ ] Network log showing POST /render response with job_id
   - [ ] Network log showing repeated GET /render/{job_id}/status with progress increments

## Troubleshooting

### "FFmpeg not found"
Make sure FFmpeg is installed and on your system PATH:
```bash
ffmpeg -version
```

### "OPENAI_API_KEY not set"
The system uses placeholder image generation if no API key is present. This is intentional for safe local testing.
To use real OpenAI images, set:
```bash
export OPENAI_API_KEY="sk-..."
```

### "Orchestrator not running" or "Movie Py errors"
Ensure `moviepy` is installed:
```bash
pip install moviepy imageio imageio-ffmpeg
```

### Port already in use
Change the port:
```bash
# Backend
python -m uvicorn app.main:app --port 8001

# Frontend (in .env.local)
VITE_PORT=3001
```

### Job hangs at a particular step
Check the logs in `platform/pipeline_outputs/{job_id}/job.log`:
```bash
tail -f platform/pipeline_outputs/*/job.log
```

## Optional: Enable YouTube Upload

To test YouTube integration (requires OAuth2 credentials):

1. Get credentials from [Google Cloud Console](https://console.cloud.google.com/)
2. Download `credentials.json` and place in `platform/`
3. Set environment variables:
   ```bash
   export ENABLE_YOUTUBE_UPLOAD="1"
   export YOUTUBE_API_KEY="your-api-key"
   ```
4. Include in request:
   ```json
   {
     "enable_youtube_upload": true,
     ...
   }
   ```

## Configuration

Key environment variables (also see `.env.example`):

```bash
# API Server
API_HOST=0.0.0.0
API_PORT=8000
API_LOG_LEVEL=INFO

# Image Generation (optional)
OPENAI_API_KEY=sk-...

# TTS Generation (optional)
ELEVENLABS_API_KEY=...

# YouTube Integration (optional)
ENABLE_YOUTUBE_UPLOAD=0
YOUTUBE_API_KEY=...
YOUTUBE_CLIENT_SECRET=...

# Storage (optional S3)
USE_S3=false
S3_BUCKET=...
S3_KEY=...
S3_SECRET=...
S3_ENDPOINT=...  # For S3-compatible services (Minio, etc.)
```

## Architecture Overview

```
┌─────────────────────────────────────────┐
│         React Frontend (3000)           │
│  ├─ CreateVideoPage                     │
│  └─ RenderStatusPage (real-time poll)   │
└────────────────┬────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────┐
│      FastAPI Backend (8000)             │
│  ├─ POST /render → enqueue job          │
│  ├─ GET /render/{job_id}/status → poll  │
│  └─ GET /metrics → Prometheus export    │
└────────────────┬────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────┐
│  Job Queue (in-memory or Celery)        │
│  ├─ Status tracking                     │
│  └─ Background job execution            │
└────────────────┬────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────┐
│    Pipeline Orchestrator                │
│  ├─ Image Engine (OpenAI fallback PIL)  │
│  ├─ TTS Engine (ElevenLabs fallback)    │
│  ├─ Subtitles (SRT generation)          │
│  ├─ Video Renderer (MoviePy + FFmpeg)   │
│  ├─ Storage (local + S3 support)        │
│  └─ YouTube Upload (optional)           │
└─────────────────────────────────────────┘
```

## Next Steps

1. **Customize**: Edit pipeline engines in `pipeline/image_engine.py`, `pipeline/tts_engine.py` to change API providers
2. **Deploy**: See `platform/docs/PRODUCTION_READINESS.md` for cloud deployment guide
3. **Scale**: Replace in-memory queue with Celery + Redis for production multi-worker setup
4. **Monitor**: Use `/metrics` and `/metrics/prometheus` for monitoring in production

## Support

- **Issues**: Check logs in `platform/pipeline_outputs/{job_id}/`
- **Debug**: Run with `--reload` flag to auto-restart on code changes
- **Tests**: Run `python tests/test_render_api.py` to verify setup

## License

This project is for educational and devotional use.
