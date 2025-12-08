# Production Deployment Guide

## Overview

This guide covers deploying the Bhakti Video Generator to production using Docker containers, GitHub Container Registry (GHCR), and automated CI/CD workflows.

## Local Development Setup

### Prerequisites

- Docker 20.10+ and Docker Compose 1.29+
- Git
- curl (for smoke testing)
- 50GB free disk space (for video processing and MinIO storage)

### Quick Start

```bash
# 1. Clone repository
git clone https://github.com/YOUR_ORG/bhakti-video-generator.git
cd bhakti-video-generator

# 2. Copy and customize environment
cp .env.example .env
nano .env  # Edit with your API keys and configuration

# 3. Start all services
make up

# 4. Run smoke tests
make smoke

# 5. View logs
make logs
```

**Access Points:**
- Frontend: http://localhost
- Backend API: http://localhost:8000
- MinIO Console: http://localhost:9001 (default: bhakti/bhakti123)
- Backend Docs: http://localhost:8000/docs

### Common Commands

```bash
make up              # Start all services
make down            # Stop all services
make logs            # View logs from all services
make restart         # Restart all services
make clean           # Remove volumes and containers (careful!)
make build-images    # Build Docker images locally
make smoke           # Run health and connectivity checks
```

## Configuration

### Environment Variables

All configuration is managed via `.env` file at the project root. Key variables:

```bash
# Backend Settings
PORT=8000
DEBUG=false
LOG_LEVEL=info

# Storage
STORAGE_PROVIDER=s3
S3_ENDPOINT=http://minio:9000
S3_ACCESS_KEY=bhakti
S3_SECRET_KEY=bhakti123
S3_BUCKET=bhakti-assets

# API Keys (get from services)
OPENAI_API_KEY=sk-...
ELEVENLABS_API_KEY=...

# YouTube Upload (optional)
ENABLE_YOUTUBE_UPLOAD=false
YOUTUBE_CHANNEL_ID=...
YOUTUBE_CLIENT_ID=...
YOUTUBE_CLIENT_SECRET=...

# Optional Services
ENABLE_REDIS=false
REDIS_URL=redis://redis:6379

# URLs
FRONTEND_PUBLIC_URL=http://localhost
BACKEND_PUBLIC_URL=http://localhost:8000
```

See `.env.example` for complete documentation.

### MinIO Setup

MinIO provides S3-compatible storage for local development.

**Console Access:**
- URL: http://localhost:9001
- Username: `bhakti`
- Password: `bhakti123`

**Initial Setup:**
- Bucket `bhakti-assets` created automatically via init container
- Default policy: download (read-only for public)
- Can be customized in `docker-compose.yml` create-buckets service

**For Production AWS S3:**
Replace in `.env`:
```bash
STORAGE_PROVIDER=s3
S3_ENDPOINT=https://s3.amazonaws.com
S3_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE
S3_SECRET_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
S3_BUCKET=bhakti-video-assets
```

## CI/CD Pipeline

### GitHub Actions Workflows

Two workflows automate the pipeline:

#### 1. CI Workflow (`.github/workflows/ci.yml`)

Runs on every push to `main`/`develop` and pull requests:

- **Linting**: Python flake8 + JavaScript ESLint
- **Type Checking**: mypy for backend + TypeScript for frontend
- **Testing**: pytest for backend, Jest for frontend
- **Smoke Test**: Minimal video render + job verification
- **Artifacts**: job_summary.json + frontend build (7-day retention)

**View Results:** GitHub Actions tab → CI workflow runs

#### 2. Release Workflow (`.github/workflows/release.yml`)

Automatically builds and pushes Docker images to GHCR:

**Triggers:**
- Every push to `main` branch
- Every Git tag (e.g., `git tag v1.0.0 && git push --tags`)

**Outputs:**
- `ghcr.io/YOUR_ORG/bhakti-video-generator-backend:latest`
- `ghcr.io/YOUR_ORG/bhakti-video-generator-frontend:latest`
- Version-specific tags (e.g., `:v1.0.0`, `:main-abc123def`)

