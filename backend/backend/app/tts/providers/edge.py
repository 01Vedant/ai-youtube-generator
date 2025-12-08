"""
Edge-TTS provider for high-quality Hindi narration
Uses Microsoft Edge TTS with hi-IN-SwaraNeural (soothing female)
"""
import asyncio
import io
import logging
import time
import random
from typing import Optional

logger = logging.getLogger(__name__)

# Try to import edge-tts
try:
    import edge_tts
    EDGE_AVAILABLE = True
except ImportError:
    EDGE_AVAILABLE = False
    logger.warning("edge-tts not available. Install with: pip install edge-tts")


async def _synthesize_async(
    text: str,
    voice: str,
    rate: str
) -> bytes:
    """
    Async synthesis using edge-tts
    
    Args:
        text: Text to synthesize
        voice: Voice identifier (e.g., hi-IN-SwaraNeural)
        rate: Rate adjustment (e.g., -10%)
    
    Returns:
        Audio bytes (MP3 from Edge, will convert to WAV in caller)
    """
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    
    audio_chunks = []
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_chunks.append(chunk["data"])
    
    return b"".join(audio_chunks)


def synthesize(text: str, lang: str, voice_id: str, pace: float) -> bytes:
    """
    Synthesize speech using Edge-TTS with retry logic
    
    Args:
        text: Text to synthesize
        lang: Language code (used for voice selection if voice_id not specified)
        voice_id: Specific voice ID (e.g., hi-IN-SwaraNeural)
        pace: Pace multiplier (1.0 = normal, <1.0 = slower, >1.0 = faster)
    
    Returns:
        WAV bytes (16-bit PCM, 24000 Hz)
    
    Raises:
        RuntimeError: If edge-tts not available or synthesis fails after retries
    """
    if not EDGE_AVAILABLE:
        raise RuntimeError("edge-tts not available")
    
    # Normalize voice selection
    if not voice_id or voice_id == "default":
        if lang == "hi":
            voice_id = "hi-IN-SwaraNeural"
        else:
            voice_id = "en-US-AriaNeural"
    
    # Convert pace to rate string (Edge uses percentage)
    # pace 1.0 = +0%, pace 0.9 = -10%, pace 1.1 = +10%
    rate_pct = int((pace - 1.0) * 100)
    rate_str = f"{rate_pct:+d}%"
    
    # Normalize Hindi punctuation
    if lang == "hi":
        text = _normalize_hindi_text(text)
    
    # Retry logic with exponential backoff
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Run async synthesis
            mp3_bytes = asyncio.run(_synthesize_async(text, voice_id, rate_str))
            
            # Convert MP3 to WAV using pydub
            wav_bytes = _mp3_to_wav(mp3_bytes)
            return wav_bytes
            
        except Exception as e:
            if attempt < max_retries - 1:
                # Exponential backoff with jitter
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                logger.warning(
                    f"TTS attempt {attempt + 1} failed: {e}. "
                    f"Retrying in {wait_time:.2f}s..."
                )
                time.sleep(wait_time)
            else:
                logger.error(f"TTS failed after {max_retries} attempts: {e}")
                raise RuntimeError(f"Edge-TTS synthesis failed: {e}")


def _normalize_hindi_text(text: str) -> str:
    """
    Normalize Hindi text for better synthesis
    - Ensure proper sentence endings with devanagari danda
    - Add slight pauses between sentences
    """
    # Add devanagari danda if missing at sentence ends
    import re
    
    # Replace common sentence endings
    text = re.sub(r'([।?!])\s+', r'\1 ', text)  # Normalize spacing
    text = re.sub(r'([^।?!])$', r'\1।', text)  # Add danda at end if missing
    
    return text


def _mp3_to_wav(mp3_bytes: bytes) -> bytes:
    """
    Convert MP3 to WAV using pydub
    
    Args:
        mp3_bytes: MP3 audio data
    
    Returns:
        WAV bytes (16-bit PCM, 24000 Hz)
    """
    try:
        from pydub import AudioSegment
        
        # Load MP3
        audio = AudioSegment.from_mp3(io.BytesIO(mp3_bytes))
        
        # Convert to 24kHz mono 16-bit PCM
        audio = audio.set_frame_rate(24000)
        audio = audio.set_channels(1)
        audio = audio.set_sample_width(2)  # 16-bit
        
        # Export to WAV
        wav_buffer = io.BytesIO()
        audio.export(wav_buffer, format="wav")
        return wav_buffer.getvalue()
        
    except ImportError:
        logger.error("pydub not available. Install with: pip install pydub")
        raise RuntimeError("pydub required for MP3 to WAV conversion")


def is_available() -> bool:
    """Check if Edge-TTS provider is available"""
    return EDGE_AVAILABLE


def get_info() -> dict:
    """Provider metadata"""
    return {
        "name": "edge",
        "voices": [
            "hi-IN-SwaraNeural",  # Soothing female (primary)
            "hi-IN-DiyaNeural",   # Alternative female
            "en-US-AriaNeural"    # English fallback
        ],
        "sample_rate": 24000,
        "features": ["rate_control", "ssml_support"],
        "available": EDGE_AVAILABLE
    }
