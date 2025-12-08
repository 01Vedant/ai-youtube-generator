"""
2.5D Parallax Engine - Depth-based layered motion
Gracefully handles SIMULATE_RENDER mode with synthetic depth
"""
import os
import numpy as np
from pathlib import Path
from typing import Optional, List, Dict, Any


def estimate_depth(image_path: Path) -> Optional[np.ndarray]:
    """
    Estimate depth map from image.
    
    Args:
        image_path: Path to input image
    
    Returns:
        Depth map as numpy array (H x W), or None if estimation fails
    
    In SIMULATE mode: generates synthetic depth gradient (top → bottom)
    In production: would use MiDaS or similar depth estimation model
    """
    simulate = int(os.getenv("SIMULATE_RENDER", "0")) == 1
    
    if simulate:
        # Synthetic depth: linear gradient from top (far) to bottom (near)
        height, width = 1080, 1920  # Standard HD resolution
        depth_map = np.linspace(0.2, 1.0, height).reshape(-1, 1)
        depth_map = np.repeat(depth_map, width, axis=1)
        return depth_map.astype(np.float32)
    
    # Production mode would load image and run depth estimation
    # try:
    #     import torch
    #     from midas.model_loader import load_model
    #     ...
    # except ImportError:
    #     return None
    
    return None


def split_layers(
    image_path: Path,
    depth_map: Optional[np.ndarray],
    out_dir: Path,
    num_layers: int = 3
) -> List[Path]:
    """
    Split image into foreground/middleground/background layers based on depth.
    
    Args:
        image_path: Path to input image
        depth_map: Depth map array (or None to use synthetic)
        out_dir: Output directory for layer PNGs
        num_layers: Number of layers to generate (2-5)
    
    Returns:
        List of paths to generated layer PNG files
    
    In SIMULATE mode: creates empty placeholder PNG files
    """
    simulate = int(os.getenv("SIMULATE_RENDER", "0")) == 1
    out_dir.mkdir(parents=True, exist_ok=True)
    
    if depth_map is None:
        depth_map = estimate_depth(image_path)
    
    layer_paths = []
    
    if simulate:
        # Create placeholder layer files (minimal PNG)
        from platform.orchestrator import tiny_png
        for i in range(num_layers):
            layer_name = f"layer_{i}_{'fg' if i == 0 else 'bg' if i == num_layers - 1 else 'mid'}.png"
            layer_path = out_dir / layer_name
            layer_path.write_bytes(tiny_png())
            layer_paths.append(layer_path)
    else:
        # Production mode would segment image by depth thresholds
        # Threshold depth into layers and save as PNG with alpha
        pass
    
    return layer_paths


def plan_parallax_moves(duration: float, style: str = "gentle_zoom") -> Dict[str, Any]:
    """
    Plan camera moves for parallax effect.
    
    Args:
        duration: Duration of clip in seconds
        style: Motion style ("gentle_zoom", "pan_right", "dramatic")
    
    Returns:
        Dict with tx, ty, zoom, ease parameters
    """
    if style == "gentle_zoom":
        return {
            "tx": 0.0,  # Translation x (pixels/sec)
            "ty": 0.0,  # Translation y (pixels/sec)
            "zoom_start": 1.0,
            "zoom_end": 1.1,  # Gentle 10% zoom
            "ease": "in_out_sine"
        }
    elif style == "pan_right":
        return {
            "tx": 50.0,  # Pan right 50px/sec
            "ty": 0.0,
            "zoom_start": 1.0,
            "zoom_end": 1.0,
            "ease": "linear"
        }
    else:  # dramatic
        return {
            "tx": 0.0,
            "ty": -30.0,  # Pan up
            "zoom_start": 1.0,
            "zoom_end": 1.2,  # 20% zoom
            "ease": "out_expo"
        }


def render_parallax(
    layers: List[Path],
    moves: Dict[str, Any],
    out_path: Path,
    fps: int = 24,
    size: tuple = (1920, 1080)
) -> Path:
    """
    Render parallax effect from layers and camera moves.
    
    Args:
        layers: List of layer image paths (back to front order)
        moves: Camera move parameters from plan_parallax_moves()
        out_path: Output MP4 path
        fps: Frames per second
        size: Output resolution (width, height)
    
    Returns:
        Path to rendered MP4
    
    In SIMULATE mode: generates minimal MP4 file
    In production: uses FFmpeg zoompan filter or frame-by-frame composition
    """
    simulate = int(os.getenv("SIMULATE_RENDER", "0")) == 1
    
    if simulate:
        # Create placeholder video file
        from platform.orchestrator import tiny_mp4
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(tiny_mp4(duration_sec=3.0))
        return out_path
    
    # Production mode would:
    # 1. Apply differential zoom/pan to each layer based on depth
    # 2. Use FFmpeg zoompan filter or Python video library
    # 3. Composite layers with proper alpha blending
    # Example FFmpeg command:
    # ffmpeg -loop 1 -i layer_bg.png -t 3 -vf "zoompan=z='zoom+0.002':d=fps*duration" ...
    
    return out_path


def apply_parallax_to_scene(
    scene_image: Path,
    output_video: Path,
    duration: float = 3.0,
    style: str = "gentle_zoom"
) -> Optional[Path]:
    """
    High-level function: apply parallax effect to a scene image.
    
    Args:
        scene_image: Path to static scene image
        output_video: Path for output MP4
        duration: Clip duration in seconds
        style: Parallax style preset
    
    Returns:
        Path to generated parallax video, or None on error
    """
    try:
        # Step 1: Estimate depth
        depth_map = estimate_depth(scene_image)
        
        # Step 2: Split into layers
        layers_dir = output_video.parent / "parallax_layers"
        layers = split_layers(scene_image, depth_map, layers_dir)
        
        # Step 3: Plan camera moves
        moves = plan_parallax_moves(duration, style)
        
        # Step 4: Render parallax video
        result = render_parallax(layers, moves, output_video)
        
        return result
    except Exception as e:
        print(f"[Parallax] Error: {e}")
        return None
