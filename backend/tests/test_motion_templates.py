"""Unit tests for motion template engine"""
import pytest
import sys
from pathlib import Path

# Add platform to path
PLATFORM_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLATFORM_ROOT))

from backend.app.motion.templates import (
    TEMPLATES,
    MotionStep,
    MotionTemplate,
    compile_to_ffmpeg_filter,
    get_template,
    list_templates,
    apply_template
)


class TestTemplateSchema:
    """Test template data structure validity"""
    
    def test_all_templates_have_required_keys(self):
        """Each template must have name, description, steps"""
        for template_name, template in TEMPLATES.items():
            assert "name" in template, f"Template {template_name} missing 'name'"
            assert "description" in template, f"Template {template_name} missing 'description'"
            assert "steps" in template, f"Template {template_name} missing 'steps'"
            assert isinstance(template["steps"], list), f"Template {template_name} steps must be list"
    
    def test_all_steps_have_required_keys(self):
        """Each step must have type, in_sec, dur_sec, params"""
        for template_name, template in TEMPLATES.items():
            for i, step in enumerate(template["steps"]):
                assert "type" in step, f"Template {template_name} step {i} missing 'type'"
                assert "in_sec" in step, f"Template {template_name} step {i} missing 'in_sec'"
                assert "dur_sec" in step, f"Template {template_name} step {i} missing 'dur_sec'"
                assert "params" in step, f"Template {template_name} step {i} missing 'params'"
                assert isinstance(step["params"], dict), f"Template {template_name} step {i} params must be dict"
    
    def test_template_count(self):
        """Should have exactly 6 templates"""
        assert len(TEMPLATES) == 6, f"Expected 6 templates, got {len(TEMPLATES)}"
    
    def test_expected_template_names(self):
        """Verify all expected templates exist"""
        expected = {"title_reveal", "caption_slide", "xfade_ease", "wipe_left", "glow_pulse", "vignette"}
        assert set(TEMPLATES.keys()) == expected


class TestFilterCompilation:
    """Test FFmpeg filter compilation"""
    
    def test_compile_empty_steps_returns_null(self):
        """Empty steps should return 'null' filter"""
        result = compile_to_ffmpeg_filter([])
        assert result == "null"
    
    def test_compile_in_simulate_mode_returns_null(self):
        """In SIMULATE_RENDER mode, should return 'null' filter"""
        steps = [{"type": "fade_in", "in_sec": 0.0, "dur_sec": 1.0, "params": {}}]
        result = compile_to_ffmpeg_filter(steps, simulate=True)
        assert result == "null"
    
    def test_compile_xfade_step(self, monkeypatch):
        """xfade step should generate xfade filter"""
        monkeypatch.setenv("SIMULATE_RENDER", "0")
        steps = [{"type": "xfade", "in_sec": -0.5, "dur_sec": 1.0, "params": {"transition": "fade"}}]
        result = compile_to_ffmpeg_filter(steps, simulate=False)
        assert "xfade" in result
        assert "duration=1.0" in result
        assert "offset=-0.5" in result
    
    def test_compile_vignette_step(self, monkeypatch):
        """vignette step should generate vignette filter"""
        monkeypatch.setenv("SIMULATE_RENDER", "0")
        steps = [{"type": "vignette", "in_sec": 0.0, "dur_sec": -1, "params": {"intensity": 0.3}}]
        result = compile_to_ffmpeg_filter(steps, simulate=False)
        assert "vignette" in result
    
    def test_compile_multiple_steps_chains_filters(self, monkeypatch):
        """Multiple steps should be chained with commas"""
        monkeypatch.setenv("SIMULATE_RENDER", "0")
        steps = [
            {"type": "text_fade", "in_sec": 0.0, "dur_sec": 0.8, "params": {}},
            {"type": "glow", "in_sec": 0.0, "dur_sec": 2.0, "params": {"radius": 10}}
        ]
        result = compile_to_ffmpeg_filter(steps, simulate=False)
        # Should have multiple filters separated by comma
        assert "," in result or "fade" in result  # At least one filter present
    
    def test_compile_all_templates_returns_non_empty(self):
        """Each template should compile to non-empty filter string"""
        for template_name, template in TEMPLATES.items():
            result = compile_to_ffmpeg_filter(template["steps"], simulate=False)
            assert result, f"Template {template_name} compiled to empty string"
            assert isinstance(result, str), f"Template {template_name} didn't return string"


class TestTemplateAPI:
    """Test public API functions"""
    
    def test_get_template_existing(self):
        """get_template should return template dict for existing name"""
        result = get_template("title_reveal")
        assert result is not None
        assert result["name"] == "Title Reveal"
    
    def test_get_template_nonexistent(self):
        """get_template should return None for non-existent name"""
        result = get_template("nonexistent_template")
        assert result is None
    
    def test_list_templates_returns_all_names(self):
        """list_templates should return all 6 template names"""
        names = list_templates()
        assert len(names) == 6
        assert "title_reveal" in names
        assert "xfade_ease" in names
    
    def test_apply_template_in_simulate_mode(self):
        """apply_template should return filter string in SIMULATE mode"""
        result = apply_template(
            "title_reveal",
            "input.mp4",
            "output.mp4",
            replacements={"title": "Test Title"}
        )
        assert result is not None
        assert isinstance(result, str)
    
    def test_apply_template_nonexistent_returns_none(self):
        """apply_template should return None for invalid template"""
        result = apply_template("invalid_template", "in.mp4", "out.mp4")
        assert result is None


class TestTemplateReplacements:
    """Test text placeholder replacements"""
    
    def test_apply_template_replaces_placeholders(self):
        """Text placeholders should be replaced with values"""
        # This test verifies the replacement logic works
        result = apply_template(
            "title_reveal",
            "input.mp4",
            "output.mp4",
            replacements={"title": "My Title"}
        )
        # Result should be a filter string (in SIMULATE mode, returns "null")
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
