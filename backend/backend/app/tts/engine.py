"""
TTS Engine: Main synthesis interface with provider selection and caching
"""
import os
import hashlib
import logging
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Provider imports
from .providers import edge, mock

# Configuration from environment
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "edge")  # Default: Edge (production)
TTS_VOICE = os.getenv("TTS_VOICE", "hi-IN-SwaraNeural")
TTS_RATE = os.getenv("TTS_RATE", "-10%")  # Slower for soothing effect
SIMULATE_RENDER = int(os.getenv("SIMULATE_RENDER", "0"))

# Hindi voice mapping with styles and tuning
HINDI_VOICE_MAP = {
    "hi-IN-SwaraNeural": {
        "style": "Calm",
        "rate": "-5%",
        "pitch": "+0st"
    },
    "hi-IN-DiyaNeural": {
        "style": "Narration",
        "rate": "-3%",
        "pitch": "+0st"
    }
}

# Parse TTS_RATE to pace multiplier
def _parse_rate_to_pace(rate_str: str) -> float:
    """Convert rate string like '-10%' to pace multiplier (0.9)"""
    try:
        if rate_str.endswith("%"):
            pct = int(rate_str[:-1])
            return 1.0 + (pct / 100.0)
        return 1.0
    except:
        return 1.0

DEFAULT_PACE = _parse_rate_to_pace(TTS_RATE)


def _select_provider():
    """Select TTS provider based on availability and config - Edge is default for production"""
    if SIMULATE_RENDER:
        logger.info("SIMULATE_RENDER=1: Using mock TTS provider")
        return mock
    
    if TTS_PROVIDER == "mock":
        logger.info("TTS_PROVIDER=mock: Using mock provider explicitly")
        return mock
    
    # Default: Try Edge provider first (production path)
    if TTS_PROVIDER == "edge" or TTS_PROVIDER == "":
        if edge.is_available():
            logger.info("Using Edge-TTS provider (production default)")
            return edge
        else:
            logger.warning("Edge-TTS not available, falling back to mock provider")
            return mock
    
    # Unknown provider - fallback to mock
    logger.warning(f"Unknown TTS_PROVIDER={TTS_PROVIDER}, falling back to mock")
    return mock


ACTIVE_PROVIDER = _select_provider()


def synthesize(
    text: str,
    lang: str = "hi",
    voice_id: Optional[str] = None,
    pace: Optional[float] = None,
    cache_dir: Optional[Path] = None
) -> Tuple[bytes, dict]:
    """
    Synthesize speech with caching
    
    Args:
        text: Text to synthesize
        lang: Language code (hi, en)
        voice_id: Specific voice (default from TTS_VOICE env)
        pace: Pace multiplier (default from TTS_RATE env)
        cache_dir: Cache directory (optional)
    
    Returns:
        Tuple of (wav_bytes, metadata_dict)
        metadata includes: provider, voice_id, pace, duration_sec, cached
    """
    # Use defaults
    if voice_id is None:
        voice_id = TTS_VOICE
    if pace is None:
        pace = DEFAULT_PACE
    
    # Apply voice mapping for Hindi - default to Swara if voice not in map
    if lang == "hi":
        if voice_id not in HINDI_VOICE_MAP:
            logger.info(f"Voice {voice_id} not in Hindi voice map, defaulting to hi-IN-SwaraNeural")
            voice_id = "hi-IN-SwaraNeural"
    
    # Check cache
    cached_wav = None
    if cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_key = _compute_cache_key(voice_id, text, pace)
        cache_path = cache_dir / f"{cache_key}.wav"
        
        if cache_path.exists():
            logger.info(f"TTS cache hit: {cache_key}")
            with open(cache_path, "rb") as f:
                cached_wav = f.read()
    
    # Synthesize if not cached (Task 6: Add timing telemetry)
    import time
    synth_start = time.time()
    
    if cached_wav is None:
        logger.info(f"Synthesizing: lang={lang}, voice={voice_id}, pace={pace:.2f}")
        wav_bytes = ACTIVE_PROVIDER.synthesize(text, lang, voice_id, pace)
        
        synth_ms = int((time.time() - synth_start) * 1000)
        
        # Save to cache
        if cache_dir:
            with open(cache_path, "wb") as f:
                f.write(wav_bytes)
            logger.info(f"Saved to cache: {cache_path}")
        
        was_cached = False
    else:
        synth_ms = int((time.time() - synth_start) * 1000)  # Cache read time
        wav_bytes = cached_wav
        was_cached = True
    
    # Get duration and ensure numeric types
    duration_sec = float(_get_wav_duration(wav_bytes))
    
    # Task 6: Add telemetry fields - ensure all numeric fields are proper types
    provider_name = ACTIVE_PROVIDER.get_info()["name"]
    metadata = {
        "provider": provider_name,
        "voice_id": voice_id,
        "pace": float(pace),
        "duration_sec": float(duration_sec),
        "cached": bool(was_cached),
        "cache_hit": bool(was_cached),
        "synth_ms": int(synth_ms),
        "lang": lang
    }
    
    # Assertion: verify numeric types
    assert isinstance(metadata["duration_sec"], float), f"duration_sec must be float, got {type(metadata['duration_sec'])}"
    assert isinstance(metadata["synth_ms"], int) or metadata["synth_ms"] is None, f"synth_ms must be int, got {type(metadata['synth_ms'])}"
    
    # Task 6: Log synthesis timing
    cache_status = "cache_hit" if was_cached else "synthesized"
    logger.info(f"TTS {voice_id} {provider_name} in {synth_ms}ms (cache_hit={was_cached})")
    
    return wav_bytes, metadata