### GitHub Secrets Configuration

Add to repository settings (Settings → Secrets and variables → Actions):

**Required for CI/CD:**
```
OPENAI_API_KEY          # sk-... from OpenAI
ELEVENLABS_API_KEY      # from ElevenLabs
```

**Optional (for YouTube upload):**
```
YOUTUBE_CLIENT_ID       # From Google Cloud Console
YOUTUBE_CLIENT_SECRET   # From Google Cloud Console
```

**For S3 (if using AWS instead of MinIO):**
```
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
```

### Setting Up GHCR Push

1. Generate GitHub Personal Access Token:
   - Go to Settings → Developer settings → Personal access tokens → Tokens (classic)
   - Create token with `write:packages` scope
   - Store securely

2. GitHub Actions automatically uses `GITHUB_TOKEN` (no setup needed)
   - Has automatic read/write access to packages
   - Tied to each workflow run
   - Cannot be reused outside the action

3. To pull images locally after push:
   ```bash
   docker login ghcr.io -u YOUR_GITHUB_USERNAME -p YOUR_GITHUB_TOKEN
   docker pull ghcr.io/YOUR_ORG/bhakti-video-generator-backend:latest
   ```

## Observability, Monitoring & Safety

### Structured Logging

All backend logs include:
- `request_id`: Unique request identifier for correlation
- `job_id`: Associated render job ID (if applicable)  
- `timestamp`: ISO 8601 timestamp
- Secret scrubbing: API keys, tokens automatically removed

**JSON Logs (Production):**
```bash
JSON_LOGS=true
```

**Pretty Logs (Development):**
```bash
JSON_LOGS=false
```

### Sentry Error Tracking

**Backend:**
```bash
SENTRY_DSN=https://your-sentry-key@sentry.io/project-id
```

**Frontend:**
```bash
VITE_SENTRY_DSN=https://your-sentry-key@sentry.io/project-id
```

Automatically captures errors with job_id, route, and request context.

### Prometheus Metrics

Endpoint: `GET /metrics/prometheus`

**Key Metrics:**
- `jobs_started_total`: Total jobs enqueued
- `jobs_succeeded_total`: Successfully completed jobs
- `jobs_failed_total`: Failed jobs (labeled by error type)
- `jobs_canceled_total`: User-canceled jobs
- `job_duration_seconds`: Time to complete (histogram)
- `step_duration_seconds`: Individual pipeline step timing
- `active_jobs`: Currently running jobs (gauge)
- `rate_limit_hits_total`: Rate limit rejections
- `quota_violations_total`: Quota exceeded events

**Prometheus Scrape Config:**
```yaml
scrape_configs:
  - job_name: 'bhakti-backend'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics/prometheus'
    scrape_interval: 30s
```

### Audit Logging

All sensitive actions logged to `platform/audit/audit-YYYYMMDD.jsonl` (daily rotation):
- Job enqueued (with topic, scene count, cost estimate)
- Job status reads
- Job cancellations
- Job completions (success/error)
- Rate limit violations
- Quota violations
- API auth failures

### Rate Limiting & Quotas

**Rate Limiting (default 10 per minute per IP):**
```bash
RATE_LIMIT_PER_MIN=20
```

**Quota Limits:**
```bash
MAX_SCENES=20              # Max scenes per video
MAX_SCENE_DURATION_SEC=20  # Max seconds per scene
MAX_TOTAL_DURATION_SEC=600 # Max 10 minutes total
MAX_JOB_COST=50.0          # Max $50 per job
```

Quota violations return 400 with clear error messages.

### Idempotency

Optional `Idempotency-Key` header prevents duplicate jobs on retry:

```bash
curl -X POST http://localhost:8000/render \
  -H "Idempotency-Key: unique-key-per-request" \
  ...
```

### Cost Guards

Backend estimates cost before processing and blocks if exceeds `MAX_JOB_COST`:
- OpenAI images: $0.04-0.20 each (by quality)
- Elevenlabs TTS: $0.015 per 1K characters
- Video rendering: $0.10-0.50 (by resolution)

