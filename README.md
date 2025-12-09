[![CI](https://github.com/01Vedant/ai-youtube-generator/actions/workflows/ci.yml/badge.svg)](https://github.com/01Vedant/ai-youtube-generator/actions/workflows/ci.yml)


# BhaktiGen

## Video Pipeline Quickcheck

Requires `ffmpeg` in PATH.

```
pip install -r scripts/requirements.txt
python scripts/preflight.py
bash scripts/smoke_video.sh   # macOS/Linux
# or on Windows:
pwsh scripts/smoke_video.ps1
```

On success, you should see `SMOKE OK` and a non-empty file at `scripts/_out/smoke.mp4`.
