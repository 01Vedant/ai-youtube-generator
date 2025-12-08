# Fast Path GPU Rendering Runbook

## Quick Reference

### Environment Variables
```bash
FAST_PATH=1                # Enable GPU-accelerated rendering
ENCODER=h264_nvenc         # h264_nvenc | hevc_nvenc | libx264
TARGET_RES=1080p           # 720p | 1080p | 4k
RENDER_MODE=FINAL          # PROXY (fast preview) | FINAL (production)
CQ=18                      # Constant quality (lower=better, 18 recommended)
VBR_TARGET=20M             # Variable bitrate target
MAXRATE=40M                # Maximum bitrate
BUFSIZE=80M                # Buffer size
FPS=30                     # Frames per second
MUSIC_DB=-12               # Music volume in dB (negative=quieter)
WATERMARK_POS=br           # tl | tr | bl | br (top/bottom left/right)
UPSCALE=none               # none | realesrgan | zscale
TMP_WORKDIR=/tmp/bhakti    # Temp directory for scene caches
DEBUG=1                    # Skip temp file cleanup (for debugging)
```

## Verify NVENC Availability

### Check GPU and NVENC Driver
```bash
# Check NVIDIA GPU
nvidia-smi

# Expected output: GPU details, driver version, CUDA version
# If command not found: NVIDIA drivers not installed

# Check NVENC support in FFmpeg
ffmpeg -encoders | grep nvenc

# Expected output:
#  V..... h264_nvenc        NVIDIA NVENC H.264 encoder
#  V..... hevc_nvenc        NVIDIA NVENC H.265 encoder

# If no output: FFmpeg not compiled with NVENC support or driver issue
```

### Test NVENC Encoding
```bash
# Create test video with NVENC
ffmpeg -f lavfi -i testsrc=duration=5:size=1920x1080:rate=30 \
  -c:v h264_nvenc -preset fast -cq 18 test_nvenc.mp4

# If successful: NVENC is working
# If error "Cannot load nvcuda.dll" (Windows) or similar:
#   - Update NVIDIA drivers
#   - Ensure GPU supports NVENC (check https://developer.nvidia.com/video-encode-and-decode-gpu-support-matrix)
```

## Test Fast Path Locally

### Run Unit Tests
```bash
# Test video renderer with mocked ffmpeg
pytest tests/unit/test_video_renderer_fastpath.py -v -s

# Expected output: All tests pass
# Tests cover: NVENC detection, scene caching, fallback, PROXY vs FINAL mode
```

### Run E2E Smoke Test
```bash
# Set environment
export BACKEND_URL=http://localhost:8000
export FAST_PATH=1
export RENDER_MODE=PROXY
export TARGET_RES=1080p

# Start backend
cd platform/backend
python -m uvicorn app.main:app --reload &
sleep 5

# Run smoke test
pytest tests/smoke/test_fastpath_end_to_end.py -v -s

# Expected output: 2-scene video rendered successfully with fast_path=True metadata
# Test polls status until completion, verifies encoder/resolution/timings
```

### Manual Test with curl
```bash
# Submit render job with fast-path
curl -X POST http://localhost:8000/api/render \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Test Video",
    "language": "en",
    "voice": "F",
    "length": 10,
    "style": "cinematic",
    "fast_path": true,
    "render_mode": "PROXY",
    "target_res": "1080p",
    "scenes": [
      {
        "prompt": "Ancient temple at sunrise",
        "narration": "Test narration one",
        "duration": 3
      },
      {
        "prompt": "Sacred river at sunset",
        "narration": "Test narration two",
        "duration": 3
      }
    ]
  }'

# Response: {"job_id": "abc123..."}

# Poll status
curl http://localhost:8000/api/status/abc123

# Check job_summary.json after completion
cat platform/pipeline_outputs/abc123/job_summary.json

# Verify fast_path: true, encoder: "h264_nvenc" or "libx264", resolution: "1080p"
```

## PROXY vs FINAL Mode

### PROXY Mode (Fast Preview)
- **Purpose**: Quick preview for iteration
- **Quality**: Lower (CQ+5, preset=fast/ultrafast)
- **Speed**: 3-5x faster than FINAL
- **Use case**: Testing content, layout, timing before full render

