#!/usr/bin/env python3
"""
Generate a 1-second silent MP3 and overwrite the placeholder file.

Steps:
- Check that `ffmpeg` is available on PATH. If not, raise an informative error.
- Create a 1.0s silent WAV (PCM16, 44.1kHz, mono) using the stdlib `wave` module.
- Use `ffmpeg` to transcode the WAV to MP3 (libmp3lame, 64k bitrate).
- Overwrite `platform/frontend/public/static/placeholders/placeholder_silent.mp3` with the MP3 binary.
- Verify file size and duration using `ffprobe` if available, otherwise parse `ffmpeg -i` output.

Idempotent: running multiple times will recreate the same silent MP3.
"""
import shutil
import subprocess
import sys
from pathlib import Path
import wave
import struct
import tempfile


TARGET = Path('platform/frontend/public/static/placeholders/placeholder_silent.mp3')


def check_ffmpeg():
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        raise SystemExit('ffmpeg not found on PATH. Please install ffmpeg and ensure it is available in your PATH.')
    return ffmpeg


def generate_silent_wav(path: Path, duration_s: float = 1.0, rate: int = 44100):
    # PCM16 mono
    nchannels = 1
    sampwidth = 2  # bytes
    nframes = int(duration_s * rate)

    with wave.open(str(path), 'wb') as wf:
        wf.setnchannels(nchannels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(rate)
        # write nframes of silence (zeros)
        silence_frame = struct.pack('<h', 0)  # 16-bit PCM little-endian zero
        wf.writeframes(silence_frame * nframes)


def transcode_to_mp3(ffmpeg_path: str, wav_path: Path, out_path: Path):
    # Use libmp3lame with modest bitrate to keep size small but compatible
    cmd = [ffmpeg_path, '-y', '-hide_banner', '-loglevel', 'error', '-i', str(wav_path), '-codec:a', 'libmp3lame', '-b:a', '64k', str(out_path)]
    subprocess.run(cmd, check=True)


def get_duration(ffprobe_path: str, mp3_path: Path):
    # Try ffprobe first
    ffprobe = shutil.which('ffprobe')
    if ffprobe:
        try:
            out = subprocess.check_output([ffprobe, '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', str(mp3_path)])
            return float(out.decode().strip())
        except Exception:
            return None
    # Fallback: call ffmpeg -i and parse stderr
    try:
        proc = subprocess.run([shutil.which('ffmpeg'), '-i', str(mp3_path)], stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        err = proc.stderr
        # look for Duration: 00:00:01.00
        import re
        m = re.search(r'Duration:\s*(\d{2}:\d{2}:\d{2}\.\d+)', err)
        if m:
            hh, mm, ss = m.group(1).split(':')
            secs = float(hh) * 3600 + float(mm) * 60 + float(ss)
            return secs
    except Exception:
        pass
    return None


def main():
    ffmpeg = check_ffmpeg()

    with tempfile.TemporaryDirectory() as td:
        wav = Path(td) / 'silent.wav'
        tmp_out = Path(td) / 'silent.mp3'

        print('Generating 1.0s silent WAV ->', wav)
        generate_silent_wav(wav, duration_s=1.0, rate=44100)

        print('Transcoding WAV to MP3 using ffmpeg...')
        transcode_to_mp3(ffmpeg, wav, tmp_out)

        # Ensure target directory exists
        TARGET.parent.mkdir(parents=True, exist_ok=True)
        # Overwrite target
        tmp_out.replace(TARGET)

        size = TARGET.stat().st_size
        print(f'Wrote {TARGET} ({size} bytes)')

        duration = get_duration(shutil.which('ffprobe') or ffmpeg, TARGET)
        print('Detected duration (s):', duration)

        # Print first 12 bytes hex for inspection
        head = TARGET.read_bytes()[:12]
        print('First bytes:', head.hex())

        if size < 1024:
            print('\nWarning: resulting MP3 size is < 1KB. It may still play, but for best compatibility consider increasing duration or bitrate.')
        if duration is None or duration < 0.5:
            print('\nWarning: detected duration is <0.5s or unknown. Please verify playback in your browser.')

        print('\nDone. The frontend references the placeholder at /static/placeholders/placeholder_silent.mp3')


if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError as e:
        print('ffmpeg failed:', e)
        sys.exit(2)
    except SystemExit as e:
        raise
    except Exception as e:
        print('Error:', e)
        sys.exit(1)
