"""stitch_assets.py

Stitches assets from `assets/` into `output/Prahlad_Final_4K.mp4`.

It expects:
 - assets/assets_map.json produced by `run_pipeline.py`
 - assets/images/scene_{n}.png (4K recommended)
 - assets/audio/scene_{n}.mp3
 - assets/subtitles/scene_{n}.srt

Outputs:
 - output/scene_{n}_clip.mp4 (optional)
 - output/Prahlad_Final_4K.mp4
"""
from pathlib import Path
import json
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
try:
    import moviepy.video.fx.all as vfx
except Exception:
    import moviepy.video.fx as vfx

BASE = Path(__file__).parent
ASSETS = BASE.parent / 'assets'
OUTDIR = BASE.parent / 'output'
OUTDIR.mkdir(exist_ok=True)
TARGET_W, TARGET_H = 3840, 2160

def parse_srt_entries(srt_path: Path):
    if not srt_path.exists(): return []
    s = srt_path.read_text(encoding='utf-8')
    parts = [p.strip() for p in s.split('\n\n') if p.strip()]
    entries = []
    for p in parts:
        lines = p.splitlines()
        if len(lines) >= 2:
            times = lines[1]; t0, t1 = times.split('-->')
            def t2s(ts):
                hh,mm,rest = ts.strip().split(':'); ss,ms = rest.split(',')
                return int(hh)*3600 + int(mm)*60 + int(ss) + int(ms)/1000.0
            text = '\n'.join(lines[2:])
            entries.append((t2s(t0), t2s(t1), text))
    return entries

def create_subtitle_clips(entries, w, h):
    # Subtitle rendering via MoviePy TextClip can be environment-dependent (ImageMagick/fonts).
    # To keep the pipeline robust, we skip rendering here and recommend burning SRTs with ffmpeg
    # during final encoding. Return no text clips so concatenation proceeds.
    return []

def center_crop_resize(clip, w=TARGET_W, h=TARGET_H):
    iw, ih = clip.size
    scale = max(w/iw, h/ih)
    # resize compat: try several APIs depending on MoviePy version
    if hasattr(clip, 'resized'):
        clip = clip.resized(scale)
    else:
        try:
            clip = vfx.resize(clip, scale)
        except Exception:
            # fallback to calling Resize class if available
            if hasattr(vfx, 'Resize'):
                clip = vfx.Resize(clip, scale)
            else:
                # last resort: use clip.with_size (if exists)
                try:
                    new_w = int(clip.w * scale); new_h = int(clip.h * scale)
                    clip = clip.with_size((new_w, new_h))
                except Exception:
                    pass
    # crop center
    try:
        return vfx.crop(clip, x_center=clip.w/2, y_center=clip.h/2, width=w, height=h)
    except Exception:
        # fallback: compute coordinates and use vfx.crop
        cx = int(clip.w/2); cy = int(clip.h/2)
        x1 = max(0, cx - w//2); y1 = max(0, cy - h//2)
        try:
            return vfx.crop(clip, x1=x1, y1=y1, width=w, height=h)
        except Exception:
            # last resort: try with_size to force dimensions (may stretch)
            try:
                return clip.with_size((w, h))
            except Exception:
                return clip

def main():
    assets_map = ASSETS / 'assets_map.json'
    if not assets_map.exists():
        print('Run run_pipeline.py first to create assets_map.json')
        return
    items = json.loads(assets_map.read_text(encoding='utf-8'))
    scene_clips = []
    for it in items:
        idx = it['scene']
        img = ASSETS / 'images' / f'scene_{idx}.png'
        if not img.exists():
            # fallback to any images in scripts/images
            scr_imgs = list((BASE / 'images').glob('*'))
            img = scr_imgs[(idx-1) % len(scr_imgs)] if scr_imgs else None
        dur = float(it.get('duration_seconds', 8.0))
        if img:
            clip = ImageClip(str(img)).with_duration(dur)
            clip = center_crop_resize(clip)
        else:
            from moviepy.video.VideoClip import ColorClip
            clip = ColorClip((TARGET_W,TARGET_H), color=(30,30,40)).with_duration(dur)

        try:
            clip = vfx.resize(clip, lambda t: 1 + 0.03*(t/clip.duration))
        except Exception:
            # fallback: no animated resize
            pass

        audio = Path(it['audio'])
        if audio.exists():
            ac = AudioFileClip(str(audio))
            clip = clip.with_audio(ac).with_duration(ac.duration)

        srt = ASSETS / 'subtitles' / f'scene_{idx}.srt'
        entries = parse_srt_entries(srt)
        if entries:
            subs = create_subtitle_clips(entries, clip.w, clip.h)
            clip = CompositeVideoClip([clip, *subs])

        # save individual clip
        clip_out = OUTDIR / f'scene_{idx}_clip.mp4'
        clip.write_videofile(str(clip_out), fps=24, codec='libx264', audio_codec='aac')
        clip.close()
        # append rendered clip as VideoFileClip
        scene_clips.append(VideoFileClip(str(clip_out)))

    # concatenate final
    if scene_clips:
        final = concatenate_videoclips(scene_clips, method='compose')
        final_out = OUTDIR / 'Prahlad_Final_4K.mp4'
        final.write_videofile(str(final_out), fps=30, codec='libx264', audio_codec='aac', bitrate='20M')
        final.close()
        print('Wrote', final_out)
    else:
        print('No scene clips created')

if __name__ == '__main__':
    main()