def _compute_cache_key(voice_id: str, text: str, pace: float) -> str:
    """Compute cache key hash from voice, text, and pace"""
    content = f"{voice_id}|{text}|{pace:.3f}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def _get_wav_duration(wav_bytes: bytes) -> float:
    """Extract duration from WAV file"""
    import wave
    import io
    
    try:
        with wave.open(io.BytesIO(wav_bytes), 'rb') as wav:
            frames = wav.getnframes()
            rate = wav.getframerate()
            return frames / rate
    except:
        return 0.0


def make_silent_wav_ms(ms: int) -> bytes:
    """Create a tiny silent WAV file of specified duration in milliseconds"""
    try:
        from pydub import AudioSegment
        import io
        
        silent = AudioSegment.silent(duration=ms)
        buffer = io.BytesIO()
        silent.export(buffer, format="wav")
        return buffer.getvalue()
    except ImportError:
        # Fallback: create minimal WAV manually (1 second at 24kHz)
        import struct
        import io
        
        sample_rate = 24000
        num_samples = int((ms / 1000.0) * sample_rate)
        num_channels = 1
        bits_per_sample = 16
        byte_rate = sample_rate * num_channels * bits_per_sample // 8
        block_align = num_channels * bits_per_sample // 8
        data_size = num_samples * block_align
        
        wav = io.BytesIO()
        wav.write(b'RIFF')
        wav.write(struct.pack('<I', 36 + data_size))
        wav.write(b'WAVE')
        wav.write(b'fmt ')
        wav.write(struct.pack('<I', 16))
        wav.write(struct.pack('<H', 1))
        wav.write(struct.pack('<H', num_channels))
        wav.write(struct.pack('<I', sample_rate))
        wav.write(struct.pack('<I', byte_rate))
        wav.write(struct.pack('<H', block_align))
        wav.write(struct.pack('<H', bits_per_sample))
        wav.write(b'data')
        wav.write(struct.pack('<I', data_size))
        wav.write(b'\x00' * data_size)
        
        return wav.getvalue()


def get_provider_info() -> dict:
    """Get active provider information"""
    return ACTIVE_PROVIDER.get_info()


def health_check() -> dict:
    """Perform TTS health check"""
    try:
        provider_info = get_provider_info()
        provider_name = provider_info.get("name", "unknown")
        
        # If edge provider, verify imports
        if provider_name == "edge":
            try:
                import edge_tts
                import aiohttp
                result = {
                    "ok": True,
                    "provider": provider_name,
                    "edge_tts_version": edge_tts.__version__ if hasattr(edge_tts, '__version__') else "unknown",
                    "available": edge.is_available(),
                    "reason": "Edge-TTS imports successful"
                }
            except Exception as e:
                result = {
                    "ok": False,
                    "provider": provider_name,
                    "available": False,
                    "reason": f"Edge-TTS import failed: {str(e)}"
                }
        else:
            # Mock provider
            result = {
                "ok": True,
                "provider": provider_name,
                "available": True,
                "reason": "Mock provider always available"
            }
        
        return result
        
    except Exception as e:
        return {
            "ok": False,
            "provider": "unknown",
            "available": False,
            "reason": str(e)
        }
