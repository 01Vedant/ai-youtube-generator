#!/usr/bin/env bash
set -euo pipefail

python scripts/preflight.py

mkdir -p scripts/_tmp/imgs scripts/_out

# Create 3 solid-color PNGs using Python + Pillow
python - <<'PY'
from PIL import Image
from pathlib import Path
out = Path('scripts/_tmp/imgs')
out.mkdir(parents=True, exist_ok=True)
colors = [(255,0,0), (0,255,0), (0,0,255)]
for i, c in enumerate(colors, start=1):
    img = Image.new('RGB', (640, 360), c)
    img.save(out / f"img_{i}.png")
print("Generated test PNGs")
PY

# Generate 2-second sine-wave MP3 via ffmpeg
ffmpeg -hide_banner -loglevel error -f lavfi -i "sine=frequency=440:duration=2" -q:a 3 scripts/_tmp/tone.mp3 -y

# Compose video
python scripts/generate_video.py --audio scripts/_tmp/tone.mp3 --images scripts/_tmp/imgs --output scripts/_out/smoke.mp4 --seconds 1.5

# Verify output non-empty
if [ -s scripts/_out/smoke.mp4 ]; then
  echo "SMOKE OK"
else
  echo "Smoke output missing or empty" >&2
  exit 3
fi

# Cleanup temp files
rm -rf scripts/_tmp
