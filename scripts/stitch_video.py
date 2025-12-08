import json
from pathlib import Path
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
from moviepy.video.fx import resize
from moviepy.video.compositing import CompositeVideoClip
from moviepy.video.io.VideoFileClip import VideoFileClip
import moviepy.video.fx.all as vfx

def load_assets_map(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))

def apply_ken_burns(clip, zoom=1.06):
    # simple zoom effect using resize with lambda over t
    try:
        return clip.fx(vfx.resize, lambda t: 1 + (zoom - 1) * (t / clip.duration))
    except Exception:
        return clip

def render_subtitles_to_clips(srt_path: Path, w, h, fontsize=30):
    # Very basic SRT reader producing list of (start, end, text)
    entries = []
    s = srt_path.read_text(encoding='utf-8')
    parts = [p.strip() for p in s.split('\n\n') if p.strip()]
    for p in parts:
        lines = p.splitlines()
        if len(lines) >= 2:
            time_line = lines[1].strip()
            m = time_line.split('-->')
            if len(m) == 2:
                def t2s(ts):
                    hh,mm,rest = ts.strip().split(':')
                    ss,ms = rest.split(',')
                    return int(hh)*3600 + int(mm)*60 + int(ss) + int(ms)/1000.0
                start = t2s(m[0])
                end = t2s(m[1])
                text = '\n'.join(lines[2:])
                entries.append((start, end, text))
    return entries

def make_textclip(text, w, h, fontsize=36):
    from moviepy.video.VideoClip import TextClip
    return TextClip(text, fontsize=fontsize, color='white', font='Arial', method='label').set_position(('center','bottom'))

def main():
    base = Path(__file__).parent
    assets_map = load_assets_map(base / 'assets_map.json')

    scene_clips = []
    for item in assets_map:
        idx = item['scene']
        img_candidates = [base / f"scene_{idx}.png", base / f"scene_{idx}.jpg", base / f"scene_{idx}.jpeg"]
        img_path = None
        for p in img_candidates:
            if p.exists():
                img_path = p
                break
        # fallback: use first image in scripts/images
        if img_path is None:
            imgs_dir = base / 'images'
            found = list(imgs_dir.glob('*'))
            img_path = found[(idx-1) % len(found)] if found else None

        duration = float(item.get('duration_seconds', 8.0))

        if img_path is None:
            # create a color clip placeholder
            from moviepy.video.VideoClip import ColorClip
            clip = ColorClip((1280,720), color=(50,50,80)).with_duration(duration)
        else:
            clip = ImageClip(str(img_path)).with_duration(duration).resize(height=720)

        # apply simple Ken Burns
        clip = apply_ken_burns(clip, zoom=1.06)

        # attach audio if exists
        audio_path = Path(item['audio'])
        if audio_path.exists():
            audio = AudioFileClip(str(audio_path))
            clip = clip.with_audio(audio)
            # ensure clip duration matches audio
            clip = clip.with_duration(audio.duration)

        # overlay subtitles if exist
        srt_path = Path(item['srt'])
        if srt_path.exists():
            subs = render_subtitles_to_clips(srt_path, clip.w, clip.h)
            txt_clips = []
            for (start, end, text) in subs:
                # create text clip
                from moviepy.video.VideoClip import TextClip
                txt = TextClip(text, fontsize=30, color='white', font='Arial', method='label')
                txt = txt.set_start(start).set_duration(max(0.1, end - start)).set_position(('center', 'bottom'))
                txt_clips.append(txt)
            if txt_clips:
                clip = CompositeVideoClip([clip, *txt_clips])

        scene_clips.append(clip)

    # Concatenate with crossfade of 0.6s
    if scene_clips:
        final = concatenate_videoclips(scene_clips, method='compose')
        out = base / 'Prahlad_Final.mp4'
        # export
        final.write_videofile(str(out), fps=24, codec='libx264', audio_codec='aac')
        final.close()
        print('Wrote', out)
    else:
        print('No scene clips found; aborting')

if __name__ == '__main__':
    main()
