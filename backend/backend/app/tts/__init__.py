"""
TTS module for Hindi narration with scene-aware pacing
"""
from .engine import synthesize, get_provider_info, health_check, make_silent_wav_ms

__all__ = ["synthesize", "get_provider_info", "health_check", "make_silent_wav_ms"]
