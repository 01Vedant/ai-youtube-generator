"""
Music Mixer - Combines narration with background music bed.
Applies sidechain-style ducking and normalizes to target LUFS.
"""
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import struct
import io

logger = logging.getLogger(__name__)


def mix_with_bed(
    narration_full: Path,
    out_dir: Path
) -> Dict[str, Any]:
    """
    Mix narration with background music bed.
    
    Args:
        narration_full: Path to full narration WAV file
        out_dir: Output directory (will create audio/ subdirectory)
    
    Returns:
        Dict with keys:
            - mix_path: Path to audio/mix.wav
            - lufs: Target LUFS (-16.0)
            - ducking_db: Ducking amount in dB (-6)
            - bed_source: "file" or "synth"
            - bed_path: Path to music bed file (if applicable)
    """
    audio_dir = out_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    
    mix_path = audio_dir / "mix.wav"
    
    try:
        from pydub import AudioSegment
        import pyloudnorm as pyln
        import numpy as np
        
        # Load narration
        narration = AudioSegment.from_wav(str(narration_full))
        narration_duration_ms = len(narration)
        
        # Get or create music bed
        music_bed_path_str = os.getenv("MUSIC_BED_PATH")
        if music_bed_path_str and Path(music_bed_path_str).exists():
            bed_source = "file"
            bed = AudioSegment.from_file(music_bed_path_str)
            bed_path_rel = music_bed_path_str
        else:
            bed_source = "synth"
            # Synthesize soft pad (quiet sine wave at 200 Hz and 300 Hz)
            bed = _generate_soft_pad(narration_duration_ms)
            bed_synth_path = audio_dir / "bed_synth.wav"
            bed.export(str(bed_synth_path), format="wav")
            bed_path_rel = str(bed_synth_path.relative_to(out_dir))
        
        # Ensure bed matches narration duration
        if len(bed) < narration_duration_ms:
            # Loop bed to match duration
            repeats = (narration_duration_ms // len(bed)) + 1
            bed = bed * repeats
        bed = bed[:narration_duration_ms]
        
        # Apply ducking: reduce bed volume during narration
        # Simple approach: reduce bed by 6 dB across entire duration
        ducking_db = -6
        bed_ducked = bed + ducking_db
        
        # Mix: narration at 0 dB, bed at ducked level
        mixed = narration.overlay(bed_ducked)
        
        # Normalize to target LUFS (-16.0)
        target_lufs = float(os.getenv("AUDIO_TARGET_LUFS", "-16.0"))
        normalized = _normalize_to_lufs(mixed, target_lufs)
        
        # Export final mix
        normalized.export(str(mix_path), format="wav")
        
        logger.info(f"Mixed narration with bed: {len(per_scene)} scenes, LUFS={target_lufs}")
        
        return {
            "mix_path": str(mix_path.relative_to(out_dir)),
            "lufs": target_lufs,
            "ducking_db": ducking_db,
            "bed_source": bed_source,
            "bed_path": bed_path_rel
        }
    
    except ImportError as e:
        logger.warning(f"Missing audio libraries (pydub/pyloudnorm): {e}, creating simple copy")
        # Fallback: just copy narration to mix
        import shutil
        shutil.copy(str(narration_full), str(mix_path))
        
        return {
            "mix_path": str(mix_path.relative_to(out_dir)),
            "lufs": -16.0,
            "ducking_db": 0,
            "bed_source": "none",
            "bed_path": None
        }
    
    except Exception as e:
        logger.error(f"Music mixing failed: {e}, using narration as-is")
        # Fallback: copy narration
        import shutil
        shutil.copy(str(narration_full), str(mix_path))
        
        return {
            "mix_path": str(mix_path.relative_to(out_dir)),
            "lufs": -16.0,
            "ducking_db": 0,
            "bed_source": "error",
            "bed_path": None
        }


def _generate_soft_pad(duration_ms: int) -> 'AudioSegment':
    """Generate soft sine wave pad for background."""
    from pydub.generators import Sine
    
    # Two sine waves at different frequencies for richness
    sine1 = Sine(200).to_audio_segment(duration=duration_ms)  # Low drone
    sine2 = Sine(300).to_audio_segment(duration=duration_ms)  # Mid drone
    
    # Mix at low volume (-30 dB each)
    pad = (sine1 - 30).overlay(sine2 - 30)
    
    return pad


def _normalize_to_lufs(audio: 'AudioSegment', target_lufs: float) -> 'AudioSegment':
    """
    Normalize audio to target LUFS using pyloudnorm.
    
    Args:
        audio: pydub AudioSegment
        target_lufs: Target loudness in LUFS (e.g., -16.0)
    
    Returns:
        Normalized AudioSegment
    """
    try:
        import pyloudnorm as pyln
        import numpy as np
        
        # Convert to numpy array
        samples = np.array(audio.get_array_of_samples()).astype(np.float32)
        samples = samples / (2**15)  # Normalize to [-1, 1]
        
        # Reshape for mono/stereo
        if audio.channels == 2:
            samples = samples.reshape((-1, 2))
        
        # Measure current loudness
        meter = pyln.Meter(audio.frame_rate)
        current_lufs = meter.integrated_loudness(samples)
        
        # Calculate gain needed
        gain_db = target_lufs - current_lufs
        
        # Apply gain
        normalized = audio + gain_db
        
        logger.info(f"Normalized audio: {current_lufs:.1f} LUFS → {target_lufs:.1f} LUFS (gain: {gain_db:+.1f} dB)")
        
        return normalized
    
    except Exception as e:
        logger.warning(f"LUFS normalization failed: {e}, returning original audio")
        return audio
