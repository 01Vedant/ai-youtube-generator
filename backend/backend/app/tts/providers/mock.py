"""
Mock TTS provider for SIMULATE mode
Generates soft noise with fade-in/out as fallback
"""
import io
import wave
import struct
import math
import random


def synthesize(text: str, lang: str, voice_id: str, pace: float) -> bytes:
    """
    Generate mock audio with soft noise and fade effects
    
    Args:
        text: Text to synthesize (used for duration estimation)
        lang: Language code (ignored in mock)
        voice_id: Voice identifier (ignored in mock)
        pace: Pace multiplier (ignored in mock)
    
    Returns:
        WAV bytes (16-bit PCM, 22050 Hz)
    """
    # Estimate duration: ~10 chars per second at normal pace
    char_rate = 10.0 / pace if pace > 0 else 10.0
    duration_sec = max(0.5, len(text) / char_rate)
    
    sample_rate = 22050
    num_samples = int(duration_sec * sample_rate)
    fade_samples = int(0.05 * sample_rate)  # 50ms fade
    
    # Generate soft pink noise
    samples = []
    b0 = b1 = b2 = b3 = b4 = b5 = b6 = 0.0
    
    for i in range(num_samples):
        # Pink noise filter
        white = random.uniform(-1, 1)
        b0 = 0.99886 * b0 + white * 0.0555179
        b1 = 0.99332 * b1 + white * 0.0750759
        b2 = 0.96900 * b2 + white * 0.1538520
        b3 = 0.86650 * b3 + white * 0.3104856
        b4 = 0.55000 * b4 + white * 0.5329522
        b5 = -0.7616 * b5 - white * 0.0168980
        pink = b0 + b1 + b2 + b3 + b4 + b5 + b6 + white * 0.5362
        b6 = white * 0.115926
        
        # Apply amplitude envelope with fade
        amplitude = 0.05  # Very soft
        if i < fade_samples:
            amplitude *= (i / fade_samples)  # Fade in
        elif i > num_samples - fade_samples:
            amplitude *= ((num_samples - i) / fade_samples)  # Fade out
        
        sample = int(pink * amplitude * 32767)
        sample = max(-32768, min(32767, sample))
        samples.append(sample)
    
    # Write WAV
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(struct.pack(f'{len(samples)}h', *samples))
    
    return buffer.getvalue()


def is_available() -> bool:
    """Mock provider is always available"""
    return True


def get_info() -> dict:
    """Provider metadata"""
    return {
        "name": "mock",
        "voices": ["mock-voice"],
        "sample_rate": 22050,
        "note": "Fallback provider for SIMULATE mode"
    }
