# Hybrid Pipeline Architecture

## Overview

The **Hybrid Pipeline** extends the basic video rendering system with advanced motion, audio, and quality features while maintaining backward compatibility and graceful fallbacks in SIMULATE_RENDER mode.

## Core Features

### 1. Motion Templates (JSON-driven FFmpeg filters)
- **Location**: `platform/backend/app/motion/templates.py`
- **Templates**: 6 production-ready presets
  - `title_reveal`: Fade-in title with slide-up animation
  - `caption_slide`: Lower-third captions from left
  - `xfade_ease`: Smooth crossfade transitions
  - `wipe_left`: Hard wipe transitions
  - `glow_pulse`: Subtle glow with pulse effect
  - `vignette`: Cinematic edge darkening
- **Fallback**: Returns `"null"` filter in SIMULATE mode
- **Usage**: Applied per-scene for titles, captions, and transitions

### 2. 2.5D Parallax Motion
- **Location**: `platform/backend/app/motion/parallax.py`
- **Depth Estimation**: 
  - SIMULATE: Synthetic linear gradient (top→bottom)
  - Production: MiDaS depth estimation (optional)
- **Layer Splitting**: Segments image into foreground/middleground/background
- **Camera Moves**: Gentle zoom, pan right, dramatic (configurable)
- **Fallback**: Creates placeholder MP4s in SIMULATE mode

### 3. Audio-Led Editing
- **Location**: `platform/backend/app/audio/director.py`
- **Beat Detection**:
  - SIMULATE: Uniform grid at 100 BPM (0.6s intervals)
  - Production: Librosa onset detection
- **Voice Phrase Splitting**: Segments narration for natural pacing
- **Beat Snapping**: Aligns cuts to nearest beat within tolerance (±0.15s)
- **Music Ducking**: Reduces background music by -6dB during voiceover

### 4. Quality Profiles
- **Location**: `platform/backend/app/motion/profiles.py`
- **Profiles**:
  - **Preview**: 720p, 24fps, CQ=28, fast presets, minimal filters
  - **Final**: 1080p, 30fps, CQ=20, slow preset, deband/unsharp/grain/LUT
- **Configuration**: Returned as dict with fps, size, encoder, filters

### 5. Quality Assurance
- **Location**: `platform/backend/app/motion/qa.py`
- **Checks**:
  - No black frames (mean luma > 10)
  - Subtitle safe area (max 2 lines)
  - Music ducking metadata present
- **Status**: `"ok"` or `"warning"` (non-blocking)

## API Contract (P0 - Unchanged)

### POST /render
```json
{
  "topic": "string",
  "language": "en|hi",
  "voice": "F|M",
  "scenes": [{"image_prompt": "...", "narration": "...", "duration_sec": 3}],
  "enable_parallax": true,      // NEW
  "enable_templates": true,     // NEW
  "enable_audio_sync": true,    // NEW
  "quality": "preview|final"    // NEW
}
```

**Response** (unchanged):
```json
{
  "job_id": "uuid",
  "status": "queued",
  "estimated_wait_seconds": 0
}
```

### GET /render/{job_id}/status
**Response** (enriched with hybrid fields):
```json
{
  "job_id": "uuid",
  "state": "success",
  "progress_pct": 100,
  "final_video_url": "/artifacts/{job_id}/final_video.mp4",
  "assets": [...],
  "templates": {
    "applied": true,
    "count": 4
  },
  "parallax": {
    "applied": true,
    "scenes": 2
  },
  "audio_director": {
    "beats_used": 50,
    "ducking_applied": true
  },
  "profile": {
    "name": "final",
    "resolution": "1080p",
    "fps": 30
  },
  "qa": {
    "status": "ok"
  }
}
```

## job_summary.json Structure

```json
{
  "job_id": "uuid",
  "state": "success",
  "progress": 100,
  "final_video_url": "/artifacts/{job_id}/final_video.mp4",
  "templates": {
    "applied": true,
    "count": 4
  },
  "parallax": {
    "applied": true,
    "scenes": 2
  },
  "audio_director": {
    "beats_used": 50,
    "ducking_applied": true
  },
  "profile": {
    "name": "final",
    "resolution": "1080p",
    "fps": 30
  },
  "qa": {
    "status": "ok"
  },
  "timings": {
    "total_ms": 2000,
    "images_ms": 600,
    "audio_ms": 500,
    "subtitles_ms": 400,
    "stitch_ms": 400,
    "upload_ms": 100
  }
}
```

## Orchestrator Integration

