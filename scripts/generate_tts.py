"""generate_tts.py

Generates high-quality TTS audio for prahlad_plan.json.

Usage:
  - Provide ELEVENLABS_API_KEY env var to use ElevenLabs (recommended for expressive voices)
  - Otherwise the script falls back to local `pyttsx3` (good for quick tests)

Outputs:
  - MP3 files: `scripts/generated_audio/scene_{n}.mp3`
  - `scripts/tts_assets_map.json` mapping scene -> filename -> duration

Note: This script contains example ElevenLabs API usage. You must add your own API key
and accept ElevenLabs TOS before using it.
"""
import os
import json
from pathlib import Path
import math

BASE = Path(__file__).parent
PLAN = BASE / 'prahlad_plan.json'
OUT_DIR = BASE / 'generated_audio'
OUT_DIR.mkdir(exist_ok=True)

def parse_duration_from_notes(notes: str):
    # Expect formats like "Duration: 8-10s" or "Duration: 10-12s"
    import re
    m = re.search(r"Duration:\s*(\d+)(?:[–-](\d+))?s", notes)
    if m:
        a = int(m.group(1))
        b = int(m.group(2)) if m.group(2) else a
        return (a + b) / 2.0
    return None

def tts_elevenlabs_save(text, out_path, voice_name='alloy', api_key=None):
    # Minimal ElevenLabs example (pseudo-code). Replace with official SDK if available.
    import requests
    url = 'https://api.elevenlabs.io/v1/text-to-speech/' + voice_name + '/stream'
    headers = {
        'xi-api-key': api_key,
        'Content-Type': 'application/json'
    }
    payload = { 'text': text }
    with requests.post(url, headers=headers, json=payload, stream=True) as r:
        r.raise_for_status()
        with open(out_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

def tts_pyttsx3_save(text, out_path):
    import pyttsx3
    engine = pyttsx3.init()
    # Attempt to pick a female-sounding voice if available
    try:
        for v in engine.getProperty('voices'):
            name = getattr(v, 'name', '').lower()
            if 'female' in name or 'zira' in name or 'samantha' in name:
                engine.setProperty('voice', v.id)
                break
    except Exception:
        pass
    engine.save_to_file(text, str(out_path))
    engine.runAndWait()

def main():
    with PLAN.open('r', encoding='utf-8') as f:
        scenes = json.load(f)

    assets = []
    eleven_key = os.getenv('ELEVENLABS_API_KEY') or os.getenv('ELEVENLABS_KEY')

    if not eleven_key:
        raise RuntimeError('ELEVENLABS_API_KEY is required. Please set it in your environment.')

    for s in scenes:
        idx = s['scene_number']
        voice = s['voiceover']
        notes = s.get('notes','')
        dur = parse_duration_from_notes(notes)
        if dur is None:
            # fallback guess: ~2.7 words/sec
            words = len(voice.split())
            dur = max(4.0, words / 2.7)

        out_file = OUT_DIR / f'scene_{idx}.mp3'

        print(f'Generating TTS for scene {idx} -> {out_file.name} (dur ~{dur}s)')

        # Use ElevenLabs only
        tts_elevenlabs_save(voice, out_file, voice_name='alloy', api_key=eleven_key)

        assets.append({ 'scene': idx, 'file': str(out_file), 'duration_seconds': round(dur,2) })

    map_path = BASE / 'tts_assets_map.json'
    map_path.write_text(json.dumps(assets, indent=2, ensure_ascii=False), encoding='utf-8')
    print('Saved tts_assets_map.json')

if __name__ == '__main__':
    main()
