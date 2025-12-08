# Hindi TTS Implementation Guide

## Overview

The Hindi TTS system provides high-quality, soothing female narration for devotional video content. It supports scene-aware pacing to match audio duration with scene timing.

## Features

- **Provider**: Microsoft Edge TTS (primary) with mock fallback
- **Voice**: `hi-IN-SwaraNeural` (soothing female, default)
- **Alternative**: `hi-IN-DiyaNeural` (female)
- **Sample Rate**: 24kHz, 16-bit PCM, mono
- **Scene Pacing**: Automatic time-stretching to match `duration_sec` (±5% tolerance)
- **Caching**: Hash-based caching to avoid re-synthesizing identical text

## Installation

### Dependencies

```bash
pip install edge-tts pydub
```

### Optional: librosa for better time-stretching

```bash
pip install librosa soundfile
```

### FFmpeg (Required for pydub)

**Windows**:
```powershell
# Download from https://ffmpeg.org/download.html
# Or use Chocolatey:
choco install ffmpeg
```

**Linux**:
```bash
sudo apt-get install ffmpeg
```

**macOS**:
```bash
brew install ffmpeg
```

## Configuration

Add to your `.env` file or set as environment variables:

```env
# TTS Provider Selection
TTS_PROVIDER=edge              # Options: edge, mock
TTS_VOICE=hi-IN-SwaraNeural    # Default Hindi voice
TTS_RATE=-10%                  # Rate adjustment (negative = slower, soothing)

# Audio Quality
AUDIO_SAMPLE_RATE=24000        # Sample rate in Hz
AUDIO_PACE_TOLERANCE=0.05      # 5% tolerance for duration matching
TTS_PAUSE_MS=200               # Pause between clauses (ms)

# SIMULATE mode (for testing without dependencies)
SIMULATE_RENDER=1              # Uses mock provider automatically
```

## Usage

### API: Render Request

```json
POST /render
{
  "topic": "Meera's Devotion",
  "language": "hi",
  "voice_id": "hi-IN-SwaraNeural",
  "scenes": [
    {
      "image_prompt": "Temple at dawn",
      "narration": "भोर की पहली किरण में मंदिर जागता है।",
      "duration_sec": 5
    },
    {
      "image_prompt": "Flickering diya lamp",
      "narration": "दीपक की लौ हिलती है।",
      "duration_sec": 4
    }
  ]
}
```

### API: TTS Preview

Preview a voice before rendering:

```bash
POST /tts/preview
{
  "text": "नमस्ते, यह एक परीक्षण है।",
  "lang": "hi",
  "voice_id": "hi-IN-SwaraNeural",
  "pace": 0.9
}

Response:
{
  "url": "/artifacts/_previews/abc123.wav",
  "duration_sec": 2.3,
  "cached": false
}
```

### Python: Direct Usage

```python
from backend.app.tts import synthesize, get_provider_info

# Check provider
info = get_provider_info()
print(f"Using provider: {info['name']}")

# Synthesize speech
wav_bytes, metadata = synthesize(
    text="नमस्ते, यह एक परीक्षण है।",
    lang="hi",
    voice_id="hi-IN-SwaraNeural",
    pace=0.9  # 10% slower
)

print(f"Duration: {metadata['duration_sec']}s")
print(f"Provider: {metadata['provider']}")
print(f"Cached: {metadata['cached']}")

# Save to file
with open("output.wav", "wb") as f:
    f.write(wav_bytes)
```

## Job Response Format

The `/render/{job_id}/status` endpoint returns audio metadata when Hindi TTS is used:

```json
{
  "job_id": "abc-123",
  "state": "success",
  "audio": {
    "lang": "hi",
    "voice_id": "hi-IN-SwaraNeural",
    "provider": "edge",
    "paced": true,
    "total_duration_sec": 12.5,
    "scenes": [
      {
        "scene_index": 1,
        "path": "audio/scene_1.wav",
        "duration_sec": 5.1,
        "paced": true
      },
      {
        "scene_index": 2,
        "path": "audio/scene_2.wav",
        "duration_sec": 4.0,
        "paced": false
      }
    ]
  }
}
```

## Available Voices

### Hindi

| Voice ID | Gender | Style | Use Case |
|----------|--------|-------|----------|
| `hi-IN-SwaraNeural` | Female | Soothing, calm | Default for devotional content |
| `hi-IN-DiyaNeural` | Female | Clear, friendly | Alternative option |

