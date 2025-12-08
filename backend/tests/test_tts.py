"""
Tests for TTS module
"""
import pytest
from pathlib import Path
import tempfile
import wave
import io
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_edge_provider_available_or_mock_fallback():
    """Test that either Edge provider is available or mock fallback works"""
    from app.tts.providers import edge, mock
    
    # Mock should always be available
    assert mock.is_available() is True
    
    # Edge may or may not be available depending on dependencies
    # If not available, get_provider_info should reflect this
    info = edge.get_info()
    assert "name" in info
    assert info["name"] == "edge"
    
    # If edge not available, mock should be used
    if not edge.is_available():
        print("Edge-TTS not available, using mock fallback")
    else:
        print("Edge-TTS available")


def test_synthesize_returns_wav_bytes_hi():
    """Test that synthesize returns valid WAV bytes for Hindi"""
    from app.tts import synthesize
    
    text = "नमस्ते, यह एक परीक्षण है।"
    lang = "hi"
    
    wav_bytes, metadata = synthesize(text=text, lang=lang)
    
    # Check return types
    assert isinstance(wav_bytes, bytes)
    assert isinstance(metadata, dict)
    
    # Check metadata structure
    assert "provider" in metadata
    assert "voice_id" in metadata
    assert "duration_sec" in metadata
    assert "cached" in metadata
    assert metadata["lang"] == lang
    
    # Verify WAV format
    with wave.open(io.BytesIO(wav_bytes), 'rb') as wav:
        assert wav.getnchannels() == 1  # Mono
        assert wav.getsampwidth() == 2  # 16-bit
        assert wav.getframerate() in [22050, 24000, 44100]  # Valid sample rates
        
        # Check duration matches metadata
        frames = wav.getnframes()
        rate = wav.getframerate()
        actual_duration = frames / rate
        assert abs(actual_duration - metadata["duration_sec"]) < 0.1


@pytest.mark.skip(reason="Requires orchestrator module from parent directory")
def test_time_stretch_hits_target_duration_within_tolerance():
    """Test that time-stretched audio matches target duration within tolerance"""
    # This test requires platform.orchestrator which is outside backend/ directory
    # Will be tested via integration smoke test instead
    pass


def test_cache_hit_is_used():
    """Test that TTS caching works correctly"""
    from app.tts import synthesize
    import tempfile
    
    text = "परीक्षण कैश"
    lang = "hi"
    
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir)
        
        # First call - should synthesize
        wav_bytes1, metadata1 = synthesize(
            text=text,
            lang=lang,
            cache_dir=cache_dir
        )
        
        assert metadata1["cached"] is False
        assert len(list(cache_dir.glob("*.wav"))) == 1
        
        # Second call - should hit cache
        wav_bytes2, metadata2 = synthesize(
            text=text,
            lang=lang,
            cache_dir=cache_dir
        )
        
        assert metadata2["cached"] is True
        assert wav_bytes1 == wav_bytes2
        
        # Still only one cached file
        assert len(list(cache_dir.glob("*.wav"))) == 1


def test_mock_provider_basic():
    """Test mock provider basic functionality"""
    from app.tts.providers import mock
    
    text = "Test narration"
    wav_bytes = mock.synthesize(text, "hi", "mock-voice", 1.0)
    
    assert isinstance(wav_bytes, bytes)
    assert len(wav_bytes) > 44  # WAV header is 44 bytes
    
    # Verify it's a valid WAV
    with wave.open(io.BytesIO(wav_bytes), 'rb') as wav:
        assert wav.getnchannels() == 1
        assert wav.getsampwidth() == 2
        assert wav.getframerate() == 22050


def test_provider_info():
    """Test that provider info is available"""
    from app.tts import get_provider_info
    
    info = get_provider_info()
    
    assert "name" in info
    assert info["name"] in ["edge", "mock"]
    assert "voices" in info or "sample_rate" in info


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