### SIMULATE_RENDER=1 Behavior
- **Templates**: Logs count, returns identity filter
- **Parallax**: Creates placeholder MP4s with tiny_mp4()
- **Audio Director**: Returns synthetic beat grid
- **QA**: All checks pass with simulated data
- **No external dependencies**: Works without torch, librosa, FFmpeg

### Real Mode (Future)
- Templates compile to actual FFmpeg filter_complex strings
- Parallax runs MiDaS depth estimation and layer composition
- Audio director uses librosa for beat/onset detection
- QA probes actual video frames with FFmpeg

## Frontend Integration

### CreateVideoPage.tsx
**New Toggles** (lines 295-350):
- ☑ 2.5D Parallax Motion
- ☑ Motion Templates
- ☑ Audio-Led Editing
- 📊 Quality Profile (dropdown: Preview/Final)

**Default State**: All enabled, quality="final"

### RenderStatusPage.tsx
**Badges** (displayed when job completes):
- 📐 X Templates
- 🎬 Parallax (Y scenes)
- 🎵 Audio Sync (Z beats)
- ⭐ FINAL (1080p) or ⚡ PREVIEW (720p)
- ✓ QA: ok

## Environment Variables

```bash
# Core
SIMULATE_RENDER=1  # Use simulator mode (default in dev)

# Feature Flags (optional, defaults to enabled)
ENABLE_PARALLAX=1
ENABLE_TEMPLATES=1
ENABLE_AUDIO_SYNC=1
```

## File Structure

```
platform/backend/app/
├── motion/
│   ├── __init__.py
│   ├── templates.py      # 6 motion templates
│   ├── parallax.py       # 2.5D depth-based motion
│   ├── profiles.py       # Preview vs Final settings
│   └── qa.py             # Quality checks
└── audio/
    ├── __init__.py
    └── director.py       # Beat detection, ducking

platform/tests/
├── test_motion_templates.py  # 16 tests, all passing
├── test_parallax.py           # (placeholder)
├── test_audio_director.py     # (placeholder)
├── test_profiles.py           # (placeholder)
└── test_qa.py                 # (placeholder)

platform/orchestrator.py
└── run()  # Wires all hybrid features

platform/frontend/src/
├── pages/
│   ├── CreateVideoPage.tsx   # Feature toggles
│   └── RenderStatusPage.tsx  # Feature badges
└── types/
    └── api.ts                # RenderPlan with hybrid flags
```

## Graceful Degradation Strategy

1. **Missing FFmpeg filters**: Log warning, continue with identity filter
2. **Depth estimation unavailable**: Use synthetic gradient in SIMULATE mode
3. **Beat detection library missing**: Fall back to uniform grid
4. **QA probe fails**: Mark as warning, don't block completion
5. **Template compilation error**: Log `templates_applied=false`, proceed

## Cache Strategy

- **Scene Hash**: Already implemented in orchestrator
- **Parallax Clips**: Cache by hash of (scene_image, duration, style)
- **Beat Detection**: Cache by hash of music track
- **Depth Maps**: Cache by hash of input image

## Performance Notes

- **SIMULATE mode**: ~2s per job (no heavy computation)
- **Preview mode**: Target <30s for 2-scene video
- **Final mode**: Target <2min for 2-scene video (with real FFmpeg/depth)

## Security Notes

- All file paths validated before disk I/O
- FFmpeg commands sanitized (no shell injection)
- Temporary files cleaned up after render
- Artifacts served via /artifacts/ route (already secured)

## Testing

### Unit Tests
```bash
cd platform
python -m pytest tests/test_motion_templates.py -v  # 16/16 passing
```

### E2E Test
```bash
# See smoke_render.ps1
POST /render with all flags → 200
Poll /render/{id}/status → completed
Verify job_summary.json contains: templates, parallax, audio_director, profile, qa
GET /artifacts/{id}/final_video.mp4 → 200, video/mp4
```

## Next Steps

1. **Production FFmpeg Integration**: Wire compiled filters to actual ffmpeg commands
2. **MiDaS Depth Estimation**: Add torch/MiDaS for real parallax
3. **Librosa Integration**: Real beat detection for audio-led editing
4. **LUT/Grain**: Add color grading files for final profile
5. **Cache Persistence**: Redis or disk cache for scene hashes

## Migration Guide

**Existing jobs continue to work**: All hybrid fields are optional with sensible defaults.

**To enable hybrid features**:
1. Frontend: Use new CreateVideoPage toggles
2. Backend: Flags flow through RenderPlan → orchestrator
3. No breaking changes to /render or /render/{id}/status contracts

**Rollback**: Set `ENABLE_PARALLAX=0 ENABLE_TEMPLATES=0 ENABLE_AUDIO_SYNC=0` in env