### English (Fallback)

| Voice ID | Gender | Style |
|----------|--------|-------|
| `en-US-AriaNeural` | Female | Natural, warm |

## Scene-Aware Pacing

The system automatically adjusts narration duration to match `duration_sec`:

1. **Synthesis**: Generate audio at natural pace
2. **Duration Check**: Compare actual vs. target duration
3. **Time-Stretch**: If difference > 5%, apply time-stretching without pitch change
4. **Tolerance**: Small differences (< 5%) are kept as-is for natural sound

### Pacing Strategies

- **< 5% difference**: No adjustment (natural)
- **5-20% difference**: Time-stretch using pydub frame rate manipulation
- **> 20% difference**: Time-stretch + fade/pad (rare edge case)

## Caching

TTS results are cached to improve performance:

- **Cache Key**: SHA-256 hash of `(voice_id, text, pace)`
- **Cache Location**: `pipeline_outputs/_cache/tts/`
- **Cache Hit**: Instant retrieval, no re-synthesis
- **Cache Miss**: Synthesize and save to cache

## Troubleshooting

### Edge-TTS Not Available

```
RuntimeError: edge-tts not available
```

**Solution**: Install edge-tts
```bash
pip install edge-tts
```

### pydub Not Found

```
RuntimeError: pydub required for MP3 to WAV conversion
```

**Solution**: Install pydub and ffmpeg
```bash
pip install pydub
# Install ffmpeg (see Installation section)
```

### No Audio Generated

**Check logs** for error messages:
```bash
# Backend logs will show:
# "TTS provider: mock" (fallback)
# or
# "TTS provider: edge" (real synthesis)
```

**Fallback behavior**: System automatically falls back to mock provider if Edge unavailable.

### Testing Without Dependencies

Set `SIMULATE_RENDER=1`:
```bash
export SIMULATE_RENDER=1  # Linux/Mac
$env:SIMULATE_RENDER="1"  # Windows PowerShell
```

This uses the mock provider (soft noise generator) instead of real TTS.

## Testing

### Unit Tests

```bash
cd platform/backend
pytest tests/test_tts.py -v
```

### Smoke Test

```powershell
# Start backend with SIMULATE_RENDER=1
cd platform/backend
$env:SIMULATE_RENDER="1"
python -m uvicorn app.main:app --reload

# In another terminal:
cd scripts
.\smoke_tts_hi.ps1
```

## Performance

- **Cold synthesis**: ~2-4 seconds per scene (network call)
- **Cached synthesis**: < 50ms per scene
- **Time-stretching**: ~100-300ms per scene
- **Typical job (5 scenes)**: 3-8 seconds total

## Best Practices

1. **Use short narration**: Keep under 15 words per scene for natural pacing
2. **Match duration**: Set `duration_sec` close to natural speech duration
3. **Preview first**: Use `/tts/preview` to test voice before full render
4. **Cache warming**: Pre-render common phrases for instant retrieval
5. **Error handling**: System auto-falls back to mock on TTS failure

## Example: Complete Workflow

```python
# 1. Preview voice
import requests

preview = requests.post("http://127.0.0.1:8000/tts/preview", json={
    "text": "भोर की पहली किरण",
    "lang": "hi",
    "voice_id": "hi-IN-SwaraNeural"
})
print(f"Preview URL: {preview.json()['url']}")

# 2. Submit render job
render = requests.post("http://127.0.0.1:8000/render", json={
    "language": "hi",
    "voice_id": "hi-IN-SwaraNeural",
    "scenes": [
        {
            "image_prompt": "Temple dawn",
            "narration": "भोर की पहली किरण में मंदिर जागता है।",
            "duration_sec": 5
        }
    ]
})
job_id = render.json()["job_id"]

# 3. Poll status
import time
while True:
    status = requests.get(f"http://127.0.0.1:8000/render/{job_id}/status")
    state = status.json()["state"]
    if state == "success":
        break
    time.sleep(2)

# 4. Access audio
audio_metadata = status.json()["audio"]
print(f"Provider: {audio_metadata['provider']}")
print(f"Duration: {audio_metadata['total_duration_sec']}s")
```

## Support

For issues or questions:
- Check logs: `platform/backend/logs/`
- Run smoke test: `scripts/smoke_tts_hi.ps1`
- Enable debug mode: `export LOG_LEVEL=DEBUG`
