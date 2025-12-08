"""finalize_subtitles.py

Load `assets/assets_map.json` and per-scene SRT files, ensure each .srt is wrapped
to 32-40 chars per line and that total SRT duration matches audio duration. Outputs
cleaned SRTs back to `assets/subtitles/` and writes `assets/subtitles_map.json`.
"""
import json
import re
from pathlib import Path

BASE = Path(__file__).parent.parent
ASSETS = BASE / 'assets'
SUBS = ASSETS / 'subtitles'
MAP = ASSETS / 'assets_map.json'

def wrap_lines(text, max_chars=38):
    words = text.strip().split()
    lines = []
    cur = ''
    for w in words:
        if len(cur) + len(w) + (1 if cur else 0) <= max_chars:
            cur = (cur + ' ' + w).strip()
        else:
            lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines

def seconds_to_ts(t):
    h = int(t//3600); m = int((t%3600)//60); s = int(t%60); ms = int((t-int(t))*1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def process_scene(scene_entry):
    idx = scene_entry['scene']
    srt_path = SUBS / f'scene_{idx}.srt'
    if not srt_path.exists():
        print('Missing', srt_path); return None

    text = srt_path.read_text(encoding='utf-8')
    # rebuild from voiceover in plan for consistent splitting
    plan = BASE / 'scripts' / 'prahlad_plan.json'
    plan_data = json.loads(plan.read_text(encoding='utf-8'))
    voice = next((p['voiceover'] for p in plan_data if p['scene_number']==idx), '')

    dur = scene_entry.get('duration_seconds') or max(4.0, len(voice.split())/2.7)
    # split sentences then wrap
    parts = re.split(r'(?<=[।.!?])\s+', voice.strip())
    lines = []
    for p in parts:
        lines.extend(wrap_lines(p, max_chars=38))

    per = dur / max(1, len(lines))
    out = []
    t = 0.0
    idxn = 1
    for l in lines:
        start = seconds_to_ts(t); end = seconds_to_ts(t+per)
        out.append(f"{idxn}\n{start} --> {end}\n{l}\n")
        t += per; idxn += 1

    srt_path.write_text('\n'.join(out), encoding='utf-8')
    return {'scene': idx, 'srt': str(srt_path), 'duration_seconds': round(dur,2)}

def main():
    if not MAP.exists():
        print('Run run_pipeline.py first to create assets_map.json')
        return
    assets = json.loads(MAP.read_text(encoding='utf-8'))
    out_map = []
    for it in assets:
        entry = process_scene(it)
        if entry: out_map.append(entry)

    (ASSETS / 'subtitles_map.json').write_text(json.dumps(out_map, indent=2, ensure_ascii=False), encoding='utf-8')
    print('Wrote subtitles_map.json')

if __name__ == '__main__':
    main()
