from pathlib import Path
from typing import List
import logging
import subprocess

logger = logging.getLogger(__name__)


def generate_srt(scences: List[dict], out_path: Path):
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf8") as fh:
        cursor = 0.0
        idx = 1
        for s in scences:
            start = cursor
            dur = float(s.get("duration", 3.0))
            end = start + dur
            start_ts = _format_ts(start)
            end_ts = _format_ts(end)
            text = s.get("narration", "")
            fh.write(f"{idx}\n")
            fh.write(f"{start_ts} --> {end_ts}\n")
            fh.write(f"{text}\n\n")
            cursor = end
            idx += 1
    return out_path


def _format_ts(seconds: float) -> str:
    ms = int((seconds - int(seconds)) * 1000)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def burn_in_subtitles(video_in: Path, srt_path: Path, video_out: Path):
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_in),
        "-vf",
        f"subtitles={str(srt_path)}:force_style='FontName=Arial,FontSize=48'",
        "-c:a",
        "copy",
        str(video_out),
    ]
    try:
        subprocess.run(cmd, check=True)
        return Path(video_out)
    except Exception as e:
        logger.exception("ffmpeg burn-in failed: %s", e)
        raise
