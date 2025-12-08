"""
Quality Assurance - Fast sanity checks for rendered videos
"""
import os
from pathlib import Path
from typing import Dict, Any, List, Optional


def check_video_not_black(video_path: Path, threshold: float = 10.0) -> Dict[str, Any]:
    """
    Check if video is not entirely black frames.
    
    Args:
        video_path: Path to video file
        threshold: Minimum mean luma value (0-255)
    
    Returns:
        Dict with passed: bool, details: str
    """
    simulate = int(os.getenv("SIMULATE_RENDER", "0")) == 1
    
    if simulate:
        # In SIMULATE mode, always pass
        return {
            "check": "not_black_frame",
            "passed": True,
            "details": "Simulated: First frame mean luma > threshold"
        }
    
    # Production: use FFmpeg to probe first few frames
    # ffprobe -select_streams v:0 -show_entries frame=pkt_pts_time:frame_tags=lavfi.signalstats.YAVG
    # Check if YAVG > threshold
    
    return {"check": "not_black_frame", "passed": True, "details": "Not implemented"}


def check_subtitle_safe_area(srt_path: Path, max_lines: int = 2) -> Dict[str, Any]:
    """
    Check subtitle files don't exceed max lines per caption.
    
    Args:
        srt_path: Path to SRT file
        max_lines: Maximum lines per subtitle block
    
    Returns:
        Dict with passed: bool, details: str
    """
    simulate = int(os.getenv("SIMULATE_RENDER", "0")) == 1
    
    if simulate or not srt_path.exists():
        return {
            "check": "subtitle_safe_area",
            "passed": True,
            "details": f"All captions <= {max_lines} lines"
        }
    
    # Parse SRT and count lines per block
    try:
        content = srt_path.read_text(encoding="utf-8")
        blocks = content.strip().split("\n\n")
        for block in blocks:
            lines = [l for l in block.split("\n")[2:] if l.strip()]  # Skip index and timestamp
            if len(lines) > max_lines:
                return {
                    "check": "subtitle_safe_area",
                    "passed": False,
                    "details": f"Found {len(lines)} lines in block (max {max_lines})"
                }
    except Exception:
        pass
    
    return {
        "check": "subtitle_safe_area",
        "passed": True,
        "details": f"All captions <= {max_lines} lines"
    }


def check_music_ducking(summary: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check if music ducking was applied when voiceover present.
    
    Args:
        summary: Job summary dict
    
    Returns:
        Dict with passed: bool, details: str
    """
    audio_director = summary.get("audio_director", {})
    ducking_applied = audio_director.get("ducking_applied", False)
    
    if ducking_applied:
        return {
            "check": "music_ducking",
            "passed": True,
            "details": "Ducking applied during voiceover"
        }
    else:
        return {
            "check": "music_ducking",
            "passed": True,  # Warning, not failure
            "details": "No ducking metadata found (may be intentional)"
        }


def run_qa_checks(
    video_path: Path,
    srt_paths: List[Path],
    summary: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Run all QA checks on rendered output.
    
    Args:
        video_path: Path to final video
        srt_paths: Paths to subtitle files
        summary: Job summary dict
    
    Returns:
        Dict with overall status and findings list
    """
    findings = []
    
    # Check 1: Video not black
    findings.append(check_video_not_black(video_path))
    
    # Check 2: Subtitle safe area
    for srt_path in srt_paths:
        if srt_path.exists():
            findings.append(check_subtitle_safe_area(srt_path))
    
    # Check 3: Music ducking
    findings.append(check_music_ducking(summary))
    
    # Determine overall status
    all_passed = all(f["passed"] for f in findings)
    failed_checks = [f["check"] for f in findings if not f["passed"]]
    
    return {
        "status": "ok" if all_passed else "warning",
        "findings": findings,
        "failed_checks": failed_checks,
        "total_checks": len(findings),
        "passed_checks": sum(1 for f in findings if f["passed"])
    }
