"""
Safety guardrails: input validation, quotas, cost guards.
"""
import logging
import re
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)


class QuotaExceeded(Exception):
    """Raised when quota limits are exceeded."""
    pass


class ValidationError_(Exception):
    """Raised when input validation fails."""
    pass


def sanitize_text(text: str, max_length: int = 5000) -> str:
    """Sanitize text: remove HTML, trim whitespace, enforce length."""
    if not text or not isinstance(text, str):
        raise ValidationError_("Text must be non-empty string")
    
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    
    # Trim whitespace
    text = text.strip()
    
    # Enforce length
    if len(text) > max_length:
        raise ValidationError_(f"Text exceeds max length of {max_length} characters")
    
    if not text:
        raise ValidationError_("Text cannot be empty after sanitization")
    
    return text


def validate_render_plan(plan: Dict[str, Any], config: Any) -> Tuple[bool, str]:
    """
    Validate render plan against quotas and safety guardrails.
    
    Args:
        plan: RenderPlan dict
        config: Settings object with quota limits
    
    Returns:
        (is_valid, error_message)
    """
    errors = []

    # Validate scenes
    scenes = plan.get("scenes", [])
    
    if not scenes:
        errors.append("At least one scene is required")
    
    if len(scenes) > config.MAX_SCENES:
        errors.append(f"Maximum {config.MAX_SCENES} scenes allowed; got {len(scenes)}")
    
    # Validate each scene
    total_duration = 0
    for i, scene in enumerate(scenes):
        # Validate prompt
        try:
            if "prompt" in scene:
                sanitize_text(scene["prompt"], max_length=1000)
        except ValidationError_ as e:
            errors.append(f"Scene {i}: Invalid prompt: {e}")
        
        # Validate narration
        try:
            if "narration" in scene:
                narration = scene["narration"]
                if not narration or not isinstance(narration, str):
                    errors.append(f"Scene {i}: Narration must be non-empty string")
                else:
                    sanitize_text(narration, max_length=2000)
        except ValidationError_ as e:
            errors.append(f"Scene {i}: Invalid narration: {e}")
        
        # Validate duration
        duration = scene.get("duration", 0)
        if duration <= 0 or duration > config.MAX_SCENE_DURATION_SEC:
            errors.append(
                f"Scene {i}: Duration must be 1-{config.MAX_SCENE_DURATION_SEC}s; got {duration}s"
            )
        
        total_duration += duration
    
    # Validate total duration
    if total_duration > config.MAX_TOTAL_DURATION_SEC:
        errors.append(
            f"Total duration exceeds max {config.MAX_TOTAL_DURATION_SEC}s; got {total_duration}s"
        )
    
    # Validate topic (optional but if provided, should be sanitized)
    if "topic" in plan:
        try:
            sanitize_text(plan["topic"], max_length=500)
        except ValidationError_ as e:
            errors.append(f"Invalid topic: {e}")
    
    # Validate language (whitelist)
    language = plan.get("language", "en")
    allowed_languages = ["en", "hi", "sa"]
    if language not in allowed_languages:
        errors.append(f"Language must be one of {allowed_languages}; got {language}")
    
    # Validate voice (whitelist)
    voice = plan.get("voice", "F")
    allowed_voices = ["M", "F", "male", "female", "aria", "sagara", "daya"]
    if voice not in allowed_voices:
        errors.append(f"Voice must be one of {allowed_voices}; got {voice}")

    if errors:
        return False, "; ".join(errors)
    
    return True, ""


def estimate_cost(plan: Dict[str, Any], config: Any) -> float:
    """
    Estimate cost of rendering based on scenes, resolution, engines.
    Returns cost in USD.
    """
    scenes = plan.get("scenes", [])
    num_scenes = len(scenes)
    
    # Base costs (in USD)
    cost = 0.0
    
    # Image generation: ~$0.04-0.20 per image depending on engine/quality
    image_engine = plan.get("image_engine", "openai")
    image_quality = plan.get("image_quality", "preview")
    
    if image_engine == "openai":
        cost += num_scenes * (0.20 if image_quality == "final" else 0.04)
    elif image_engine == "sdxl":
        cost += num_scenes * (0.10 if image_quality == "final" else 0.02)
    else:
        cost += 0  # local/free engines
    
    # TTS: ~$0.015 per 1K characters for elevenlabs
    tts_engine = plan.get("tts_engine", "elevenlabs")
    if tts_engine == "elevenlabs":
        total_chars = sum(len(scene.get("narration", "")) for scene in scenes)
        cost += (total_chars / 1000) * 0.015
    
    # Video rendering: flat fee based on resolution
    video_resolution = plan.get("video_resolution", "1080p")
    if video_resolution == "4k":
        cost += 0.50
    elif video_resolution == "1080p":
        cost += 0.25
    else:
        cost += 0.10
    
    return round(cost, 3)


def check_cost_guard(cost_estimate: float, max_job_cost: float) -> Tuple[bool, str]:
    """
    Check if cost exceeds max allowed per job.
    
    Returns:
        (is_allowed, message)
    """
    if cost_estimate > max_job_cost:
        return False, f"Estimated cost ${cost_estimate:.2f} exceeds max ${max_job_cost:.2f}"
    return True, ""