### API Key Authentication (Optional)

```bash
API_KEY_ADMIN=admin-secret-key
API_KEY_CREATOR=creator-secret-key
```

Protected endpoints require `X-API-Key` header. Public endpoints (health, metrics) require no auth.

### Celery Worker & Redis

If `REDIS_URL` configured, uses Celery + Redis for distributed job processing. Otherwise falls back to in-memory queue.

**Worker Service:**
```yaml
services:
  worker:
    build:
      context: ./platform/backend
      dockerfile: Dockerfile
    command: celery -A app.celery_queue.celery_app worker --loglevel=info
    environment:
      - REDIS_URL=redis://redis:6379
```

### Job Cancellation

Request cancellation via DELETE endpoint:

```bash
curl -X DELETE http://localhost:8000/render/{job_id}/cancel
```

Frontend shows cancel button on RenderStatusPage with confirmation modal.

## Smoke Testing

### Local Smoke Test

```bash
make smoke
```

Tests:
1. Backend health (`/healthz`)
2. Frontend health (`/healthz`)
3. MinIO bucket connectivity

### Manual Smoke Test

```bash
# 1. Create test render plan
curl -X POST http://localhost:8000/render \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "test",
    "images": ["image1.jpg"],
    "duration": 10
  }'
# Returns: { "job_id": "abc123" }

# 2. Poll for completion (max 60 seconds)
curl http://localhost:8000/render/abc123/status

# 3. Check MinIO for output video
aws s3 ls s3://bhakti-assets/videos/ --endpoint-url http://localhost:9000 \
  --region us-east-1 \
  --aws-access-key-id bhakti \
  --aws-secret-access-key bhakti123
```

## Production Deployment

### Using Docker Compose (Single Server)

```bash
# On production server:
git clone https://github.com/YOUR_ORG/bhakti-video-generator.git
cd bhakti-video-generator

# Copy and configure
cp .env.example .env
# Edit .env with production values (real S3, API keys, etc.)

# Start services
docker-compose up -d

# Monitor
docker-compose logs -f
```

### Using Pre-built Images from GHCR

```bash
# Set in .env:
# BACKEND_IMAGE=ghcr.io/YOUR_ORG/bhakti-video-generator-backend:latest
# FRONTEND_IMAGE=ghcr.io/YOUR_ORG/bhakti-video-generator-frontend:latest

# In docker-compose override or via direct command:
docker run -d \
  --name backend \
  -p 8000:8000 \
  -e STORAGE_PROVIDER=s3 \
  -e S3_ENDPOINT=https://s3.amazonaws.com \
  ghcr.io/YOUR_ORG/bhakti-video-generator-backend:latest

docker run -d \
  --name frontend \
  -p 80:80 \
  -e VITE_API_BASE_URL=https://api.example.com \
  ghcr.io/YOUR_ORG/bhakti-video-generator-frontend:latest
```

### Using Kubernetes (Advanced)

For high-availability deployment, use Helm charts or manifests:

```bash
# Example manifest structure needed:
# - Deployment: backend (replicas: 2+)
# - Deployment: frontend (replicas: 2+)
# - Service: backend (ClusterIP:8000)
# - Service: frontend (LoadBalancer:80)
# - ConfigMap: for environment variables
# - Secret: for API keys
# - PersistentVolumeClaim: for video storage
# - RDS/S3: for production storage
```

## Health Endpoints

Both backend and frontend expose health endpoints for orchestration:

### Backend

```bash
# Liveness probe (fast, no dependencies)
curl http://localhost:8000/healthz
# Returns: 200 OK with minimal JSON

# Readiness probe (checks dependencies)
curl http://localhost:8000/readyz
# Returns: 200 OK if ffmpeg, tmp dir, disk space available
# Returns: 503 Service Unavailable if any dependency missing
```

### Frontend

```bash
# Health check
curl http://localhost/healthz
# Returns: 200 OK
```

## Monitoring & Logging

### Container Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f minio

