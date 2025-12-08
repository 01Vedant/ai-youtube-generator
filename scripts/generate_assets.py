import json
import re
from pathlib import Path

# Simple utility to parse duration like "Duration: 8-10s" or "Duration: 10-12s"
def parse_duration(notes):
    m = re.search(r"Duration:\s*(\d+)(?:[–-](\d+))?s", notes)
    if m:
        a = int(m.group(1))
        b = int(m.group(2)) if m.group(2) else a
        return (a + b) / 2.0
    # fallback: estimate from word count (~160 wpm)
    return None

def split_subtitle_lines(text, max_chars=40):
    words = text.strip().split()
    lines = []
    cur = []
    cur_len = 0
    for w in words:
        if cur_len + len(w) + (1 if cur else 0) <= max_chars:
            cur.append(w)
            cur_len += len(w) + (1 if cur_len else 0)
        else:
            lines.append(" ".join(cur))
            cur = [w]
            cur_len = len(w)
    if cur:
        lines.append(" ".join(cur))
    return lines

def seconds_to_srt_timestamp(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    ms = int((t - int(t)) * 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def write_srt(scene_idx, voice_text, duration, out_path):
    # Split into subtitle blocks by sentences first, then wrap lines
    # Very simple sentence split by punctuation
    sentences = re.split(r'(?<=[।.!?])\s+', voice_text.strip())
    lines = []
    for s in sentences:
        for l in split_subtitle_lines(s, max_chars=40):
            lines.append(l)

    # Distribute time evenly across subtitle lines
    if duration is None:
        duration = max(4.0, len(voice_text.split()) / 3.0)  # fallback seconds

    per_line = duration / max(1, len(lines))

    srt_lines = []
    cur_t = 0.0
    idx = 1
    for l in lines:
        start = cur_t
        end = cur_t + per_line
        srt_lines.append(f"{idx}\n{seconds_to_srt_timestamp(start)} --> {seconds_to_srt_timestamp(end)}\n{l}\n")
        cur_t = end
        idx += 1

    out_path.write_text("\n".join(srt_lines), encoding="utf-8")

def main():
    base = Path(__file__).parent
    plan_path = base / "prahlad_plan.json"
    out_audio_dir = base / "generated_audio"
    out_audio_dir.mkdir(exist_ok=True)

    with plan_path.open("r", encoding="utf-8") as f:
        scenes = json.load(f)

    # Use ElevenLabs for TTS (required).
    import os
    eleven_key = os.getenv('ELEVENLABS_API_KEY') or os.getenv('ELEVENLABS_KEY')
    if not eleven_key:
        raise RuntimeError('ELEVENLABS_API_KEY required for TTS. Please set it in your environment.')

    assets_map = []

    for s in scenes:
        idx = s.get('scene_number')
        voice = s.get('voiceover', '').strip()
        notes = s.get('notes', '')

        # parse duration
        dur = parse_duration(notes)
        if dur is None:
            # estimate ~ 160 wpm ~ 2.67 words/sec -> duration = words/2.67
            words = len(voice.split())
            dur = max(4.0, words / 2.7)

        # Save prompt
        prompt_file = base / f"scene_{idx}_prompt.txt"
        prompt_file.write_text(s.get('image_prompt', ''), encoding='utf-8')

        # Save TTS audio via ElevenLabs
        audio_file = out_audio_dir / f"scene_{idx}.mp3"
        from requests import post
        url = 'https://api.elevenlabs.io/v1/text-to-speech/alloy/stream'
        headers = {'xi-api-key': eleven_key, 'Content-Type': 'application/json'}
        payload = {'text': voice, 'model_id': 'eleven_multilingual_v2', 'voice_settings': {'stability':0.35, 'similarity_boost':0.7}}
        with post(url, json=payload, headers=headers, stream=True) as r:
            r.raise_for_status()
            with open(audio_file, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

        # Save SRT
        srt_file = base / f"scene_{idx}.srt"
        write_srt(idx, voice, dur, srt_file)

        assets_map.append({
            'scene': idx,
            'title': s.get('scene_title', ''),
            'prompt': str(prompt_file),
            'audio': str(audio_file),
            'srt': str(srt_file),
            'duration_seconds': round(dur, 2)
        })

    # All ElevenLabs TTS files written synchronously above

    # Save assets map
    (base / 'assets_map.json').write_text(json.dumps(assets_map, indent=2, ensure_ascii=False), encoding='utf-8')

    print('Generated prompts, kicked off TTS (saved to generated_audio), and created SRTs.')

if __name__ == '__main__':
    main()
