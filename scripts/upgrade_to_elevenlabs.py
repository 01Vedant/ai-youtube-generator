"""upgrade_to_elevenlabs.py

Replace existing pyttsx3 audio with ElevenLabs expressive TTS.

Usage:
  - Set environment variable `ELEVENLABS_API_KEY` with your key
  - Optionally set `ELEVENLABS_VOICE_ID` to a preferred voice id (else uses default)
  - Run: python scripts/upgrade_to_elevenlabs.py

Outputs:
  - Overwrites `assets/audio/scene_{n}.mp3` with ElevenLabs audio
  - Updates `assets/tts_eleven_map.json` with scene -> file -> duration

Note: This script streams audio from ElevenLabs. Do not commit API keys.
"""
import os
import time
import json
from pathlib import Path

BASE = Path(__file__).parent.parent
ASSETS = BASE / 'assets'
ASSETS.mkdir(exist_ok=True)
AUDIO = ASSETS / 'audio'
AUDIO.mkdir(exist_ok=True)
MAP = ASSETS / 'assets_map.json'

ELEVEN_KEY = os.getenv('ELEVENLABS_API_KEY')
VOICE_ID = os.getenv('ELEVENLABS_VOICE_ID', 'alloy')

if not ELEVEN_KEY:
    print('ELEVENLABS_API_KEY not set. Set the env var and re-run.')
    raise SystemExit(1)

def eleven_tts_stream(text, out_path, voice_id=VOICE_ID, api_key=ELEVEN_KEY, max_retries=3):
    import requests
    url = f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream'
    headers = {'xi-api-key': api_key, 'Content-Type': 'application/json'}
    payload = {'text': text}
    for attempt in range(1, max_retries+1):
        try:
            with requests.post(url, headers=headers, json=payload, stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(out_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            return True
        except Exception as e:
            print(f'Attempt {attempt} failed:', e)
            time.sleep(2 * attempt)
    return False

def main():
    if not MAP.exists():
        print('Missing assets_map.json. Run scripts/run_pipeline.py first to create assets_map.json')
        raise SystemExit(1)

    assets = json.loads(MAP.read_text(encoding='utf-8'))
    out_map = []
    for it in assets:
        scene = it['scene']
        # read voiceover from plan
        plan = BASE / 'scripts' / 'prahlad_plan.json'
        plan_data = json.loads(plan.read_text(encoding='utf-8'))
        voice_text = next((s['voiceover'] for s in plan_data if s['scene_number']==scene), None)
        if not voice_text:
            print('No voiceover found for scene', scene); continue

        out_file = AUDIO / f'scene_{scene}.mp3'
        print('Generating ElevenLabs TTS for scene', scene)
        ok = eleven_tts_stream(voice_text, out_file)
        if not ok:
            print('Failed to generate TTS for scene', scene)
            continue

        dur = it.get('duration_seconds') or None
        out_map.append({'scene': scene, 'file': str(out_file), 'duration_seconds': dur})

    (ASSETS / 'tts_eleven_map.json').write_text(json.dumps(out_map, indent=2, ensure_ascii=False), encoding='utf-8')
    print('Wrote tts_eleven_map.json in assets/')

if __name__ == '__main__':
    main()