# Last 100 lines
docker-compose logs --tail=100 backend
```

### Application Logs

Backend logs include:
- Request/response details
- Video render progress
- S3 operations
- API errors

Frontend logs available in:
- Browser console (F12)
- Docker container stdout

### Disk Space Monitoring

Video generation requires significant disk:
- Temporary files: `/tmp` (ensure 50GB+ free)
- MinIO storage: docker volume `minio_data`
- Output videos: S3 bucket

Monitor with:
```bash
# Check MinIO storage
df -h /var/lib/docker/volumes/

# Check S3 bucket size
aws s3 ls s3://bhakti-assets/ --recursive --sum
```

## Troubleshooting

### Services Won't Start

```bash
# Check docker daemon
docker ps

# Inspect service logs
docker-compose logs backend
docker-compose logs frontend

# Verify images built correctly
docker images | grep bhakti
```

### Backend Can't Connect to S3

```bash
# Verify MinIO is running
docker-compose ps minio

# Test MinIO connectivity
docker-compose exec backend curl -v http://minio:9000/

# Check S3_ENDPOINT env var
docker-compose exec backend env | grep S3
```

### Video Render Fails

```bash
# Check ffmpeg availability
docker-compose exec backend which ffmpeg

# Verify tmp dir is writable
docker-compose exec backend touch /tmp/test && rm /tmp/test

# Check disk space
docker-compose exec backend df -h /tmp
```

### Frontend Shows 404

```bash
# Verify nginx config
docker-compose exec frontend nginx -t

# Check API connectivity
curl -v http://localhost:8000/healthz

# Inspect nginx logs
docker-compose logs frontend | grep error
```

## Creator Mode Features

Creator Mode unlocks production-grade features for content creators:

### Templates & Quick Start

Preset Bhakti video templates for instant creation:

**Endpoint:** `GET /templates` - List available templates
```bash
curl http://localhost:8000/api/templates
```

**Response:**
```json
{
  "templates": [
    {
      "id": "prahlad",
      "title": "Prahlad Charitram",
      "description": "Epic story of Prahlad's devotion",
      "tags": ["devotion", "epic"]
    },
    {
      "id": "ganga_avatar",
      "title": "Ganga Avatar",
      "description": "Sacred descent of River Ganga",
      "tags": ["sacred", "river"]
    }
  ]
}
```

**Build Plan from Template:** `POST /templates/plan`
```bash
curl -X POST http://localhost:8000/api/templates/plan \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": "prahlad",
    "language": "en",
    "length_sec": 60,
    "voice": "F"
  }'
```

### Dual Subtitles (Hindi + English)

Generate SRT subtitle files in multiple languages:

**Automatic Generation:** During render, if `ENABLE_DUAL_SUBTITLES=true`, both Hindi and English subtitles are generated and included in response.

**Status Response Includes:**
```json
{
  "job_id": "...",
  "dual_subtitles": {
    "hi_url": "s3://bucket/subtitles_hi.srt",
    "en_url": "s3://bucket/subtitles_en.srt"
  }
}
```

### Thumbnail Composer

Auto-generate 1280x720 PNG thumbnails from first scene + title:

**Automatic Generation:** Called post-render if `ENABLE_THUMBNAIL=true`. Includes bold text, glow effect, and watermark.

**Status Response Includes:**
```json
{
  "job_id": "...",
  "thumbnail_url": "s3://bucket/thumbnail_xxx.png"
}
```

### Content Library

Browse and duplicate past video projects:

**List Library:** `GET /library?page=1&page_size=20&state=success&language=en`
```bash
curl http://localhost:8000/api/library?page=1&page_size=20
```

**Response:**
```json
{
  "entries": [
    {
      "job_id": "abc123",
      "title": "Prahlad Story",
      "state": "success",
      "final_video_url": "s3://...",
      "thumbnail_url": "s3://...",
      "youtube_url": "https://youtube.com/watch?v=...",
      "created_at": "2025-12-20T10:00:00Z"
    }
  ],
  "total": 42,
  "has_more": true
}
```

**Duplicate for Reuse:** `POST /library/{job_id}/duplicate`
```bash
curl -X POST http://localhost:8000/api/library/abc123/duplicate
```

Returns a fully-formed RenderPlan ready for customization and re-submission.

### Scheduled Publishing

Schedule automatic YouTube publishing at future date/time:

**Schedule Publish:** `POST /publish/{job_id}/schedule`
```bash
curl -X POST http://localhost:8000/api/publish/abc123/schedule \
  -H "Content-Type: application/json" \
  -d '{
    "iso_datetime": "2025-12-25T14:00:00Z",
    "title": "Prahlad - Eternal Devotion",
    "description": "A beautiful story...",
    "tags": ["bhakti", "prahlad"]
  }'