```bash
export RENDER_MODE=PROXY
# Result: Fast render with visible compression artifacts, good enough for preview
```

### FINAL Mode (Production Quality)
- **Purpose**: Production-ready output for publishing
- **Quality**: High (CQ=18, preset=slow, VBR with maxrate)
- **Speed**: Slower (3-10 minutes for 60s video depending on GPU)
- **Use case**: Final video for YouTube upload

```bash
export RENDER_MODE=FINAL
# Result: High-quality render with minimal compression, optimized bitrate
```

### Comparison Example
```bash
# PROXY: 2-minute 1080p video in ~30 seconds, 50MB file
# FINAL: Same video in ~3 minutes, 100MB file with better quality
```

## Troubleshooting

### Scene Caching Not Working
**Symptom**: Re-rendering same video takes full time even though scenes unchanged

**Diagnosis**:
```bash
# Check temp directory
ls -lh $TMP_WORKDIR/<job_id>/

# Expected: scene_000_<hash>.mp4 files from previous run
```

**Solution**:
- Ensure TMP_WORKDIR has write permissions
- Check DEBUG=1 is not set (otherwise cache is cleaned up)
- Verify scene hash determinism (same image + narration + duration = same hash)

### NVENC Error: "Cannot load nvcuda.dll"
**Symptom**: FFmpeg fails with "Cannot load nvcuda.dll" or "No NVENC capable devices found"

**Diagnosis**:
```bash
nvidia-smi
# Check if GPU is detected and driver version >= 418.81 (for h264_nvenc)
```

**Solution**:
1. Update NVIDIA drivers: https://www.nvidia.com/Download/index.aspx
2. Verify GPU supports NVENC: https://developer.nvidia.com/video-encode-and-decode-gpu-support-matrix
3. For Windows: Ensure CUDA toolkit is installed
4. For Linux: Ensure nvidia-driver-XXX package installed, not nouveau

**Fallback**:
- System will automatically fallback to libx264 (CPU encoding)
- Check job_summary.json: encoder should be "libx264" instead of "h264_nvenc"

### FFmpeg Not Found
**Symptom**: "FileNotFoundError: [Errno 2] No such file or directory: 'ffmpeg'"

**Solution**:
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Windows (via Chocolatey)
choco install ffmpeg

# Verify installation
ffmpeg -version
```

### Out of Memory (CUDA OOM)
**Symptom**: "CUDA out of memory" or "cudaMalloc failed"

**Diagnosis**:
```bash
# Check GPU memory usage
nvidia-smi

# Check resolution and bitrate settings
echo $TARGET_RES $VBR_TARGET $MAXRATE
```

**Solution**:
1. Lower TARGET_RES: `export TARGET_RES=720p`
2. Lower VBR_TARGET: `export VBR_TARGET=10M`
3. Use PROXY mode: `export RENDER_MODE=PROXY`
4. Reduce parallel workers in video_renderer.py (max_workers=2 instead of 4)

### Slow Rendering Despite GPU
**Symptom**: Render takes longer than expected even with NVENC

**Diagnosis**:
```bash
# Check if NVENC is actually being used
ffmpeg -encoders | grep nvenc
cat platform/pipeline_outputs/<job_id>/job_summary.json | grep encoder

