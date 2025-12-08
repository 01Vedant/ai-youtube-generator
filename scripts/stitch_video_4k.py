"""stitch_video_4k.py

Stitches scene images, audio and subtitles into a single 4K (3840x2160) MP4.

Requirements:
 - MoviePy 2.x, imageio-ffmpeg
 - Provide per-scene images as `scripts/scene_{n}.png` (recommended 3840x2160 or larger)
 - TTS audio: `scripts/generated_audio/scene_{n}.mp3`
 - Subtitles: `scripts/scene_{n}.srt`

This script applies:
 - Center-crop / letterbox to 3840x2160
 - Gentle Ken-Burns zoom (1.03x) and slow pan where notes suggest
 - Subtitle overlay using TextClip
 - Crossfade between scenes
 - Writes `scripts/Prahlad_Final_4K.mp4`
"""
from pathlib import Path
import json
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
from moviepy.video.fx import resize
from moviepy.video.compositing import CompositeVideoClip
import moviepy.video.fx.all as vfx

BASE = Path(__file__).parent
ASSETS = BASE / 'assets_map.json'
OUT = BASE / 'Prahlad_Final_4K.mp4'
TARGET_W, TARGET_H = 3840, 2160

def center_crop_resize(imgclip, w=TARGET_W, h=TARGET_H):
    # Resize maintaining aspect, then crop center to w,h
    iw, ih = imgclip.size
    scale = max(w/iw, h/ih)
    clip = imgclip.resize(scale)
    # crop center
    return clip.crop(x_center=clip.w/2, y_center=clip.h/2, width=w, height=h)

def apply_ken_burns(clip, zoom=1.03):
    # scale gradually from 1.0 to zoom
    return clip.fx(vfx.resize, lambda t: 1 + (zoom-1)*(t/clip.duration))

def read_srt_entries(srt_path: Path):
    if not srt_path.exists():
        return []
    s = srt_path.read_text(encoding='utf-8')
    parts = [p.strip() for p in s.split('\n\n') if p.strip()]
    out = []
    for p in parts:
        lines = p.splitlines()
        if len(lines) >= 2:
            times = lines[1]
            t0, t1 = [t.strip() for t in times.split('-->')]
            def ts2s(ts):
                hh,mm,rest = ts.split(':')
                ss,ms = rest.split(',')
                return int(hh)*3600 + int(mm)*60 + int(ss) + int(ms)/1000.0
            text = '\n'.join(lines[2:])
            out.append((ts2s(t0), ts2s(t1), text))
    return out

def create_subtitle_clips(srt_entries, w, h):
    from moviepy.video.VideoClip import TextClip
    clips = []
    for start, end, text in srt_entries:
        txt = TextClip(text, fontsize=80, font='Arial', color='white', method='label')
        txt = txt.set_start(start).set_duration(max(0.1, end-start)).set_position(('center', h - 250))
        clips.append(txt)
    return clips

def main():
    if not ASSETS.exists():
        print('Missing assets_map.json — run generate_assets.py first to produce assets_map.json')
        return
    assets = json.loads(ASSETS.read_text(encoding='utf-8'))
    scene_clips = []

    for it in assets:
        idx = it['scene']
        # prefer high-res scene_{n}.png
        img_candidates = [BASE / f'scene_{idx}.png', BASE / f'scene_{idx}.jpg', BASE / f'scene_{idx}.jpeg']
        img = next((p for p in img_candidates if p.exists()), None)
        if img is None:
            # fallback to images folder
            imgs = list((BASE / 'images').glob('*'))
            img = imgs[(idx-1) % len(imgs)] if imgs else None

        dur = float(it.get('duration_seconds', 8.0))

        if img:
            clip = ImageClip(str(img)).with_duration(dur)
            clip = center_crop_resize(clip, TARGET_W, TARGET_H)
        else:
            from moviepy.video.VideoClip import ColorClip
            clip = ColorClip((TARGET_W, TARGET_H), color=(20,20,30)).with_duration(dur)

        clip = apply_ken_burns(clip, zoom=1.03)

        audio_path = BASE / it['audio'] if it.get('audio') else None
        if audio_path and Path(audio_path).exists():
            audio = AudioFileClip(str(audio_path))
            clip = clip.with_audio(audio).with_duration(audio.duration)

        # subtitles overlay
        srt_path = BASE / f'scene_{idx}.srt'
        srt_entries = read_srt_entries(srt_path)
        if srt_entries:
            subs = create_subtitle_clips(srt_entries, clip.w, clip.h)
            clip = CompositeVideoClip([clip, *subs])

        scene_clips.append(clip)

    if not scene_clips:
        print('No scene clips available — aborting')
        return

    # crossfade concatenate
    final = concatenate_videoclips(scene_clips, method='compose')
    print('Rendering final 4K video — this may take time')
    final.write_videofile(str(OUT), fps=30, codec='libx264', audio_codec='aac', bitrate='20M')
    final.close()
    print('Wrote', OUT)

if __name__ == '__main__':
    main()
