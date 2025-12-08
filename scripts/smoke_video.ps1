# Requires: PowerShell, Python, ffmpeg in PATH
$ErrorActionPreference = "Stop"

python scripts/preflight.py

# Create temp and output dirs
New-Item -ItemType Directory -Force -Path "scripts/_tmp/imgs" | Out-Null
New-Item -ItemType Directory -Force -Path "scripts/_out" | Out-Null

# Create 3 solid-color PNGs via Python + Pillow
$py = @"
from PIL import Image
from pathlib import Path
out = Path('scripts/_tmp/imgs')
out.mkdir(parents=True, exist_ok=True)
colors = [(255,0,0), (0,255,0), (0,0,255)]
for i, c in enumerate(colors, start=1):
    img = Image.new('RGB', (640, 360), c)
    img.save(out / f"img_{i}.png")
print('Generated test PNGs')
"@
$pyPath = "scripts/_tmp/gen_imgs.py"
$py | Out-File -FilePath $pyPath -Encoding UTF8
python $pyPath

# Generate 2-second sine-wave MP3 via ffmpeg
ffmpeg -hide_banner -loglevel error -f lavfi -i "sine=frequency=440:duration=2" -q:a 3 "scripts/_tmp/tone.mp3" -y

# Compose video
python scripts/generate_video.py --audio "scripts/_tmp/tone.mp3" --images "scripts/_tmp/imgs" --output "scripts/_out/smoke.mp4" --seconds 1.5

# Verify output non-empty
if ((Test-Path "scripts/_out/smoke.mp4") -and ((Get-Item "scripts/_out/smoke.mp4").Length -gt 0)) {
  Write-Output "SMOKE OK"
} else {
  Write-Error "Smoke output missing or empty"; exit 3
}

# Cleanup temp files
Remove-Item -Recurse -Force "scripts/_tmp"