# If encoder is "libx264", NVENC is not being used (fallback occurred)
```

**Solution**:
- Verify NVENC availability (see "Verify NVENC Availability" section above)
- Check logs for "falling back to libx264" warning
- Ensure FAST_PATH=1 is set

### Temp Files Not Cleaned Up
**Symptom**: Disk space filling up with scene_XXX_*.mp4 files

**Diagnosis**:
```bash
du -sh $TMP_WORKDIR/*
```

**Solution**:
- Ensure DEBUG=1 is **not** set in production
- Check if cleanup code is executing (look for errors in logs)
- Manual cleanup: `rm -rf $TMP_WORKDIR/*` (be careful!)

### Filter Complex Errors
**Symptom**: "Cannot find a valid device" or "Invalid filter complex"

**Diagnosis**:
```bash
# Test watermark overlay
ffmpeg -i video.mp4 -i watermark.png \
  -filter_complex "[0:v][1:v]overlay=W-w-10:H-h-10[vout]" \
  -map "[vout]" test_output.mp4
```

**Solution**:
- Verify watermark file exists and is valid image format (PNG/JPG)
- Check watermark position (tl, tr, bl, br)
- Ensure audio file is valid if using music overlay

## Performance Benchmarks

### Typical Render Times (2-minute 1080p video, 10 scenes, RTX 3080)

| Mode | Encoder | Preset | Time | File Size | Quality |
|------|---------|--------|------|-----------|---------|
| PROXY | h264_nvenc | fast | ~45s | 60MB | Good for preview |
| FINAL | h264_nvenc | slow | ~3m | 120MB | Excellent |
| FINAL | libx264 | slow | ~8m | 100MB | Excellent (CPU) |

### Scene Caching Impact
- **First render**: Full time (as above)
- **Re-render unchanged scenes**: ~10-20% of full time
- **Single scene change**: Only that scene re-renders, ~30% of full time

## Monitoring

### Check Render Progress
```bash
# Watch GPU utilization
watch -n 1 nvidia-smi

# Expected during NVENC render:
#   - GPU Utilization: 20-50%
#   - Encoder Utilization: 80-100%
#   - Memory Usage: 2-4GB depending on resolution

# Watch job status
watch -n 2 "curl -s http://localhost:8000/api/status/<job_id> | jq '.state'"
```

### Log Files
```bash
# Backend logs
tail -f platform/backend/app.log

# Pipeline logs (if configured)
tail -f platform/pipeline_outputs/<job_id>/render.log

# Look for:
#   - "Scene X rendered in Y.Ys" (confirms parallel rendering)
#   - "Concatenation completed in Y.Ys" (final assembly)
#   - "Fast path render completed: h264_nvenc @ 1080p" (success)
#   - "falling back to libx264" (NVENC unavailable warning)
```

## Best Practices

### Development/Testing
```bash
export FAST_PATH=1
export RENDER_MODE=PROXY
export TARGET_RES=720p
export DEBUG=1  # Keep temp files for debugging
```

### Production
```bash
export FAST_PATH=1
export RENDER_MODE=FINAL
export TARGET_RES=1080p
export ENCODER=h264_nvenc  # Or hevc_nvenc for better compression
export CQ=18
export VBR_TARGET=20M
export MAXRATE=40M
export BUFSIZE=80M
export DEBUG=0  # Cleanup temp files
```

### High-Volume Production
- Use scene caching: Keep TMP_WORKDIR persistent between renders
- Monitor disk usage: Set up log rotation for TMP_WORKDIR
- Scale horizontally: Run multiple instances with separate TMP_WORKDIR paths
- Use HEVC (hevc_nvenc) for better compression if playback devices support it

## Emergency Procedures

### Kill Stuck Render
```bash
# Find process
ps aux | grep ffmpeg

# Kill specific job's ffmpeg processes
pkill -f "ffmpeg.*<job_id>"

# Or kill all ffmpeg processes (use with caution)
pkill ffmpeg
```

### Clear All Temp Files
```bash
# Backup important renders first!
cp -r platform/pipeline_outputs/<job_id> ~/backups/

# Clear temp directory
rm -rf $TMP_WORKDIR/*

# Clear old job outputs (older than 7 days)
find platform/pipeline_outputs -type d -mtime +7 -exec rm -rf {} \;
```

### Reset to MoviePy Fallback
```bash
# Disable fast-path temporarily
export FAST_PATH=0

# Restart backend
pkill -f uvicorn
cd platform/backend
python -m uvicorn app.main:app --reload
```

## Provider Sanity Checks

### Preflight Diagnostics

Check all system dependencies and providers before production:

```bash
# Basic health check (no external dependencies)
curl http://localhost:8000/diagnostics/preflight

# Full check including providers (may take up to 2s per provider)
curl http://localhost:8000/diagnostics/preflight?check_providers=true
```

**Expected response (all passing):**
```json
{
  "ok": true,
  "timestamp": "2025-12-20T10:00:00Z",
  "ffmpeg": {"ok": true, "reason": "ffmpeg 4.4.2 available"},
  "nvenc": {"ok": true, "reason": "h264_nvenc, hevc_nvenc available"},
  "disk": {"ok": true, "reason": "45.2 GB free"},
  "tmp": {"ok": true, "reason": "/tmp/bhakti writable"},
  "s3": {"ok": true, "reason": "Connected to S3 bucket"},
  "openai": {"ok": true, "reason": "OpenAI API key valid"},
  "elevenlabs": {"ok": true, "reason": "ElevenLabs API accessible"},
  "youtube": {"ok": true, "reason": "YouTube OAuth configured"}
}
```

### Interpreting Check Failures

**FFmpeg check failed:**
```bash
# Install FFmpeg
sudo apt-get install ffmpeg  # Ubuntu/Debian
brew install ffmpeg          # macOS
choco install ffmpeg         # Windows

# Verify
ffmpeg -version
```

**NVENC check failed (optional, will fallback to CPU):**
```bash
# Check GPU
nvidia-smi

# Update drivers
# Visit: https://www.nvidia.com/Download/index.aspx

# Verify GPU supports NVENC
# Check: https://developer.nvidia.com/video-encode-and-decode-gpu-support-matrix
```

**Disk check failed:**
```bash
# Free up space
du -sh /tmp/bhakti/*
rm -rf /tmp/bhakti/old_jobs/

# Or adjust cleanup retention (see Data Retention section below)
```

**TMP check failed:**
```bash
# Fix permissions
mkdir -p /tmp/bhakti
chmod 1777 /tmp/bhakti

# Or set custom path
export TMP_WORKDIR=/var/tmp/bhakti
```

**S3 check failed:**
```bash
# Verify credentials
echo $S3_ACCESS_KEY
echo $S3_SECRET_KEY
echo $S3_ENDPOINT
echo $S3_BUCKET

# Test with AWS CLI
aws s3 ls s3://$S3_BUCKET --endpoint-url $S3_ENDPOINT \
  --access-key $S3_ACCESS_KEY --secret-key $S3_SECRET_KEY
```

**OpenAI check failed:**
```bash
# Verify API key format (starts with sk-)
echo $OPENAI_API_KEY

# Test directly
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# Check account status at: https://platform.openai.com/account/billing
```

**ElevenLabs check failed:**
```bash
# Verify API key
echo $ELEVENLABS_API_KEY

# Test directly
curl -X GET "https://api.elevenlabs.io/v1/user" \
  -H "xi-api-key: $ELEVENLABS_API_KEY"

# Check account and quota at: https://elevenlabs.io/subscription
```

**YouTube check failed:**
```bash
# Verify environment variables
echo $YOUTUBE_CLIENT_ID
echo $YOUTUBE_CLIENT_SECRET
echo $ENABLE_YOUTUBE_UPLOAD

# Check if token file exists
ls -lh youtube_tokens.json

# If missing, run OAuth flow:
python scripts/youtube_oauth_setup.py

# Check provider status
curl http://localhost:8000/publish/providers
```

### Provider Status Endpoint

Check which providers are configured and authenticated:

```bash
curl http://localhost:8000/publish/providers
```

**Response:**
```json
{
  "providers": {
    "youtube": {
      "configured": true,
      "enabled": true,
      "authenticated": true,
      "ready": true
    }
  }
}
```

**Field meanings:**
- `configured`: Environment variables present (CLIENT_ID, CLIENT_SECRET)
- `enabled`: ENABLE_YOUTUBE_UPLOAD=1
- `authenticated`: Token file exists (youtube_tokens.json)
- `ready`: All conditions true (ready to upload)

### Provider-Specific Troubleshooting

**OpenAI 401 Unauthorized:**
- API key expired or invalid
- Check billing: https://platform.openai.com/account/billing
- Rotate key in OpenAI dashboard and update OPENAI_API_KEY

**OpenAI 429 Rate Limit:**
- Increase rate limit tier in OpenAI account
- Add exponential backoff (already implemented in script generation)
- Spread requests across multiple API keys (load balancing)

**ElevenLabs 429 Rate Limit:**
- Upgrade subscription plan for higher quota
- Check quota usage: https://elevenlabs.io/subscription
- Wait for quota reset (monthly or character-based)

**YouTube 401 Unauthorized:**
- OAuth token expired or revoked
- Re-run OAuth flow: `python scripts/youtube_oauth_setup.py`
- Check token file: `cat youtube_tokens.json | jq '.refresh_token'`
- Automatic refresh happens on next upload attempt

**YouTube 403 Forbidden:**
- API quota exceeded (10,000 units/day default)
- Check quota: https://console.cloud.google.com/apis/api/youtube.googleapis.com/quotas
- Request quota increase or wait for daily reset (midnight Pacific Time)

**YouTube 429 Rate Limit:**
- Too many requests per second
- System automatically retries with exponential backoff
- Check Retry-After header in logs
- Spread uploads across time window

## Data Retention & Cleanup

### Retention Policies

**Default retention periods:**
- Pipeline outputs (videos, summaries): 30 days (MAX_LOCAL_DAYS)
- Temp files (scene caches): 7 days (MAX_TMP_DAYS)
- Logs: Rotate when >100MB

**Configure retention:**
```bash
# In .env
MAX_LOCAL_DAYS=30    # Pipeline outputs retention
MAX_TMP_DAYS=7       # Temp files retention
```

### Manual Cleanup

**On-demand cleanup via API:**
```bash
# Run cleanup job
curl -X POST http://localhost:8000/admin/retention/run \
  -H "X-API-Key: $ADMIN_API_KEY"
```

**Response:**
```json
{
  "status": "completed",
  "pipeline_outputs_freed_bytes": 5368709120,
  "pipeline_outputs_deleted_count": 42,
  "tmp_workdir_freed_bytes": 2147483648,
  "tmp_workdir_deleted_count": 103,
  "logs_rotated_count": 2,
  "errors": []
}
```

### Automated Cleanup (Cron)

**Setup cron job:**
```bash
# Edit crontab
crontab -e

# Run cleanup daily at 2 AM
0 2 * * * /path/to/docker/cron/cleanup.sh >> /var/log/bhakti-cleanup.log 2>&1
```

**Cleanup script configuration:**
```bash
# docker/cron/cleanup.sh
export BACKEND_URL=http://localhost:8000
export ADMIN_TOKEN=your-admin-api-key

# Test manually
bash docker/cron/cleanup.sh
```

### Kubernetes CronJob

**Deploy as K8s CronJob:**
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: bhakti-cleanup
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM UTC
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: cleanup
            image: curlimages/curl:latest
            env:
            - name: BACKEND_URL
              value: "http://backend-service:8000"
            - name: ADMIN_TOKEN
              valueFrom:
                secretKeyRef:
                  name: admin-secrets
                  key: api-key
            command:
            - sh
            - -c
            - |
              curl -X POST $BACKEND_URL/admin/retention/run \
                -H "X-API-Key: $ADMIN_TOKEN" \
                -H "Content-Type: application/json"
          restartPolicy: OnFailure
```

### Pinning Important Jobs

**Protect specific jobs from cleanup:**
```bash
# Create .pinned marker file in job directory
touch platform/pipeline_outputs/<job_id>/.pinned

# Job will not be deleted even if older than MAX_LOCAL_DAYS
```

**Unpin job:**
```bash
rm platform/pipeline_outputs/<job_id>/.pinned
```

### Emergency Disk Cleanup

**If disk full and cleanup fails:**
```bash
# 1. Find largest directories
du -sh /tmp/bhakti/* | sort -rh | head -20

# 2. Delete oldest temp files manually
find /tmp/bhakti -type f -mtime +7 -delete

# 3. Delete old pipeline outputs (except pinned)
find platform/pipeline_outputs -type d -mtime +30 \
  ! -path "*/.pinned" -exec rm -rf {} \;