```

**Get Schedule Status:** `GET /publish/{job_id}`
```bash
curl http://localhost:8000/api/publish/abc123
```

**Cancel Schedule:** `DELETE /publish/{job_id}/cancel`
```bash
curl -X DELETE http://localhost:8000/api/publish/abc123/cancel
```

**Background Processing:** Celery Beat runs `process_scheduled_publishes()` every minute to check for due publishes and trigger YouTube upload via youtube_service.

### Configuration

Enable Creator Mode features via environment:

```bash
# .env
ENABLE_TEMPLATES=true          # Template library
ENABLE_LIBRARY=true            # Content library & duplication
ENABLE_SCHEDULING=true         # Scheduled publishing
ENABLE_DUAL_SUBTITLES=true     # Multi-language subtitles
ENABLE_THUMBNAIL=true          # Thumbnail generation
SCHEDULE_TZ=UTC                # Timezone for scheduled publishes

# YouTube Integration
YOUTUBE_API_KEY=...
YOUTUBE_CLIENT_ID=...
YOUTUBE_CLIENT_SECRET=...
```

## Scaling

### Horizontal Scaling (Multiple Backends)

For high-load scenarios:

```bash
# Scale backend service in docker-compose
docker-compose up -d --scale backend=3

# Behind a load balancer (nginx reverse proxy)
# Distribute render requests across instances
```

### Caching Layer (Redis)

Enable Redis in `.env`:
```bash
ENABLE_REDIS=true
```

Then uncomment redis service in `docker-compose.yml`:
```yaml
  redis:
    image: redis:7-alpine
```

## Updates & Patching

### Updating to Latest Version

```bash
# Pull latest code
git pull origin main

# Pull latest images (if using GHCR)
docker-compose pull

# Restart services with new images
docker-compose up -d --no-build
```

### Rolling Updates (Zero Downtime)

```bash
# Update one backend instance at a time
docker-compose up -d --scale backend=2  # Increase replicas
# ... update infrastructure ...
docker-compose up -d --scale backend=1  # Reduce old instances
```

## Support & Documentation

- **Backend API Docs**: http://your-backend:8000/docs (Swagger/OpenAPI)
- **GitHub Issues**: https://github.com/YOUR_ORG/bhakti-video-generator/issues
- **Docker Compose Docs**: https://docs.docker.com/compose/
- **GHCR Docs**: https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry

## Security Considerations

### Credentials & Secrets

- **Never** commit `.env` file to git (use `.env.example`)
- Rotate API keys regularly
- Use GitHub Secrets for CI/CD (not in commits)
- Use environment variables (not hardcoded values)

### Network Security

- Restrict MinIO console access (only from trusted IPs in production)
- Use HTTPS/TLS for production (nginx reverse proxy with Let's Encrypt)
- Enable authentication on all services
- Use VPC/private networks where possible

### Container Security

- Images run as non-root users (uid 1000)
- No sensitive data in image layers
- Regularly scan images for vulnerabilities
- Use read-only root filesystem if possible
- Limit container resource usage (CPU, memory)

## Fast Path GPU Rendering

### Overview

The Fast Path GPU renderer uses NVIDIA NVENC hardware acceleration to dramatically speed up video rendering compared to CPU-based encoding. It includes scene caching, parallel rendering, and automatic fallback to CPU encoding when GPU is unavailable.

### NVENC Verification

**Check if NVENC is available:**
```bash
# Check GPU
nvidia-smi

