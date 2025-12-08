#!/usr/bin/env python3
"""
Decode the base64 payload inside placeholder_silent.mp3 (if present) and overwrite the file with real MP3 binary.
Usage: python tools/decode_silent_mp3.py
"""
import re
import base64
from pathlib import Path

p = Path('platform/frontend/public/static/placeholders/placeholder_silent.mp3')
if not p.exists():
    print('File not found:', p)
    raise SystemExit(2)

text = p.read_text(encoding='utf-8', errors='ignore')
# Remove C-style comments and lines starting with //
lines = []
for line in text.splitlines():
    s = line.strip()
    if not s:
        continue
    if s.startswith('//'):
        continue
    # If line looks like base64 (contains only base64 chars), keep
    lines.append(s)

candidate = ''.join(lines)
# Remove any non-base64 characters (keep A-Za-z0-9+/=)
candidate = re.sub(r'[^A-Za-z0-9+/=]', '', candidate)

if len(candidate) < 20:
    print('No base64 payload found (length < 20). Aborting.')
    raise SystemExit(3)

try:
    data = base64.b64decode(candidate, validate=True)
except Exception as e:
    print('Base64 decode failed:', e)
    # try padding
    pad = '=' * ((4 - len(candidate) % 4) % 4)
    try:
        data = base64.b64decode(candidate + pad)
        print('Decoded with padding')
    except Exception as e2:
        print('Retry decode failed:', e2)
        raise

# Basic sanity check: MP3 typically contains 'ID3' or frame headers 0xfffb
if not (data.startswith(b'ID3') or data[0] == 0xff):
    print('Warning: decoded bytes do not look like an MP3 (no ID3 or frame header). Proceeding anyway.')

# Overwrite file with binary
p.write_bytes(data)
print('Wrote', p, 'length=', p.stat().st_size)

# Print first 16 bytes hex for inspection
print('First 16 bytes:', data[:16].hex())
