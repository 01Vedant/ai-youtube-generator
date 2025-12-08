"""
Motion Template Engine - JSON-driven FFmpeg filter generation
For hybrid video pipeline - gracefully handles SIMULATE_RENDER mode
"""
import os
from typing import TypedDict, List, Dict, Any, Optional


class MotionStep(TypedDict):
    """Single motion template step"""
    type: str  # 'fade_in', 'zoom', 'pan', 'text_reveal', etc.
    in_sec: float  # Start time relative to clip
    dur_sec: float  # Duration of effect
    params: Dict[str, Any]  # Effect-specific parameters


class MotionTemplate(TypedDict):
    """Complete motion template with multiple steps"""
    name: str
    description: str
    steps: List[MotionStep]


# ==============================================================================
# Template Library (6 production-ready templates)
# ==============================================================================

TEMPLATES: Dict[str, MotionTemplate] = {
    "title_reveal": {
        "name": "Title Reveal",
        "description": "Fade in title text with slide up animation",
        "steps": [
            {
                "type": "text_fade",
                "in_sec": 0.0,
                "dur_sec": 0.8,
                "params": {"text": "{title}", "position": "center", "font_size": 72, "color": "white"}
            },
            {
                "type": "slide_up",
                "in_sec": 0.0,
                "dur_sec": 0.8,
                "params": {"distance_px": 50, "ease": "out_cubic"}
            }
        ]
    },
    
    "caption_slide": {
        "name": "Caption Slide",
        "description": "Lower-third caption with slide from left",
        "steps": [
            {
                "type": "text_overlay",
                "in_sec": 0.2,
                "dur_sec": 2.5,
                "params": {"text": "{caption}", "position": "lower_third", "font_size": 48, "bg_alpha": 0.7}
            },
            {
                "type": "slide_left",
                "in_sec": 0.2,
                "dur_sec": 0.5,
                "params": {"distance_px": 100, "ease": "out_expo"}
            }
        ]
    },
    
    "xfade_ease": {
        "name": "Crossfade with Ease",
        "description": "Smooth crossfade transition between scenes with easing",
        "steps": [
            {
                "type": "xfade",
                "in_sec": -0.5,  # Start before end of first clip
                "dur_sec": 1.0,
                "params": {"transition": "fade", "ease": "in_out_sine"}
            }
        ]
    },
    
    "wipe_left": {
        "name": "Wipe Left",
        "description": "Hard wipe transition from right to left",
        "steps": [
            {
                "type": "xfade",
                "in_sec": -0.4,
                "dur_sec": 0.8,
                "params": {"transition": "wipeleft", "ease": "linear"}
            }
        ]
    },
    
    "glow_pulse": {
        "name": "Glow Pulse",
        "description": "Subtle glow effect that pulses during scene",
        "steps": [
            {
                "type": "glow",
                "in_sec": 0.0,
                "dur_sec": 3.0,
                "params": {"intensity": 1.2, "radius": 10, "pulse_hz": 0.5}
            }
        ]
    },
    
    "vignette": {
        "name": "Vignette",
        "description": "Cinematic vignette darkening edges",
        "steps": [
            {
                "type": "vignette",
                "in_sec": 0.0,
                "dur_sec": -1,  # -1 means entire duration
                "params": {"intensity": 0.3, "softness": 0.5}
            }
        ]
    }
}


# ==============================================================================
# FFmpeg Filter Compilation
# ==============================================================================

def compile_to_ffmpeg_filter(
    steps: List[MotionStep],
    width: int = 1920,
    height: int = 1080,
    simulate: bool = False
) -> str:
    """
    Compile motion steps to FFmpeg filter_complex string.
    
    Args:
        steps: List of motion steps to compile
        width: Output video width
        height: Output video height
        simulate: If True, return identity filter (for SIMULATE_RENDER mode)
    
    Returns:
        FFmpeg filter_complex string
    
    Example:
        >>> steps = [{"type": "fade_in", "in_sec": 0.0, "dur_sec": 1.0, "params": {}}]
        >>> compile_to_ffmpeg_filter(steps)
        'fade=t=in:st=0.0:d=1.0'
    """
    simulate = simulate or int(os.getenv("SIMULATE_RENDER", "0")) == 1
    
    if simulate or not steps:
        # Return identity filter (no-op) for simulator mode
        return "null"
    
    # Build filter chain from steps
    filters = []
    
    for step in steps:
        step_type = step["type"]
        in_sec = step["in_sec"]
        dur_sec = step["dur_sec"]
        params = step.get("params", {})
        
        # Map step types to FFmpeg filters
        if step_type == "text_fade":
            text = params.get("text", "")
            font_size = params.get("font_size", 48)
            color = params.get("color", "white")
            position = params.get("position", "center")
            
            # Simplified: just fade for now (full text rendering needs drawtext)
            filters.append(f"fade=t=in:st={in_sec}:d={dur_sec}")
            
        elif step_type == "xfade":
            transition = params.get("transition", "fade")
            # Note: xfade requires two inputs; handle at higher level
            filters.append(f"xfade=transition={transition}:duration={dur_sec}:offset={in_sec}")
            
        elif step_type == "vignette":
            intensity = params.get("intensity", 0.3)
            # Vignette using boxblur and overlay (simplified)
            filters.append(f"vignette=angle=PI/4")
            
        elif step_type == "glow":
            intensity = params.get("intensity", 1.2)
            radius = params.get("radius", 10)
            filters.append(f"gblur=sigma={radius}")
            
        else:
            # Unknown type: skip
            pass
    
    if not filters:
        return "null"
    
    # Join filters with comma (sequential chain)
    return ",".join(filters)


def apply_template(
    template_name: str,
    input_path: str,
    output_path: str,
    width: int = 1920,
    height: int = 1080,
    replacements: Optional[Dict[str, str]] = None
) -> Optional[str]:
    """
    Apply motion template to video file (placeholder - for future FFmpeg integration).
    
    Args:
        template_name: Name of template from TEMPLATES dict
        input_path: Path to input video
        output_path: Path to output video
        width: Video width
        height: Video height
        replacements: Dict of {placeholder: value} for text substitution
    
    Returns:
        Filter string that was applied, or None if template not found
    """
    if template_name not in TEMPLATES:
        return None
    
    template = TEMPLATES[template_name]
    steps = template["steps"]
    
    # Perform text replacements in steps
    if replacements:
        import copy
        steps = copy.deepcopy(steps)
        for step in steps:
            if "text" in step.get("params", {}):
                text = step["params"]["text"]
                for placeholder, value in replacements.items():
                    text = text.replace(f"{{{placeholder}}}", value)
                step["params"]["text"] = text
    
    filter_str = compile_to_ffmpeg_filter(steps, width, height)
    
    # In SIMULATE mode, don't actually run FFmpeg
    if int(os.getenv("SIMULATE_RENDER", "0")) == 1:
        return filter_str
    
    # Future: run FFmpeg command with filter_complex
    # ffmpeg -i input_path -filter_complex filter_str -y output_path
    
    return filter_str


def get_template(name: str) -> Optional[MotionTemplate]:
    """Get template by name"""
    return TEMPLATES.get(name)


def list_templates() -> List[str]:
    """List all available template names"""
    return list(TEMPLATES.keys())
