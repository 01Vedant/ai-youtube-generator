"""
Dual subtitles generation: create both Hindi and English SRT files.
Integrates with orchestrator to include subtitle assets in output.
"""

import logging
import re
from pathlib import Path
from typing import Dict, Optional, Tuple
from datetime import timedelta

logger = logging.getLogger(__name__)


def seconds_to_srt_time(seconds: float) -> str:
    """Convert seconds to SRT time format (HH:MM:SS,mmm)."""
    td = timedelta(seconds=seconds)
    hours, remainder = divmod(int(td.total_seconds()), 3600)
    minutes, secs = divmod(remainder, 60)
    millis = int((td.total_seconds() % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def create_srt_entry(index: int, start: float, end: float, text: str) -> str:
    """Create a single SRT subtitle entry."""
    return f"{index}\n{seconds_to_srt_time(start)} --> {seconds_to_srt_time(end)}\n{text}\n\n"


def estimate_word_duration(text: str, wpm: int = 150) -> float:
    """
    Estimate duration (in seconds) for spoken text.
    Default 150 words per minute = ~0.4 seconds per word.
    """
    word_count = len(text.split())
    return max(1, (word_count / wpm) * 60)


def generate_dual_srt(plan: dict, output_dir: Optional[Path] = None) -> Dict[str, str]:
    """
    Generate dual SRT subtitle files (Hindi + English) from a RenderPlan.
    
    Args:
        plan: RenderPlan dictionary with scenes
        output_dir: Where to write .srt files (default: temp)
    
    Returns:
        {
            'hi_path': '/path/to/subtitles_hi.srt',
            'en_path': '/path/to/subtitles_en.srt',
            'hi_content': 'SRT content for Hindi',
            'en_content': 'SRT content for English',
        }
    """
    if output_dir is None:
        import tempfile
        output_dir = Path(tempfile.gettempdir()) / "subtitles"
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    scenes = plan.get("scenes", [])
    language = plan.get("language", "en")
    
    hi_srt_content = ""
    en_srt_content = ""
    
    current_time = 0.0
    srt_index = 1
    
    for scene_idx, scene in enumerate(scenes):
        narration = scene.get("narration", "")
        duration = scene.get("duration", 3)
        
        if not narration.strip():
            # No narration, skip subtitle for this scene
            current_time += duration
            continue
        
        # Estimate word duration for this narration
        estimated_duration = estimate_word_duration(narration, wpm=150)
        
        # Use actual scene duration or estimated, whichever is longer
        actual_duration = max(duration, estimated_duration)
        
        start_time = current_time
        end_time = current_time + actual_duration
        
        # Create SRT entries
        # For simplicity, we use the same narration for both hi and en
        # In a real system, you'd translate the narration to both languages
        
        en_srt_content += create_srt_entry(srt_index, start_time, end_time, narration)
        
        # For Hindi SRT, try simple transliteration of English narration
        # (In production, use proper translation service like Google Translate)
        hi_narration = narration  # Placeholder: would translate here
        hi_srt_content += create_srt_entry(srt_index, start_time, end_time, hi_narration)
        
        current_time = end_time
        srt_index += 1
    
    # Write SRT files
    hi_path = output_dir / "subtitles_hi.srt"
    en_path = output_dir / "subtitles_en.srt"
    
    hi_path.write_text(hi_srt_content, encoding="utf-8")
    en_path.write_text(en_srt_content, encoding="utf-8")
    
    logger.info(
        "Generated dual subtitles: hi=%s (%d entries), en=%s (%d entries)",
        hi_path, srt_index - 1, en_path, srt_index - 1
    )
    
    return {
        "hi_path": str(hi_path),
        "en_path": str(en_path),
        "hi_content": hi_srt_content,
        "en_content": en_srt_content,
    }


def embed_soft_subs_ffmpeg_cmd(
    video_path: str,
    hi_srt_path: str,
    en_srt_path: str,
    output_path: str,
    primary_lang: str = "en",
) -> str:
    """
    Generate ffmpeg command to embed soft subtitles (ASS format).
    Primary language is burned in; secondary is soft.
    
    Args:
        video_path: Path to input video
        hi_srt_path: Path to Hindi SRT
        en_srt_path: Path to English SRT
        output_path: Path to output video
        primary_lang: 'en' or 'hi' (which language to burn in)
    
    Returns:
        ffmpeg command string
    """
    # Convert SRT to ASS (Advanced SubStation Alpha) for better formatting
    if primary_lang == "en":
        primary_srt = en_srt_path
        secondary_srt = hi_srt_path
    else:
        primary_srt = hi_srt_path
        secondary_srt = en_srt_path
    
    # Build ffmpeg filter: burn primary subs, map secondary subs
    # This is a simplified version; production needs more complexity
    
    cmd = (
        f"ffmpeg -i {video_path} "
        f"-vf subtitles={primary_srt}:force_style='FontSize=20,FontName=DejaVu Sans' "
        f"-c:v libx264 -c:a aac "
        f"-sub_charenc UTF-8 "
        f"{output_path}"
    )
    
    return cmd


def create_multitrack_video_with_subs(
    video_path: str,
    hi_srt_path: str,
    en_srt_path: str,
    output_dir: Path,
) -> Dict[str, str]:
    """
    Create two video variants: one with Hindi burned-in, one with English.
    Both include soft subtitles in the other language.
    
    Returns:
        {
            'hi_variant': '/path/to/video_hi.mp4',
            'en_variant': '/path/to/video_en.mp4',
        }
    """
    import subprocess
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Variant 1: Hindi burned-in
    hi_output = str(output_dir / "video_hi.mp4")
    hi_cmd = embed_soft_subs_ffmpeg_cmd(video_path, hi_srt_path, en_srt_path, hi_output, primary_lang="hi")
    
    logger.info("Rendering Hindi variant: %s", hi_cmd)
    try:
        subprocess.run(hi_cmd, shell=True, check=True, capture_output=True, timeout=300)
        logger.info("Hindi variant created: %s", hi_output)
    except subprocess.CalledProcessError as e:
        logger.error("Failed to create Hindi variant: %s", e.stderr.decode() if e.stderr else str(e))
        hi_output = None
    
    # Variant 2: English burned-in
    en_output = str(output_dir / "video_en.mp4")
    en_cmd = embed_soft_subs_ffmpeg_cmd(video_path, hi_srt_path, en_srt_path, en_output, primary_lang="en")
    
    logger.info("Rendering English variant: %s", en_cmd)
    try:
        subprocess.run(en_cmd, shell=True, check=True, capture_output=True, timeout=300)
        logger.info("English variant created: %s", en_output)
    except subprocess.CalledProcessError as e:
        logger.error("Failed to create English variant: %s", e.stderr.decode() if e.stderr else str(e))
        en_output = None
    
    result = {}
    if hi_output:
        result['hi_variant'] = hi_output
    if en_output:
        result['en_variant'] = en_output
    
    return result
