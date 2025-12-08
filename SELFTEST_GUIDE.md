# Bhakti Video Generator - Self-Test Guide

## ✨ Auto-Configuration

The backend now **automatically configures itself** on startup:

- 🔍 **Auto-detects FFmpeg** in PATH or common locations
- 🎬 **Checks encoder support** (NVENC GPU / libx264 CPU)
- 🔄 **Auto-selects mode**:
  - `SIMULATE_RENDER=0` if FFmpeg with encoders found
  - `SIMULATE_RENDER=1` if FFmpeg missing (fallback to simulator)
- 📊 **Prints detailed report** on startup

## 🧪 Running Self-Tests

### Option 1: Standalone Python Script (No Server Required)

Run directly from VS Code or terminal:

```bash
# From project root
python run_selftest.py
```

This will:
- Detect your environment (FFmpeg, encoders)
- Run simulator self-test
- Validate orchestrator, status tracking, file generation
- Print comprehensive report

### Option 2: API Endpoint (Server Running)

1. **Start the server** (it auto-configures on startup):
   ```bash
   cd platform/backend
   python -m uvicorn app.main:app --reload
   ```

2. **Call the self-test endpoint**:
   ```bash
   # From browser or Postman
   http://127.0.0.1:8000/render/selftest
   
   # Or with curl/PowerShell
   Invoke-RestMethod http://127.0.0.1:8000/render/selftest
   ```

### Option 3: VS Code "Run Python File"

1. Open `run_selftest.py` in VS Code
2. Click the ▶️ **Run Python File** button in top right
3. View results in the integrated terminal

## 📋 What Gets Tested

### Simulator Mode (SIMULATE_RENDER=1)
- ✅ Plan creation and validation
- ✅ Orchestrator initialization
- ✅ Status callback progression (6+ updates expected)
- ✅ File generation (job_summary.json, assets)
- ✅ Asset count (4+ expected: image, audio, 2x subtitles)
- ✅ Final video URL presence
- ✅ JSON structure validation

### Real Mode (SIMULATE_RENDER=0, requires FFmpeg)
- ✅ FFmpeg availability and version
- ✅ Encoder support (NVENC GPU vs libx264 CPU)
- ✅ Test asset creation (tiny PNG, WAV)
- ✅ Actual video rendering (1-second test)
- ✅ Output file validation
- ✅ Timing measurements

## 📊 Environment Report

On startup, you'll see:

```
======================================================================
BHAKTI VIDEO GENERATOR - ENVIRONMENT REPORT
======================================================================

📹 FFmpeg Detection:
  ✅ Found: C:\ffmpeg\bin\ffmpeg.exe
  📦 Version: 6.0

🎬 Video Encoders:
  ✅ h264_nvenc (NVIDIA GPU acceleration)
  ✅ libx264 (CPU encoding)

💾 Filesystem:
  ✅ pipeline_outputs/ writable
  📁 Platform root: C:\...\platform

⚙️  Render Mode:
  🎯 Selected: REAL (production)
  💡 Reason: FFmpeg with encoders detected
  
======================================================================
```

## 🔧 Forcing a Specific Mode

Override auto-detection:

```bash
# Force simulator mode (even if FFmpeg available)
$env:SIMULATE_RENDER="1"
python -m uvicorn app.main:app --reload

# Force real mode (will fail if FFmpeg missing)
$env:SIMULATE_RENDER="0"
python -m uvicorn app.main:app --reload
```

## 🐛 Troubleshooting

### "FFmpeg not found"
- Install FFmpeg: https://ffmpeg.org/download.html
- Add to PATH or place in: `C:\ffmpeg\bin\`
- Restart terminal/VS Code after installation

### "NVENC not available"
- NVENC requires NVIDIA GPU (GTX 600+, RTX series)
- Will automatically fall back to libx264 (CPU encoding)
- CPU encoding is slower but works on all systems

### "Output directory not writable"
- Check `platform/pipeline_outputs/` exists
- Verify write permissions
- Run from project root directory

## 📁 Project Structure

```
ai-youtube-generator/
├── run_selftest.py          # ← Run this for standalone test
├── platform/
│   ├── backend/
│   │   └── app/
│   │       ├── main.py       # Auto-configures on startup
│   │       └── env_detector.py  # Environment detection
│   ├── orchestrator.py       # Simulator + selftest
│   ├── routes/
│   │   └── render.py         # /selftest endpoint
│   └── pipeline/
│       └── video_renderer.py # Real renderer + selftest
```

## 🚀 Quick Start

1. **Just run the server** - it auto-configures:
   ```bash
   cd platform/backend
   python -m uvicorn app.main:app --reload
   ```

2. **Check the startup report** in console

3. **Visit** http://127.0.0.1:8000/docs for API documentation

4. **Test** http://127.0.0.1:8000/render/selftest

That's it! No manual configuration needed.
