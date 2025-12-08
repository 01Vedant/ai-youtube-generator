Automation README — Prahlad devotional video pipeline

Overview
--------
This repository contains a pipeline to convert `scripts/prahlad_plan.json` into a cinematic devotional video.

Files created:
- `scripts/prahlad_plan.json` — scene plan
- `scripts/generate_tts.py` — TTS generator (ElevenLabs if `ELEVENLABS_API_KEY` set, else `pyttsx3`)
- `scripts/generate_images.py` — writes engine-specific image prompts (OpenAI/SD/Runway/Luma)
- `scripts/generate_srt_from_plan.py` — create per-scene `.srt` subtitle files
- `scripts/stitch_video_4k.py` — stitches all assets into `scripts/Prahlad_Final_4K.mp4`
- `requirements.txt`

Quick setup (Windows PowerShell)
1) Create and activate venv (recommended)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

2) Generate prompts and subtitle files
```powershell
python scripts/generate_images.py
python scripts/generate_srt_from_plan.py
```

3) Generate TTS audio
- Option A (recommended): set `ELEVENLABS_API_KEY` env var and run:
```powershell
$env:ELEVENLABS_API_KEY = 'your_key_here'
python scripts/generate_tts.py
```
- Option B (local): no env var needed, the script falls back to `pyttsx3`.

4) Generate or create images
- Use the files `scripts/scene_{n}_prompt_openai.txt` or `_sd.txt` etc. as input to your preferred image service.
- Save final images as `scripts/scene_{n}.png` (recommended resolution: 3840x2160 or higher).

5) Stitch video into 4K
```powershell
python scripts/stitch_video_4k.py
```

Notes / Tips
- ElevenLabs voice produces the best expressive TTS; choose an Indian female voice if available.
- For subtitles, MoviePy's `TextClip` may require ImageMagick on some systems; if you hit issues, either install ImageMagick or use ffmpeg-based burning.
- Particle overlays and animated auras: provide small loopable video files (e.g., `scripts/overlays/particles.mp4`) and composite them in `stitch_video_4k.py` near the top of the main loop (not added automatically).

Security
- Do NOT commit API keys. Use environment variables for all secrets.
