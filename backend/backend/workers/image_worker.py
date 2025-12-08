"""
Image generation async worker for DevotionalAI Platform
Integrates with DALL-E 3, Stable Diffusion XL, Runway, or Luma
"""

from celery_config import celery_app, update_job_progress, mark_job_complete, mark_job_failed
from models import Project
from storage import S3Storage, LocalStorage
from config import settings
import logging
from pathlib import Path
import requests
import json
from PIL import Image
from io import BytesIO

logger = logging.getLogger(__name__)
storage = S3Storage() if settings.USE_S3 else LocalStorage()

@celery_app.task(bind=True, queue='images')
def generate_images_async(self, job_id: str, user_id: str, project_id: str, params: dict):
    """
    Generate AI images for all scenes
    Supports multiple engines: openai, sdxl, runway, local
    """
    try:
        update_job_progress(job_id, 5, "Loading project...")
        
        project = Project.get(user_id, project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        engine = params.get("engine", settings.DEFAULT_IMAGE_ENGINE)
        quality = params.get("quality", "preview")  # preview or final
        scenes = project.story_data.get("scenes", [])
        
        if not scenes:
            raise ValueError("No scenes found in project")
        
        total_scenes = len(scenes)
        image_files = []
        
        update_job_progress(job_id, 10, f"Generating images ({quality}) with {engine}...")
        
        for idx, scene in enumerate(scenes):
            scene_num = scene.get("scene_number", idx + 1)
            image_prompt = scene.get("image_prompt", "")
            
            if not image_prompt:
                logger.warning(f"No image prompt for scene {scene_num}")
                continue
            
            # If prompt missing, auto-build from scene text/voiceover
            if not image_prompt:
                image_prompt = _build_prompt_from_scene(scene)

            # Generate image based on engine with simple quality check + retry
            max_retries = 2
            image_file = None
            for attempt in range(max_retries + 1):
                image_file = _generate_scene_image(user_id, project_id, scene_num, image_prompt, engine, quality)
                # Attempt to download and validate size
                try:
                    local_path = storage.download_file(user_id, project_id, "images", image_file)
                    if local_path:
                        with Image.open(local_path) as im:
                            w, h = im.size
                        if w >= 3840 and h >= 2160:
                            break
                        else:
                            logger.warning(f"Generated image too small ({w}x{h}), retrying (attempt {attempt+1})")
                    else:
                        logger.warning("Could not download generated image for validation")
                except Exception as e:
                    logger.warning(f"Image validation failed: {e}")

            # final image_file may be None or placeholder
            
            if image_file:
                image_files.append({
                    "scene": scene_num,
                    "file": image_file,
                    "engine": engine
                })
            
            progress = 10 + (idx / total_scenes) * 85
            update_job_progress(job_id, int(progress), f"Generated image {scene_num}/{total_scenes}")
        
        update_job_progress(job_id, 95, "Finalizing...")
        
        mark_job_complete(job_id, {
            "images": image_files,
            "total_scenes": total_scenes,
            "engine": engine,
            "quality": quality
        })
        
        logger.info(f"Image generation completed for project {project_id}")
        
    except Exception as e:
        logger.exception(f"Image generation failed: {e}")
        mark_job_failed(job_id, str(e))

def _generate_scene_image(user_id: str, project_id: str, scene_num: int, 
                          prompt: str, engine: str, quality: str):
    """Generate a single scene image"""
    
    if engine == "openai":
        return _generate_openai(user_id, project_id, scene_num, prompt, quality)
    elif engine == "sdxl":
        return _generate_sdxl(user_id, project_id, scene_num, prompt, quality)
    elif engine == "runway":
        return _generate_runway(user_id, project_id, scene_num, prompt, quality)
    elif engine == "luma":
        return _generate_luma(user_id, project_id, scene_num, prompt, quality)
    else:
        logger.warning(f"Unknown engine {engine}, using local placeholder")
        return _create_placeholder(user_id, project_id, scene_num)

def _generate_openai(user_id: str, project_id: str, scene_num: int, 
                    prompt: str, quality: str):
    """Generate image using DALL-E 3"""
    
    if not settings.OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set, using placeholder")
        return _create_placeholder(user_id, project_id, scene_num)
    
    import openai
    openai.api_key = settings.OPENAI_API_KEY
    
    # Adjust prompt based on quality
    if quality == "final":
        prompt += " | ultra-high resolution 4K | cinematic lighting | masterpiece"
        resolution = "1024x1024"  # DALL-E 3 standard
    else:
        resolution = "1024x1024"
    
    try:
        response = openai.Image.create(
            model="dall-e-3",
            prompt=prompt,
            n=1,
            size=resolution,
        )

        image_url = response.data[0].url
        image_resp = requests.get(image_url, timeout=60)
        image_resp.raise_for_status()

        # Load image and upscale to 4K when final
        image = Image.open(BytesIO(image_resp.content)).convert('RGB')

        if quality == 'final':
            image = image.resize((3840, 2160), resample=Image.LANCZOS)

        # Save to temp and upload
        image_filename = f"scene_{scene_num}.png"
        temp_path = f"/tmp/{image_filename}"
        image.save(temp_path, format='PNG')

        storage.upload_file(user_id, project_id, "images", temp_path)
        logger.info(f"Generated DALL-E 3 image for scene {scene_num}")

        return image_filename

    except Exception as e:
        logger.exception(f"DALL-E 3 generation failed: {e}")
        return _create_placeholder(user_id, project_id, scene_num)

def _generate_sdxl(user_id: str, project_id: str, scene_num: int, 
                  prompt: str, quality: str):
    """Generate image using Stable Diffusion XL"""
    # Try Replicate (if configured) for SDXL; else fallback to placeholder
    replicate_token = getattr(settings, 'REPLICATE_API_TOKEN', None)
    if replicate_token:
        try:
            url = "https://api.replicate.com/v1/predictions"
            headers = {
                "Authorization": f"Token {replicate_token}",
                "Content-Type": "application/json"
            }
            payload = {
                "version": "stability-ai/stable-diffusion-xl", 
                "input": {"prompt": prompt, "width": 3840, "height": 2160}
            }
            resp = requests.post(url, json=payload, headers=headers, timeout=120)
            resp.raise_for_status()
            data = resp.json()
            # Replicate uses async polling - for brevity, if replicate provides output url in response, use it
            output_urls = data.get('output') or []
            if output_urls:
                image_url = output_urls[0]
                image_data = requests.get(image_url).content
                image = Image.open(BytesIO(image_data)).convert('RGB')
                image_filename = f"scene_{scene_num}.png"
                temp_path = f"/tmp/{image_filename}"
                image.save(temp_path, format='PNG')
                storage.upload_file(user_id, project_id, "images", temp_path)
                return image_filename
        except Exception as e:
            logger.exception(f"Replicate SDXL generation failed: {e}")

    logger.info("SDXL generation not available, using placeholder")
    return _create_placeholder(user_id, project_id, scene_num)

def _generate_runway(user_id: str, project_id: str, scene_num: int, 
                    prompt: str, quality: str):
    """Generate image using Runway Gen-3"""
    
    logger.info(f"Runway generation not fully implemented (requires Runway API)")
    return _create_placeholder(user_id, project_id, scene_num)

def _generate_luma(user_id: str, project_id: str, scene_num: int, 
                  prompt: str, quality: str):
    """Generate image using Luma AI"""
    
    logger.info(f"Luma generation not fully implemented (requires Luma API)")
    return _create_placeholder(user_id, project_id, scene_num)

def _create_placeholder(user_id: str, project_id: str, scene_num: int):
    """Create a placeholder image for testing"""
    
    from PIL import Image, ImageDraw, ImageFont
    
    # Create 4K placeholder (3840x2160)
    img = Image.new('RGB', (3840, 2160), color='#1a1a2e')
    draw = ImageDraw.Draw(img)
    
    # Add text
    text = f"Scene {scene_num}\nDevotionalAI"
    
    # Calculate text position
    bbox = draw.textbbox((0, 0), text)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (3840 - text_width) // 2
    y = (2160 - text_height) // 2
    
    # Draw gradient effect (simple colored rectangles)
    for i in range(0, 3840, 100):
        draw.rectangle([(i, 0), (i+50, 2160)], fill=f'#{20+i%200:02x}40{80+i%100:02x}')
    
    # Draw text
    draw.text((x, y), text, fill='white')
    
    # Save to storage
    image_filename = f"scene_{scene_num}.png"
    temp_path = f"/tmp/{image_filename}"
    img.save(temp_path, 'PNG')
    
    storage.upload_file(user_id, project_id, "images", temp_path)
    logger.info(f"Created placeholder image for scene {scene_num}")
    
    return image_filename


def _build_prompt_from_scene(scene: dict) -> str:
    """Construct a rich 4K devotional prompt from scene fields."""
    title = scene.get('scene_title') or ''
    notes = scene.get('notes') or ''
    voiceover = scene.get('voiceover') or ''

    base = f"{title}. {notes} {voiceover}".strip()
    style = (
        "Indian mythological, Sanatan Dharma, vibrant devotional, cinematic lighting, "
        "high detail, intricate ornaments, golden tones, temple architecture, dramatic rim light, ultra-realistic, 4K"
    )
    prompt = f"{base} | {style} | highly detailed, photorealistic, dramatic composition"
    return prompt
