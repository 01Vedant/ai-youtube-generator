"""
Quality Profiles - Preview vs Final render settings
"""
from typing import Dict, Any, List


def get_profile(quality: str = "final") -> Dict[str, Any]:
    """
    Get render profile settings.
    
    Args:
        quality: "preview" or "final"
    
    Returns:
        Dict with fps, size, encoder, cq, filters settings
    """
    if quality == "preview":
        return {
            "name": "preview",
            "description": "Fast preview mode for iterations",
            "fps": 24,
            "size": (1280, 720),  # 720p
            "resolution": "720p",
            "encoder": "libx264",
            "cq": 28,  # Higher CQ = lower quality, faster encode
            "preset": "faster",
            "filters": [],  # Minimal filters
            "audio_bitrate": "128k",
            "enable_grain": False,
            "enable_lut": False
        }
    else:  # final
        return {
            "name": "final",
            "description": "Production quality output",
            "fps": 30,
            "size": (1920, 1080),  # 1080p
            "resolution": "1080p",
            "encoder": "libx264",
            "cq": 20,  # Lower CQ = higher quality
            "preset": "slow",
            "filters": ["deband", "unsharp"],  # Quality enhancement
            "audio_bitrate": "192k",
            "enable_grain": True,  # Film grain for cinematic look
            "enable_lut": True     # Color grading LUT
        }


def list_profiles() -> List[str]:
    """List available profile names"""
    return ["preview", "final"]
