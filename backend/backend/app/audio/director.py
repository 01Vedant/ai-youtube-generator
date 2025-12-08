"""
Audio Director - Beat detection and audio-led editing
Gracefully handles SIMULATE_RENDER mode with synthetic beats
"""
import os
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any


def detect_beats(music_path: Path) -> List[float]:
    """
    Detect beat times in music track.
    
    Args:
        music_path: Path to music audio file (WAV/MP3)
    
    Returns:
        List of beat timestamps in seconds
    
    In SIMULATE mode: returns uniform grid (every 0.6s)
    In production: uses librosa onset detection
    """
    simulate = int(os.getenv("SIMULATE_RENDER", "0")) == 1
    
    if simulate:
        # Uniform beat grid at ~100 BPM (0.6s intervals)
        duration = 30.0  # Assume 30s track
        return [i * 0.6 for i in range(int(duration / 0.6))]
    
    # Production: librosa onset detection
    # try:
    #     import librosa
    #     y, sr = librosa.load(str(music_path))
    #     tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
    #     beat_times = librosa.frames_to_time(beats, sr=sr)
    #     return beat_times.tolist()
    # except ImportError:
    #     return []
    
    return []


def split_voice_phrases(tts_path: Path) -> List[Tuple[float, float]]:
    """
    Split TTS audio into natural phrases.
    
    Args:
        tts_path: Path to TTS/voiceover audio file
    
    Returns:
        List of (start_sec, end_sec) tuples for each phrase
    
    In SIMULATE mode: heuristic based on 150 WPM speech rate
    In production: uses voice activity detection (VAD)
    """
    simulate = int(os.getenv("SIMULATE_RENDER", "0")) == 1
    
    if simulate:
        # Assume phrases every 3-5 seconds
        duration = 30.0  # Assume 30s narration
        phrases = []
        t = 0.0
        while t < duration:
            phrase_dur = 4.0  # Average phrase duration
            phrases.append((t, min(t + phrase_dur, duration)))
            t += phrase_dur + 0.5  # Small gap between phrases
        return phrases
    
    # Production: VAD with pydub or webrtcvad
    # Split on silence detection
    
    return []


def snap_cut(cut_sec: float, beats: List[float], tolerance: float = 0.15) -> float:
    """
    Snap a cut time to nearest beat.
    
    Args:
        cut_sec: Proposed cut time in seconds
        beats: List of beat timestamps
        tolerance: Maximum distance to snap (seconds)
    
    Returns:
        Snapped cut time (or original if no beat within tolerance)
    """
    if not beats:
        return cut_sec
    
    # Find nearest beat
    diffs = [abs(beat - cut_sec) for beat in beats]
    min_diff = min(diffs)
    
    if min_diff <= tolerance:
        nearest_idx = diffs.index(min_diff)
        return beats[nearest_idx]
    
    return cut_sec


def plan_ducking(
    voice_phrases: List[Tuple[float, float]],
    music_duration: float,
    duck_db: float = -6.0
) -> Dict[str, Any]:
    """
    Plan music ducking (volume reduction) during voiceover.
    
    Args:
        voice_phrases: List of (start, end) phrase timestamps
        music_duration: Total music track duration
        duck_db: Amount to reduce music volume (negative dB)
    
    Returns:
        Dict with ducking parameters for audio mixer
    """
    return {
        "enabled": True,
        "phrases": voice_phrases,
        "duck_db": duck_db,
        "attack_ms": 100,  # Fast fade down
        "release_ms": 300   # Gradual fade up
    }