# 4. Rotate large logs immediately
find platform/ -name "*.log" -size +100M -exec gzip {} \;
```

### Monitoring Disk Usage

**Check current usage:**
```bash
# Temp directory
du -sh /tmp/bhakti

# Pipeline outputs
du -sh platform/pipeline_outputs

# Logs
du -sh platform/*.log

# Total
df -h /
```

**Add to monitoring:**
```promql
# Prometheus query for low disk space alert
disk_free_gb < 5

# Grafana panel for disk usage over time
disk_free_gb
```

## SLO Targets & Troubleshooting

### Service Level Objectives

**Render latency targets (p95, FINAL mode, 1080p, NVENC):**

| Video Length | p95 Target | p99 Target | Troubleshoot If Exceeds |
|--------------|------------|------------|------------------------|
| 30s | < 2 min | < 3 min | Check GPU utilization |
| 60s | < 5 min | < 8 min | Check scene caching |
| 3-5 min | < 15 min | < 25 min | Check disk I/O |
| 10 min | < 30 min | < 45 min | Check parallel workers |

**Availability targets:**

| Service | Target | Budget/Month | Measure |
|---------|--------|--------------|---------|
| Backend API | 99.9% | 43 min | /healthz probe |
| GPU Rendering | 99.5% | 3.6 hr | Job success rate |
| YouTube Upload | 99.0% | 7.2 hr | Upload success rate |

**Error rate targets:**
- Job timeout rate: < 5% of total jobs
- Provider 429 rate: < 5 per hour
- Infrastructure failures: < 1% of total jobs

### Timeout Troubleshooting Tree

**If job times out (status="timeout"):**

```
Job Timeout Detected
├─ Check 1: Is TOTAL_RUNTIME_LIMIT_MIN reasonable?
│  ├─ YES: Proceed to Check 2
│  └─ NO: Increase limit (export TOTAL_RUNTIME_LIMIT_MIN=60)
│
├─ Check 2: Is GPU being used?
│  ├─ nvidia-smi shows encoder usage 80-100%: GPU working, proceed to Check 3
│  ├─ nvidia-smi shows 0% utilization: GPU not used, check:
│  │  ├─ FAST_PATH=1 set?
│  │  ├─ NVENC available? (ffmpeg -encoders | grep nvenc)
│  │  └─ Fallback to CPU occurred? (check job_summary.json encoder)
│  └─ nvidia-smi command not found: No GPU, must use CPU (expect 3-5x slower)
│
├─ Check 3: Is disk I/O the bottleneck?
│  ├─ Run: iostat -x 1 during render
│  ├─ High %util on disk: I/O bound, solutions:
│  │  ├─ Use faster storage (SSD vs HDD)
│  │  ├─ Move TMP_WORKDIR to tmpfs: export TMP_WORKDIR=/dev/shm/bhakti
│  │  └─ Reduce parallel workers in video_renderer.py
│  └─ Low %util: Not I/O bound, proceed to Check 4
│
├─ Check 4: Are external providers slow?
│  ├─ Check provider_check_ms histogram in Prometheus
│  ├─ OpenAI image gen slow (>30s per image):
│  │  ├─ Switch to faster model (dall-e-2 instead of dall-e-3)
│  │  └─ Pre-generate images, use static images
│  ├─ ElevenLabs TTS slow (>10s per narration):
│  │  ├─ Use shorter narrations
│  │  └─ Switch to local TTS (pyttsx3)
│  └─ Network latency: Check ping to provider APIs
│
├─ Check 5: Is scene count too high?
│  ├─ Count scenes: cat job_plan.json | jq '.scenes | length'
│  ├─ > 20 scenes: Consider splitting into multiple videos
│  └─ Scenes with long duration (>20s): Check MAX_SCENE_DURATION_SEC
│
└─ Check 6: Check logs for errors
   ├─ cat platform/pipeline_outputs/<job_id>/job_summary.json
   ├─ Look for:
   │  ├─ "error": "<message>" (failure reason)
   │  ├─ "render_timings": {...} (which step is slow?)
   │  └─ "encoder": "libx264" (CPU fallback occurred)
   └─ Check backend logs: tail -f platform/backend/app.log
```

### Provider 429 Handling

**If provider 429 rate limit hits increase:**

**OpenAI:**
```bash
# Check Prometheus metric
rate(provider_429_total{provider="openai"}[1h])

# Solutions:
# 1. Upgrade OpenAI tier for higher limits
# 2. Add delay between requests (already implemented with backoff)
# 3. Use multiple API keys with load balancing
# 4. Cache generated images aggressively
```

**ElevenLabs:**
```bash
# Check quota usage
curl -X GET "https://api.elevenlabs.io/v1/user" \
  -H "xi-api-key: $ELEVENLABS_API_KEY" | jq '.subscription'

# Solutions:
# 1. Upgrade subscription plan
# 2. Use shorter narrations
# 3. Pre-generate common narrations
# 4. Fallback to pyttsx3 for non-critical narrations
```

**YouTube:**
```bash
# Check quota in Google Cloud Console
# https://console.cloud.google.com/apis/api/youtube.googleapis.com/quotas

# Solutions:
# 1. Request quota increase from Google
# 2. Spread uploads across time (use scheduled publishing)
# 3. Use multiple YouTube channels with separate API projects
# 4. Queue uploads with rate limiting
```

### YouTube Upload Failure Reasons

**Check youtube_fail_total metric:**
```promql
youtube_fail_total{reason="quota_exceeded"}
youtube_fail_total{reason="token_invalid"}
youtube_fail_total{reason="network_error"}
```

**Troubleshoot by reason:**

**quota_exceeded:**
- Daily quota exhausted (10,000 units default)
- Wait for reset (midnight Pacific Time)
- Request increase: https://support.google.com/youtube/contact/yt_api_form

**token_invalid:**
- OAuth token expired or revoked
- Re-run OAuth flow: `python scripts/youtube_oauth_setup.py`
- Check token file exists: `ls -lh youtube_tokens.json`
- Automatic refresh attempted on 401 (check logs)

**network_error:**
- Transient network issue
- System retries with exponential backoff (3 attempts)
- Check network connectivity: `curl -I https://www.googleapis.com`
- Check firewall rules for outbound HTTPS

**video_too_large:**
- Video exceeds YouTube size limit (256GB for verified accounts, 128GB otherwise)
- Reduce resolution: export TARGET_RES=720p
- Increase compression: export CQ=28
- Split into multiple videos

**privacy_settings:**
- Channel not configured for public uploads
- Check channel settings: https://studio.youtube.com/channel/UC.../editing/details
- Set privacy_status="unlisted" or "private" in upload request

### Job Stuck in "running" State

**Diagnosis:**
```bash
# Check if backend process alive
ps aux | grep uvicorn

# Check if ffmpeg running
ps aux | grep ffmpeg

# Check job directory exists
ls -lh platform/pipeline_outputs/<job_id>/

# Check job_summary.json status
cat platform/pipeline_outputs/<job_id>/job_summary.json | jq '.status'
```

**Solutions:**

**Backend crashed:**
```bash
# Restart backend
systemctl restart bhakti-backend  # systemd
# or
docker-compose restart backend    # Docker
```

**FFmpeg process hung:**
```bash
# Kill stuck ffmpeg
pkill -f "ffmpeg.*<job_id>"

# Job will timeout and cleanup automatically
```

**Out of disk space:**
```bash
# Check disk
df -h /tmp/bhakti

# Free up space
curl -X POST http://localhost:8000/admin/retention/run

# Or manual cleanup
rm -rf /tmp/bhakti/*
```

### Prometheus Queries for SLO Monitoring

**p95 job duration:**
```promql
histogram_quantile(0.95, 
  rate(job_duration_seconds_bucket{status="success"}[7d])
)
```

**Job timeout rate:**
```promql
rate(job_timeouts_total[1h]) / rate(jobs_started_total[1h])
```

**Provider 429 rate:**
```promql
rate(provider_429_total[1h])
```

**YouTube upload success rate:**
```promql
rate(youtube_uploads_success_total[1h]) / 
(rate(youtube_uploads_success_total[1h]) + rate(youtube_fail_total[1h]))
```

**Backend availability:**
```promql
up{job="bhakti-backend"}
```

**Queue depth (current):**
```promql
queue_depth
```

**GPU utilization:**
```promql
gpu_in_use
```

**Disk free space:**
```promql
disk_free_gb
```

## Support

For issues not covered in this runbook:
1. Check logs in platform/pipeline_outputs/<job_id>/job_summary.json
2. Review FFmpeg documentation: https://ffmpeg.org/documentation.html
3. NVENC troubleshooting: https://docs.nvidia.com/video-technologies/video-codec-sdk/nvenc-video-encoder-api-prog-guide/
4. Provider API docs: OpenAI, ElevenLabs, YouTube Data API v3
5. SLO violations: See PRODUCTION_DEPLOY.md § Service Level Objectives
6. GitHub Issues: Open issue with job_summary.json and relevant logs
