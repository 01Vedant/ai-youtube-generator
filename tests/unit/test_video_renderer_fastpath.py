"""
Unit tests for VideoRenderer fast-path functionality.
Mocks ffmpeg subprocess calls and verifies NVENC/fallback behavior.
"""
import os
import pytest
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path
import subprocess

# Add pipeline to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pipeline.video_renderer import VideoRenderer


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create temporary output directory."""
    output_dir = tmp_path / "renders"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def mock_images(tmp_path):
    """Create mock image files."""
    images_dir = tmp_path / "images"
    images_dir.mkdir()
    
    image_paths = []
    for i in range(3):
        img_path = images_dir / f"scene_{i}.jpg"
        img_path.write_text("fake image data")
        image_paths.append(img_path)
    
    return image_paths


@pytest.fixture
def mock_audio(tmp_path):
    """Create mock audio file."""
    audio_path = tmp_path / "audio.mp3"
    audio_path.write_text("fake audio data")
    return audio_path


class TestVideoRendererNVENCDetection:
    """Test NVENC availability detection."""
    
    @patch('subprocess.run')
    def test_nvenc_available(self, mock_run, temp_output_dir):
        """Test NVENC detected as available."""
        mock_run.return_value = Mock(stdout="h264_nvenc NVIDIA NVENC H.264 encoder")
        
        renderer = VideoRenderer(temp_output_dir)
        
        assert renderer.nvenc_available is True
        mock_run.assert_called_once()
        assert "ffmpeg" in mock_run.call_args[0][0]
        assert "-encoders" in mock_run.call_args[0][0]
    
    @patch('subprocess.run')
    def test_nvenc_not_available(self, mock_run, temp_output_dir):
        """Test NVENC not detected."""
        mock_run.return_value = Mock(stdout="libx264 H.264 / AVC / MPEG-4 AVC")
        
        renderer = VideoRenderer(temp_output_dir)
        
        assert renderer.nvenc_available is False
    
    @patch('subprocess.run')
    def test_nvenc_check_timeout(self, mock_run, temp_output_dir):
        """Test NVENC check handles timeout gracefully."""
        mock_run.side_effect = subprocess.TimeoutExpired("ffmpeg", 5)
        
        renderer = VideoRenderer(temp_output_dir)
        
        assert renderer.nvenc_available is False


class TestVideoRendererSceneCaching:
    """Test scene caching via deterministic hashing."""
    
    def test_scene_hash_deterministic(self, temp_output_dir):
        """Test scene hash is deterministic for same inputs."""
        renderer = VideoRenderer(temp_output_dir)
        
        hash1 = renderer._get_scene_hash("/path/to/image.jpg", "Narration text", 3.0)
        hash2 = renderer._get_scene_hash("/path/to/image.jpg", "Narration text", 3.0)
        
        assert hash1 == hash2
        assert len(hash1) == 16  # SHA256 truncated to 16 chars
    
    def test_scene_hash_changes_on_input_change(self, temp_output_dir):
        """Test scene hash changes when inputs change."""
        renderer = VideoRenderer(temp_output_dir)
        
        hash1 = renderer._get_scene_hash("/path/to/image.jpg", "Narration text", 3.0)
        hash2 = renderer._get_scene_hash("/path/to/image.jpg", "Different text", 3.0)
        hash3 = renderer._get_scene_hash("/path/to/image.jpg", "Narration text", 5.0)
        
        assert hash1 != hash2
        assert hash1 != hash3
        assert hash2 != hash3


class TestVideoRendererFastPath:
    """Test fast-path rendering with ffmpeg."""
    
    @patch('subprocess.run')
    @patch('subprocess.run')
    def test_render_with_nvenc(self, mock_nvenc_check, mock_render, temp_output_dir, mock_images, mock_audio):
        """Test fast-path render with NVENC encoder."""
        # Mock NVENC available
        mock_nvenc_check.return_value = Mock(stdout="h264_nvenc NVIDIA NVENC H.264 encoder")
        
        renderer = VideoRenderer(temp_output_dir, fps=30)
        
        # Mock ffmpeg subprocess calls
        mock_render.return_value = Mock(returncode=0, stdout="", stderr="")
        
        result = renderer.render(
            job_id="test_job",
            image_paths=mock_images,
            durations=[3.0, 3.0, 3.0],
            audio_path=mock_audio,
            narrations=["Scene 1", "Scene 2", "Scene 3"],
            fast_path=True,
            encoder="h264_nvenc",
            target_res="1080p",
            render_mode="FINAL"
        )
        
        # Verify result metadata
        assert result["fast_path"] is True
        assert result["encoder"] == "h264_nvenc"
        assert result["resolution"] == "1080p"
        assert result["render_mode"] == "FINAL"
        assert "timings" in result
        assert "scene_rendering_sec" in result["timings"]
        assert "concat_sec" in result["timings"]
        
        # Verify ffmpeg was called (once for each scene + concat)
        assert mock_render.call_count >= 4  # 3 scenes + 1 concat
        
        # Check that NVENC flags were used
        calls = mock_render.call_args_list
        scene_call = calls[0][0][0]  # First call args
        assert "h264_nvenc" in scene_call
        assert "-rc:v" in scene_call
        assert "vbr" in scene_call
    
    @patch('subprocess.run')
    def test_render_fallback_to_libx264(self, mock_run, temp_output_dir, mock_images, mock_audio):
        """Test automatic fallback to libx264 when NVENC unavailable."""
        # Mock NVENC not available
        mock_run.return_value = Mock(stdout="libx264 H.264")
        
        renderer = VideoRenderer(temp_output_dir)
        
        # Reset mock for render calls
        mock_run.reset_mock()
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        
        result = renderer.render(
            job_id="test_job",
            image_paths=mock_images,
            durations=[3.0, 3.0, 3.0],
            audio_path=mock_audio,
            narrations=["Scene 1", "Scene 2", "Scene 3"],
            fast_path=True,
            encoder="h264_nvenc"  # Request NVENC but will fallback
        )
        
        # Verify fallback to libx264
        assert result["encoder"] == "libx264"
        
        # Check that libx264 flags were used (CRF not VBR)
        calls = mock_run.call_args_list
        scene_call = calls[0][0][0]
        assert "libx264" in scene_call
        assert "-crf" in scene_call
    
    @patch('subprocess.run')
    def test_render_proxy_vs_final_mode(self, mock_run, temp_output_dir, mock_images, mock_audio):
        """Test PROXY mode uses faster settings than FINAL mode."""
        mock_run.return_value = Mock(stdout="h264_nvenc", returncode=0, stderr="")
        
        renderer = VideoRenderer(temp_output_dir)
        mock_run.reset_mock()
        
        # Render in PROXY mode
        renderer.render(
            job_id="test_proxy",
            image_paths=[mock_images[0]],
            durations=[3.0],
            narrations=["Test"],
            fast_path=True,
            encoder="h264_nvenc",
            render_mode="PROXY"
        )
        
        proxy_calls = mock_run.call_args_list.copy()
        mock_run.reset_mock()
        
        # Render in FINAL mode
        renderer.render(
            job_id="test_final",
            image_paths=[mock_images[0]],
            durations=[3.0],
            narrations=["Test"],
            fast_path=True,
            encoder="h264_nvenc",
            render_mode="FINAL"
        )
        
        final_calls = mock_run.call_args_list
        
        # Verify PROXY uses "fast" preset and FINAL uses "slow"
        proxy_cmd = proxy_calls[0][0][0]
        final_cmd = final_calls[0][0][0]
        
        assert "fast" in proxy_cmd
        assert "slow" in final_cmd
    
    @patch('subprocess.run')
    @patch('moviepy.editor.ImageClip')
    @patch('moviepy.editor.concatenate_videoclips')
    def test_fallback_to_moviepy_on_ffmpeg_failure(
        self, mock_concat, mock_imageclip, mock_run, temp_output_dir, mock_images, mock_audio
    ):
        """Test fallback to MoviePy when fast-path fails."""
        # Mock NVENC available but ffmpeg fails
        mock_run.side_effect = [
            Mock(stdout="h264_nvenc"),  # NVENC check succeeds
            subprocess.CalledProcessError(1, "ffmpeg", stderr="NVENC error")  # Render fails
        ]
        
        # Mock MoviePy
        mock_clip = MagicMock()
        mock_clip.set_duration.return_value = mock_clip
        mock_imageclip.return_value = mock_clip
        mock_concat.return_value = mock_clip
        
        renderer = VideoRenderer(temp_output_dir)
        
        result = renderer.render(
            job_id="test_fallback",
            image_paths=mock_images,
            durations=[3.0, 3.0, 3.0],
            audio_path=mock_audio,
            fast_path=True
        )
        
        # Verify MoviePy fallback was used
        assert result["fast_path"] is False
        assert result["encoder"] == "libx264"
        assert result["render_mode"] == "moviepy"
        mock_imageclip.assert_called()
        mock_concat.assert_called_once()


class TestVideoRendererFilterComplex:
    """Test filter_complex assembly for watermark/audio/subtitles."""
    
    @patch('subprocess.run')
    def test_render_with_watermark(self, mock_run, temp_output_dir, mock_images, mock_audio, tmp_path):
        """Test watermark overlay in filter_complex."""
        mock_run.return_value = Mock(stdout="h264_nvenc", returncode=0, stderr="")
        
        watermark_path = tmp_path / "watermark.png"
        watermark_path.write_text("fake watermark")
        
        renderer = VideoRenderer(temp_output_dir)
        mock_run.reset_mock()
        
        renderer.render(
            job_id="test_watermark",
            image_paths=[mock_images[0]],
            durations=[3.0],
            audio_path=mock_audio,
            watermark=watermark_path,
            narrations=["Test"],
            fast_path=True,
            watermark_pos="br"
        )
        
        # Check concat call for filter_complex with overlay
        concat_call = [c for c in mock_run.call_args_list if "concat" in str(c)][0]
        concat_cmd = concat_call[0][0]
        
        assert "-filter_complex" in concat_cmd
        assert "overlay=" in str(concat_cmd)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