# Check FFmpeg NVENC support
docker exec bhakti-backend ffmpeg -encoders | grep nvenc

# Expected output:
#  V..... h264_nvenc        NVIDIA NVENC H.264 encoder
#  V..... hevc_nvenc        NVIDIA NVENC H.265 encoder
```

**If NVENC not available:**
- Ensure NVIDIA drivers installed (version >= 418.81)
- Verify GPU supports NVENC: https://developer.nvidia.com/video-encode-and-decode-gpu-support-matrix
- For Docker: Ensure nvidia-container-toolkit installed and GPU passthrough configured
- System will automatically fallback to libx264 (CPU encoding)

### Environment Variables

Add to `.env` file:

```bash
# Fast Path GPU Rendering
FAST_PATH=1                # Enable GPU-accelerated rendering (default: 1)
ENCODER=h264_nvenc         # h264_nvenc | hevc_nvenc | libx264 (default: h264_nvenc)
TARGET_RES=1080p           # 720p | 1080p | 4k (default: 1080p)
RENDER_MODE=FINAL          # PROXY (fast preview) | FINAL (production quality)
CQ=18                      # Constant quality: 0-51, lower=better (default: 18)
VBR_TARGET=20M             # Variable bitrate target (default: 20M)
MAXRATE=40M                # Maximum bitrate (default: 40M)
BUFSIZE=80M                # Buffer size (default: 80M)
FPS=30                     # Frames per second (default: 30)
MUSIC_DB=-12               # Music volume in dB, negative=quieter (default: -12)
WATERMARK_POS=br           # Watermark position: tl|tr|bl|br (default: br)
UPSCALE=none               # Upscaling: none|realesrgan|zscale (default: none)
TMP_WORKDIR=/tmp/bhakti    # Temp directory for scene caches
DEBUG=0                    # Set to 1 to keep temp files for debugging
```

### Docker GPU Passthrough

**For Docker with NVIDIA GPU:**

1. Install nvidia-container-toolkit:
```bash
# Ubuntu/Debian
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

2. Update `docker-compose.yml`:
```yaml
services:
  backend:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

3. Verify GPU accessible in container:
```bash
docker exec bhakti-backend nvidia-smi
```

### Fallback Behavior

The renderer automatically handles NVENC unavailability:

1. **At startup**: Checks if NVENC encoders available via FFmpeg
2. **During render**: If NVENC requested but unavailable, falls back to libx264
3. **Metadata tracking**: `job_summary.json` records actual encoder used

**Check which encoder was used:**
```bash
cat platform/pipeline_outputs/<job_id>/job_summary.json | jq '.encoder'

