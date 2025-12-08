"""
Thumbnail composer: generate 1280x720 PNG thumbnails with title, glow, and watermark.
"""

import logging
from pathlib import Path
from typing import Optional, Tuple
import re

logger = logging.getLogger(__name__)


def compose_thumbnail(
    first_image_path: str,
    title: str,
    output_path: Optional[str] = None,
    language: str = "en",
    watermark_path: Optional[str] = None,
) -> str:
    """
    Compose a YouTube-optimized 1280x720 thumbnail from first scene image and title.
    
    Args:
        first_image_path: Path to first scene image
        title: Video title (will be split into lines)
        output_path: Where to save thumbnail (default: temp)
        language: 'en' or 'hi' (affects text styling)
        watermark_path: Optional path to watermark image
    
    Returns:
        Path to generated thumbnail PNG
    """
    try:
        from PIL import Image, ImageDraw, ImageFilter, ImageFont
    except ImportError:
        logger.error("PIL/Pillow not installed. Install with: pip install Pillow")
        raise
    
    # Thumbnail dimensions (YouTube standard)
    THUMB_WIDTH = 1280
    THUMB_HEIGHT = 720
    
    if output_path is None:
        import tempfile
        output_path = str(Path(tempfile.gettempdir()) / "thumbnail.png")
    
    output_path = str(output_path)
    
    try:
        # Load and resize base image
        img = Image.open(first_image_path).convert("RGB")
        img.thumbnail((THUMB_WIDTH, THUMB_HEIGHT), Image.Resampling.LANCZOS)
        
        # Create base canvas with image
        canvas = Image.new("RGB", (THUMB_WIDTH, THUMB_HEIGHT), color=(0, 0, 0))
        
        # Center the image on canvas
        img_x = (THUMB_WIDTH - img.width) // 2
        img_y = (THUMB_HEIGHT - img.height) // 2
        canvas.paste(img, (img_x, img_y))
        
    except Exception as e:
        logger.error("Failed to load/resize base image: %s", e)
        raise
    
    # Draw semi-transparent overlay for text readability
    draw = ImageDraw.Draw(canvas, "RGBA")
    
    # Dark overlay at bottom
    overlay_color = (0, 0, 0, 180)  # Black with 70% opacity
    draw.rectangle(
        [(0, THUMB_HEIGHT - 280), (THUMB_WIDTH, THUMB_HEIGHT)],
        fill=overlay_color
    )
    
    # Add subtle glow/border effect
    try:
        # Load font (fallback to default if not found)
        if language == "hi":
            # Try to load a font that supports Devanagari
            try:
                title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 64)
                subtitle_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
            except Exception:
                title_font = ImageFont.load_default()
                subtitle_font = ImageFont.load_default()
        else:
            try:
                title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 64)
                subtitle_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
            except Exception:
                title_font = ImageFont.load_default()
                subtitle_font = ImageFont.load_default()
    except Exception as e:
        logger.warning("Font loading failed, using default: %s", e)
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
    
    # Normalize title: remove HTML, truncate
    title = re.sub(r'<[^>]+>', '', title)
    title = title.strip()[:100]
    
    # Split title into lines (max 2 lines, ~20 chars each)
    lines = []
    words = title.split()
    current_line = ""
    for word in words:
        if len(current_line) + len(word) + 1 <= 30:
            current_line += " " + word if current_line else word
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
            if len(lines) >= 2:
                break
    if current_line and len(lines) < 2:
        lines.append(current_line)
    
    # Draw text
    text_x = 60
    text_y = THUMB_HEIGHT - 240
    text_color = (255, 255, 255, 255)  # White
    
    for i, line in enumerate(lines):
        y_offset = i * 80
        
        # Draw shadow/outline for better readability
        shadow_color = (0, 0, 0, 200)
        for adj_x, adj_y in [(-2, -2), (2, -2), (-2, 2), (2, 2)]:
            draw.text(
                (text_x + adj_x, text_y + y_offset + adj_y),
                line,
                font=title_font,
                fill=shadow_color,
            )
        
        # Draw main text
        draw.text(
            (text_x, text_y + y_offset),
            line,
            font=title_font,
            fill=text_color,
        )
    
    # Add subtle branding/watermark in corner
    if watermark_path and Path(watermark_path).exists():
        try:
            watermark = Image.open(watermark_path).convert("RGBA")
            watermark.thumbnail((120, 60), Image.Resampling.LANCZOS)
            # Reduce opacity
            alpha = watermark.split()[3]
            alpha = alpha.point(lambda p: int(p * 0.6))  # 60% opacity
            watermark.putalpha(alpha)
            canvas.paste(watermark, (THUMB_WIDTH - 140, THUMB_HEIGHT - 80), watermark)
        except Exception as e:
            logger.warning("Failed to add watermark: %s", e)
    else:
        # Add simple text watermark
        watermark_text = "DevotionalAI"
        try:
            wm_font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24
            )
        except Exception:
            wm_font = ImageFont.load_default()
        
        draw.text(
            (THUMB_WIDTH - 200, THUMB_HEIGHT - 50),
            watermark_text,
            font=wm_font,
            fill=(200, 200, 200, 120),
        )
    
    # Save
    canvas.save(output_path, "PNG", quality=95)
    logger.info("Thumbnail composed: %s (%dx%d)", output_path, THUMB_WIDTH, THUMB_HEIGHT)
    
    return output_path


def generate_thumbnail_from_plan(
    plan: dict,
    first_image_path: str,
    output_dir: Optional[Path] = None,
) -> str:
    """
    Convenience wrapper: generate thumbnail from a RenderPlan and first image.
    
    Args:
        plan: RenderPlan dictionary
        first_image_path: Path to first scene image
        output_dir: Where to save (default: temp)
    
    Returns:
        Path to generated thumbnail
    """
    title = plan.get("topic", "DevotionalAI Video")
    language = plan.get("language", "en")
    
    if output_dir is None:
        import tempfile
        output_dir = Path(tempfile.gettempdir()) / "thumbnails"
    
    output_path = Path(output_dir) / f"thumbnail_{plan.get('job_id', 'temp')}.png"
    
    return compose_thumbnail(
        first_image_path=first_image_path,
        title=title,
        output_path=str(output_path),
        language=language,
        watermark_path=None,
    )
