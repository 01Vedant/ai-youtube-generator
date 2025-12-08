"""generate_srt_from_plan.py

Generates per-scene .srt subtitle files from `prahlad_plan.json` using the durations in notes.
Each SRT starts at 00:00:00 and runs for scene duration (so each file is self-contained per scene).
"""
import json
import re
from pathlib import Path

BASE = Path(__file__).parent
PLAN = BASE / 'prahlad_plan.json'

def parse_duration(notes: str):
    m = re.search(r"Duration:\s*(\d+)(?:[–-](\d+))?s", notes)
    if m:
        a = int(m.group(1)); b = int(m.group(2)) if m.group(2) else a
        return (a+b)/2.0
    return None

def wrap_text(text, max_chars=38):
    words = text.strip().split()
    lines = []
    cur = ''
    for w in words:
        if len(cur) + len(w) + (1 if cur else 0) <= max_chars:
            cur = (cur + ' ' + w).strip()
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines

def seconds_to_ts(t):
    h = int(t//3600); m = int((t%3600)//60); s = int(t%60); ms = int((t-int(t))*1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def make_srt(text, duration):
    # split by sentences, then wrap
    parts = re.split(r'(?<=[।.!?])\s+', text.strip())
    lines = []
    for p in parts:
        wrapped = wrap_text(p)
        for w in wrapped:
            lines.append(w)

    if len(lines) == 0:
        return ''
    per = duration / len(lines)

    srt = []
    t = 0.0
    idx = 1
    for l in lines:
        start = t; end = t+per
        srt.append(f"{idx}\n{seconds_to_ts(start)} --> {seconds_to_ts(end)}\n{l}\n")
        t = end; idx += 1
    return '\n'.join(srt)

def main():
    scenes = json.loads(PLAN.read_text(encoding='utf-8'))
    for s in scenes:
        idx = s['scene_number']
        text = s['voiceover']
        notes = s.get('notes','')
        dur = parse_duration(notes)
        if dur is None:
            dur = max(4.0, len(text.split())/2.7)
        srt_content = make_srt(text, dur)
        (BASE / f'scene_{idx}.srt').write_text(srt_content, encoding='utf-8')
    print('Generated scene_{n}.srt files')

if __name__ == '__main__':
    main()