# Output: "h264_nvenc" (GPU) or "libx264" (CPU fallback)
```

### Performance Benchmarks

Typical render times for 2-minute 1080p video with 10 scenes:

| Mode | Encoder | Hardware | Time | File Size |
|------|---------|----------|------|-----------|
| PROXY | h264_nvenc | RTX 3080 | ~45s | 60MB |
| FINAL | h264_nvenc | RTX 3080 | ~3m | 120MB |
| FINAL | libx264 | 8-core CPU | ~8m | 100MB |

**Scene caching impact:**
- First render: Full time (as above)
- Re-render unchanged scenes: ~10-20% of full time
- Single scene change: ~30% of full time

### PROXY vs FINAL Mode

**PROXY Mode:**
- Fast preview for iteration (3-5x faster)
- Lower quality settings (CQ+5, preset=fast)
- Use for: Testing content, layout, timing
- Set: `RENDER_MODE=PROXY`

**FINAL Mode:**
- Production-ready output
- High quality (CQ=18, preset=slow, VBR optimization)
- Use for: YouTube uploads, final delivery
- Set: `RENDER_MODE=FINAL`

### Troubleshooting

**NVENC not detected:**
- Check driver version: `nvidia-smi`
- Update NVIDIA drivers: https://www.nvidia.com/Download/index.aspx
- Verify FFmpeg compiled with NVENC: `ffmpeg -encoders | grep nvenc`
- For Docker: Ensure GPU passthrough configured (see above)

**Slow rendering despite GPU:**
- Verify NVENC being used: `cat job_summary.json | jq '.encoder'`
- If shows "libx264", NVENC fallback occurred
- Check GPU utilization: `nvidia-smi` (should show 20-50% GPU, 80-100% encoder)

**Out of memory errors:**
- Lower resolution: `TARGET_RES=720p`
- Use PROXY mode: `RENDER_MODE=PROXY`
- Reduce parallel workers in `video_renderer.py` (default: 4 → 2)

**Temp files not cleaned up:**
- Ensure `DEBUG=0` in production
- Check disk usage: `du -sh $TMP_WORKDIR/*`
- Manual cleanup: `rm -rf $TMP_WORKDIR/*`

### Monitoring

**GPU utilization during render:**
```bash
watch -n 1 nvidia-smi

# Expected during NVENC render:
#   GPU Utilization: 20-50%
#   Encoder Utilization: 80-100%
#   Memory Usage: 2-4GB
```

**Render progress:**
```bash
# Watch job status
watch -n 2 "curl -s http://localhost:8000/api/status/<job_id> | jq '.state'"

# Check timings after completion
cat platform/pipeline_outputs/<job_id>/job_summary.json | jq '.render_timings'
```

## Service Level Objectives (SLOs) & Error Budgets

### Render Latency Targets

**Definition:** p95 render completion time per minute of video length (FINAL mode, 1080p, NVENC)

| Video Length | p95 Target | p99 Target | Notes |
|--------------|------------|------------|-------|
| 30s | < 2 min | < 3 min | Shorts, quick edits |
| 60s | < 5 min | < 8 min | Standard YouTube videos |
| 3-5 min | < 15 min | < 25 min | Long-form content |
| 10 min | < 30 min | < 45 min | Educational series |

**Measurement:**
- Query `job_duration_seconds` histogram from Prometheus
- Filter by `status="success"` and `render_mode="FINAL"`
- Calculate p95/p99 over 7-day rolling window

**Example Prometheus query:**
```promql
histogram_quantile(0.95, 
  rate(job_duration_seconds_bucket{status="success",render_mode="FINAL"}[7d])
)
```

### Availability Targets

| Service | Target Uptime | Downtime Budget/Month | Measurement |
|---------|---------------|------------------------|-------------|
| Backend API | 99.9% | 43 minutes | `/healthz` probe success rate |
| GPU Rendering | 99.5% | 3.6 hours | Job success rate (excluding user errors) |
| YouTube Upload | 99.0% | 7.2 hours | Upload success rate (excluding quota errors) |
| Storage (S3/MinIO) | 99.9% | 43 minutes | S3 operation success rate |

### Error Budget Policy

**When to alert & page:**

1. **Critical (Page On-Call):**
   - Backend `/healthz` failing for > 2 minutes
   - GPU rendering success rate < 95% over 1 hour window
   - Disk free space < 2GB
   - Job timeout rate > 10% over 1 hour
   - p95 render latency > 2x target for 15 minutes

2. **Warning (Slack/Email Only):**
   - p95 render latency > 1.5x target for 1 hour
   - Provider 429 rate limit hits increasing (> 5/hour)
   - Disk free space < 5GB
   - Queue depth > 20 jobs for 10 minutes

3. **Acceptable (No Alert):**
   - Individual job failures due to user input errors
   - YouTube 403 quota exceeded (expected during peak)
   - Occasional 429 rate limits from providers (< 5/hour)

### Prometheus Alert Examples

**Backend Down:**
```yaml
- alert: BackendHealthCheckFailing
  expr: up{job="bhakti-backend"} == 0
  for: 2m
  labels:
    severity: critical
  annotations:
    summary: "Backend health check failing"
    description: "Backend has been unreachable for 2 minutes"
```

**High Job Timeout Rate:**
```yaml
- alert: HighJobTimeoutRate
  expr: |
    rate(job_timeouts_total[1h]) / rate(jobs_started_total[1h]) > 0.10
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "High job timeout rate (> 10%)"
    description: "{{ $value | humanizePercentage }} of jobs timing out"
```

**Low Disk Space:**
```yaml
- alert: LowDiskSpace
  expr: disk_free_gb < 2
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "Disk space critically low"
    description: "Only {{ $value }}GB free (< 2GB threshold)"
```

**High Queue Depth:**
```yaml
- alert: HighQueueDepth
  expr: queue_depth > 20
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "Job queue backing up"
    description: "{{ $value }} jobs waiting (> 20 threshold)"
```

### Grafana Dashboard Panels

**Recommended dashboard layout:**

**Row 1: Health Overview**
- Panel: Backend uptime gauge (target: 99.9%)
- Panel: GPU rendering success rate (target: 99.5%)
- Panel: Active jobs gauge

**Row 2: Render Performance**
- Panel: p95/p99 job duration by video length (line chart)
- Panel: Jobs started/succeeded/failed rate (counter)
- Panel: Job timeouts total (counter)

**Row 3: Resource Utilization**
- Panel: Queue depth (gauge + history)
- Panel: GPU in use (0/1 gauge)
- Panel: Disk free GB (gauge + alert threshold)

**Row 4: Provider Health**
- Panel: Provider check duration (heatmap by provider)
- Panel: Provider 429 rate (by provider)
- Panel: YouTube upload failures (by reason)

**Row 5: Error Rates**
- Panel: Error rate by type (stacked area chart)
- Panel: Rate limit violations (counter)
- Panel: Quota violations (counter)

**Example Grafana JSON:**
```json
{
  "dashboard": {
    "title": "Bhakti Video Generator",
    "panels": [
      {
        "title": "p95 Render Latency",
        "targets": [{
          "expr": "histogram_quantile(0.95, rate(job_duration_seconds_bucket[5m]))"
        }],
        "thresholds": [
          {"value": 300, "color": "green"},
          {"value": 600, "color": "yellow"},
          {"value": 900, "color": "red"}
        ]
      }
    ]
  }
}
```

### Sentry Integration

**Error categorization:**
- **Critical:** Infrastructure failures (S3 down, GPU unavailable, FFmpeg crash)
- **High:** Render failures despite valid input (encoder errors, out of memory)
- **Medium:** Provider API errors (OpenAI 500, ElevenLabs 429)
- **Low:** User input validation errors (invalid topic, missing API key)

**Sentry alert routing:**
```python
# In backend app/__init__.py
import sentry_sdk

sentry_sdk.init(
    dsn=os.environ.get("SENTRY_DSN"),
    traces_sample_rate=0.1,
    profiles_sample_rate=0.1,
    before_send=scrub_secrets,
)

# Tag errors with job context
sentry_sdk.set_context("job", {
    "job_id": job_id,
    "render_mode": render_mode,
    "encoder": encoder,
    "target_res": target_res,
})
```

### On-Call Runbook Links

When alerts fire, on-call should reference:
- **Provider Sanity Checks:** See RUNBOOK.md § Provider Sanity Checks
- **Timeout Troubleshooting:** See RUNBOOK.md § SLO Targets & Troubleshooting
- **Data Retention:** See RUNBOOK.md § Data Retention & Cleanup
- **GPU Diagnostics:** See PRODUCTION_DEPLOY.md § Troubleshooting

### SLO Review Cadence

- **Weekly:** Review error budgets, trend analysis
- **Monthly:** Adjust SLO targets based on actual performance
- **Quarterly:** Update alert thresholds based on false positive rate
- **Incident:** Post-mortem for SLO violations

### Production Best Practices

1. **Enable GPU passthrough** for Docker containers
2. **Set RENDER_MODE=FINAL** for production renders
3. **Monitor disk usage** of TMP_WORKDIR (enable log rotation)
4. **Use scene caching** by keeping TMP_WORKDIR persistent
5. **Set DEBUG=0** to cleanup temp files automatically
6. **Monitor GPU temperature** with nvidia-smi during high load
7. **Scale horizontally** with multiple instances using separate TMP_WORKDIR paths

---

**Last Updated:** 2024  
**Version:** 1.0  
**Contact:** DevOps Team
