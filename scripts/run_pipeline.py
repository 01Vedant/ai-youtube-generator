"""run_pipeline.py

Orchestrates asset creation from `prahlad_plan.json` into `assets/`:
 - assets/audio/scene_{n}.mp3  (pyttsx3 or ElevenLabs)
 - assets/prompts/scene_{n}_prompt_{engine}.txt
 - assets/images/ (user-provided 4K images)
 - assets/subtitles/scene_{n}.srt
 - assets/assets_map.json

This script does not call external image APIs; it writes prompts ready for engines.
For TTS it uses ElevenLabs if ELEVENLABS_API_KEY env var is set, otherwise pyttsx3.
"""
import os
import json
import re
from pathlib import Path

BASE = Path(__file__).parent
PLAN = BASE / 'prahlad_plan.json'
ASSETS = BASE.parent / 'assets'
PROMPTS = ASSETS / 'prompts'
AUDIO = ASSETS / 'audio'
IMAGES = ASSETS / 'images'
SUBS = ASSETS / 'subtitles'
ASSETS.mkdir(exist_ok=True)
PROMPTS.mkdir(exist_ok=True)
AUDIO.mkdir(exist_ok=True)
IMAGES.mkdir(exist_ok=True)
SUBS.mkdir(exist_ok=True)

def parse_duration(notes: str):
    m = re.search(r"Duration:\s*(\d+)(?:[–-](\d+))?s", notes)
    if m:
        a = int(m.group(1)); b = int(m.group(2)) if m.group(2) else a
        return (a+b)/2.0
    return None

def make_engine_prompts(prompt_text: str):
    openai_prompt = prompt_text + " --ar 16:9 --quality cinematic --vibrant --ultra-detailed --4k"
    sd_prompt = ("<lora:hd_details:0.6> " + prompt_text + ", ultra-detailed, 8k, cinematic lighting, photorealistic painting, Raja Ravi Varma style, Pahari miniature color palette, film grain:0.2")
    runway_prompt = prompt_text + " | cinematic lighting | highly detailed | 4k | semi-realistic | animation-ready"
    luma_notes = "Use as 3D background plate: high-res 4k image, layers for FG/MG/BG, normal map and alpha for cloth/aura. " + prompt_text
    return {'openai': openai_prompt, 'sd': sd_prompt, 'runway': runway_prompt, 'luma': luma_notes}

def write_srt_for_scene(idx: int, text: str, duration: float, out_path: Path):
    # split by sentences, then wrap ~38 chars
    parts = re.split(r'(?<=[।.!?])\s+', text.strip())
    lines = []
    for p in parts:
        words = p.split()
        cur = ''
        for w in words:
            if len(cur) + len(w) + (1 if cur else 0) <= 38:
                cur = (cur + ' ' + w).strip()
            else:
                lines.append(cur); cur = w
        if cur: lines.append(cur)
    if not lines:
        out_path.write_text('')
        return
    per = duration / len(lines)
    t = 0.0
    def ts(t):
        h = int(t//3600); m = int((t%3600)//60); s = int(t%60); ms = int((t-int(t))*1000)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"
    parts_out = []
    idxn = 1
    for l in lines:
        start = ts(t); end = ts(t+per)
        parts_out.append(f"{idxn}\n{start} --> {end}\n{l}\n")
        t += per; idxn += 1
    out_path.write_text('\n'.join(parts_out), encoding='utf-8')

def tts_pyttsx3_save(text, out_path):
    try:
        import pyttsx3
    except Exception as e:
        raise RuntimeError('pyttsx3 not installed') from e
    engine = pyttsx3.init()
    # pick a female-like voice if possible
    try:
        for v in engine.getProperty('voices'):
            name = getattr(v,'name','').lower()
            if 'female' in name or 'zira' in name or 'samantha' in name:
                engine.setProperty('voice', v.id); break
    except Exception:
        pass
    engine.save_to_file(text, str(out_path))
    engine.runAndWait()

def tts_elevenlabs_save(text, out_path, api_key, voice='alloy'):
    # Minimal streaming approach; user must supply ELEVENLABS_API_KEY
    import requests
    url = f'https://api.elevenlabs.io/v1/text-to-speech/{voice}/stream'
    headers = {'xi-api-key': api_key, 'Content-Type':'application/json'}
    payload = {'text': text}
    with requests.post(url, headers=headers, json=payload, stream=True) as r:
        r.raise_for_status()
        with open(out_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk: f.write(chunk)

def main():
    plan = json.loads(PLAN.read_text(encoding='utf-8'))
    eleven_key = os.getenv('ELEVENLABS_API_KEY')
    assets_map = []
    for s in plan:
        idx = s['scene_number']
        vo = s['voiceover']
        notes = s.get('notes','')
        dur = parse_duration(notes) or max(4.0, len(vo.split())/2.7)

        # prompts
        engines = make_engine_prompts(s['image_prompt'])
        prompts_files = {}
        for k,p in engines.items():
            pf = PROMPTS / f'scene_{idx}_prompt_{k}.txt'
            pf.write_text(p, encoding='utf-8'); prompts_files[k]=str(pf)

        # srt
        srt_path = SUBS / f'scene_{idx}.srt'
        write_srt_for_scene(idx, vo, dur, srt_path)

        # tts
        audio_path = AUDIO / f'scene_{idx}.mp3'
        print(f'Generating TTS for scene {idx} -> {audio_path.name}')
            try:
                if not eleven_key:
                    raise RuntimeError('ELEVENLABS_API_KEY is required for TTS; please set it in your environment')
                tts_elevenlabs_save(vo, audio_path, eleven_key)
            except Exception as e:
                print('TTS generation failed for scene', idx, e)

        assets_map.append({'scene': idx, 'title': s.get('scene_title',''), 'prompt_files': prompts_files, 'audio': str(audio_path), 'srt': str(srt_path), 'duration_seconds': round(dur,2)})

    (ASSETS / 'assets_map.json').write_text(json.dumps(assets_map, indent=2, ensure_ascii=False), encoding='utf-8')
    print('Wrote assets_map.json to', ASSETS)

if __name__ == '__main__':
    main()
