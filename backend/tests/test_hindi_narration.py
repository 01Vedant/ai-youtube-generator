"""
Tests for Hindi narration end-to-end pipeline.
Validates TTS provider, SSML generation, narration building, and mixing.
"""
import os
import sys
import json
import pytest
from pathlib import Path

# Add platform root to path
PLATFORM_ROOT = Path(__file__).resolve().parents[2]
if str(PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(PLATFORM_ROOT))

from backend.app.utils.ssml import build_hindi_ssml, segment_devotional_text
from backend.app.audio.tts_provider import TTSProvider
from backend.app.audio.narration_director import build_hindi_narration
from backend.app.audio.music_mixer import mix_with_bed


class TestSSML:
    """Test SSML generation utilities."""
    
    def test_build_hindi_ssml_basic(self):
        """Test basic SSML generation with Hindi text."""
        sentences = ["पहली किरण", "शांति"]
        ssml = build_hindi_ssml(sentences)
        
        assert "<speak>" in ssml
        assert "</speak>" in ssml
        assert "<prosody" in ssml
        assert "पहली किरण" in ssml
        assert "शांति" in ssml
        assert '<break time="300ms"/>' in ssml
    
    def test_build_hindi_ssml_empty(self):
        """Test SSML with empty input."""
        ssml = build_hindi_ssml([])
        assert ssml == "<speak></speak>"
    
    def test_segment_devotional_text(self):
        """Test text segmentation for Hindi devotional content."""
        text = "पहली किरण। शांति का समय।"
        segments = segment_devotional_text(text)
        
        assert len(segments) >= 1
        assert "पहली किरण" in segments[0]


class TestTTSProvider:
    """Test TTS provider fallback chain."""
    
    def test_provider_initialization(self):
        """Test TTS provider initializes correctly."""
        tts = TTSProvider()
        assert tts.provider in ["azure", "elevenlabs", "fallback"]
    
    def test_fallback_synthesize(self, tmp_path):
        """Test fallback TTS generates valid WAV."""
        tts = TTSProvider()
        # Force fallback provider
        tts.provider = "fallback"
        
        out_path = tmp_path / "test.wav"
        result = tts.synthesize(
            text="नमस्ते",
            lang="hi",
            out_path=out_path
        )
        
        assert result["provider"] == "fallback"
        assert result["path"] == str(out_path)
        assert out_path.exists()
        assert out_path.stat().st_size > 44  # WAV header is 44 bytes
        
        # Verify WAV format
        with open(out_path, 'rb') as f:
            header = f.read(12)
            assert header[:4] == b'RIFF'
            assert header[8:12] == b'WAVE'
    
    def test_duration_estimation(self, tmp_path):
        """Test duration estimation for Hindi text."""
        tts = TTSProvider()
        tts.provider = "fallback"
        
        # ~26 chars should be ~2 seconds at 13 chars/sec
        text = "देवी शक्ति की आराधना।"
        out_path = tmp_path / "test_duration.wav"
        result = tts.synthesize(text=text, lang="hi", out_path=out_path)
        
        # Duration should be reasonable (within ±0.5s of estimate)
        assert 1.5 < result["duration_sec"] < 2.5


class TestNarrationDirector:
    """Test Hindi narration building."""
    
    def test_build_hindi_narration(self, tmp_path):
        """Test full narration generation from scenes."""
        tts = TTSProvider()
        tts.provider = "fallback"  # Use fallback for deterministic tests
        
        scenes = [
            {"narration": "भोर में मंदिर जागता है।", "duration_sec": 5},
            {"narration": "दीपक की लौ हिलती है।", "duration_sec": 5}
        ]
        
        result = build_hindi_narration(scenes, tmp_path, tts)
        
        # Verify structure
        assert result["provider"] in ["azure", "elevenlabs", "fallback"]
        assert result["total_duration_sec"] > 0
        assert len(result["per_scene"]) == 2
        assert result["stretch_used"] is False
        
        # Verify files exist
        voice_dir = tmp_path / "voice"
        assert voice_dir.exists()
        assert (voice_dir / "scene_1.wav").exists()
        assert (voice_dir / "scene_2.wav").exists()
        assert (voice_dir / "narration_full.wav").exists()
        
        # Verify per-scene metadata
        for scene_info in result["per_scene"]:
            assert "path" in scene_info
            assert "duration_sec" in scene_info
            assert scene_info["duration_sec"] > 0


class TestMusicMixer:
    """Test music mixing and ducking."""
    
    def test_mix_with_bed(self, tmp_path):
        """Test mixing narration with background music."""
        # Create a simple narration file first
        tts = TTSProvider()
        tts.provider = "fallback"
        
        voice_dir = tmp_path / "voice"
        voice_dir.mkdir()
        narration_path = voice_dir / "narration_full.wav"
        
        tts.synthesize(
            text="परीक्षण",
            lang="hi",
            out_path=narration_path
        )
        
        # Mix with bed
        mix_result = mix_with_bed(narration_path, tmp_path)
        
        # Verify structure
        assert "mix_path" in mix_result
        assert "lufs" in mix_result
        assert "ducking_db" in mix_result
        assert "bed_source" in mix_result
        
        # Verify mix file exists
        audio_dir = tmp_path / "audio"
        mix_path = audio_dir / "mix.wav"
        assert mix_path.exists()
        
        # Verify LUFS is reasonable
        assert -20 <= mix_result["lufs"] <= -12


@pytest.mark.skipif(
    os.getenv("SIMULATE_RENDER") == "1",
    reason="Skipping detailed validation in SIMULATE mode"
)
class TestEndToEnd:
    """End-to-end integration tests (only run when SIMULATE_RENDER != 1)."""
    
    def test_full_pipeline(self, tmp_path):
        """Test complete Hindi narration pipeline."""
        tts = TTSProvider()
        tts.provider = "fallback"
        
        # Create scene plan
        scenes = [
            {"narration": "पहली किरणों के साथ मंदिर जागता है।", "duration_sec": 6},
            {"narration": "दीपक की लौ हिलती है।", "duration_sec": 6}
        ]
        
        # Build narration
        narration_result = build_hindi_narration(scenes, tmp_path, tts)
        
        # Mix with bed
        mix_result = mix_with_bed(
            tmp_path / narration_result["full_narration_path"],
            tmp_path
        )
        
        # Validate complete audio metadata structure
        audio_metadata = {
            "language": "hi",
            "voice": narration_result["voice"],
            "provider": narration_result["provider"],
            "files": {
                "per_scene": [s["path"] for s in narration_result["per_scene"]],
                "full": narration_result["full_narration_path"],
                "music_bed": mix_result.get("bed_path"),
                "mix": mix_result["mix_path"]
            },
            "lufs": mix_result["lufs"],
            "ducking_db": mix_result["ducking_db"],
            "stretch_used": narration_result["stretch_used"]
        }
        
        # Verify structure matches job_summary.json spec
        assert audio_metadata["language"] == "hi"
        assert audio_metadata["provider"] in ["azure", "elevenlabs", "fallback"]
        assert len(audio_metadata["files"]["per_scene"]) == 2
        assert audio_metadata["lufs"] is not None
        assert audio_metadata["ducking_db"] <= 0
        assert audio_metadata["stretch_used"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
