"""
Video stitching async worker for DevotionalAI Platform
Combines images, audio, and subtitles into final 4K MP4 video
"""

from celery_config import celery_app, update_job_progress, mark_job_complete, mark_job_failed
from models import Project
from storage import S3Storage, LocalStorage
from config import settings
import logging
from pathlib import Path
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip
from moviepy.video.fx.resize import resize
import numpy as np
from PIL import Image, ImageFilter
import os
import time

logger = logging.getLogger(__name__)
storage = S3Storage() if settings.USE_S3 else LocalStorage()

@celery_app.task(bind=True, queue='videos')
def stitch_video_async(self, job_id: str, user_id: str, project_id: str, params: dict):
    """
    Stitch final video from assets
    Creates per-scene clips then concatenates into final video
    """
    try:
        update_job_progress(job_id, 5, "Loading project and assets...")
        
        project = Project.get(user_id, project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        resolution = params.get("resolution", settings.DEFAULT_VIDEO_RESOLUTION)
        fps = params.get("fps", settings.DEFAULT_VIDEO_FPS)
        
        scenes = project.story_data.get("scenes", [])
        if not scenes:
            raise ValueError("No scenes found")
        
        total_scenes = len(scenes)
        
        # Determine resolution specs
        if resolution == "720p":
            video_res = (1280, 720)
            bitrate = "3M"
        elif resolution == "1080p":
            video_res = (1920, 1080)
            bitrate = "8M"
        else:  # 4k
            video_res = (3840, 2160)
            bitrate = settings.DEFAULT_VIDEO_BITRATE
        
        update_job_progress(job_id, 10, f"Starting video rendering ({resolution})...")
        
        scene_clips = []
        
        for idx, scene in enumerate(scenes):
            scene_num = scene.get("scene_number", idx + 1)
            
            # Get asset paths
            # Download image and audio locally for processing
            image_filename = f"scene_{scene_num}.png"
            audio_filename = f"scene_{scene_num}.mp3"
            image_path = storage.download_file(user_id, project_id, "images", image_filename)
            audio_path = storage.download_file(user_id, project_id, "audio", audio_filename)
            subtitle_path = storage.download_file(user_id, project_id, "subtitles", f"scene_{scene_num}.srt")

            if not image_path or not audio_path:
                logger.warning(f"Skipping scene {scene_num}: missing assets (image:{image_path}, audio:{audio_path})")
                continue
            # Create scene clip (image static -> Ken-Burns + audio)
            clip = _create_scene_clip(image_path, audio_path, video_res, fps, subtitle_path)
            
            if clip:
                scene_clips.append(clip)
                
                # Save individual scene clip (for preview/debugging)
                scene_clip_path = f"/tmp/scene_{scene_num}_clip.mp4"
                clip.write_videofile(scene_clip_path, fps=fps, codec='libx264', audio_codec='aac')
                storage.upload_file(user_id, project_id, "videos", scene_clip_path)
            
            progress = 10 + (idx / total_scenes) * 70
            update_job_progress(job_id, int(progress), f"Rendered scene {scene_num}/{total_scenes}")
        
        if not scene_clips:
            raise ValueError("No valid scene clips created")
        
        update_job_progress(job_id, 80, "Concatenating scenes...")
        
        # Concatenate all clips with gentle crossfade
        final_clip = concatenate_videoclips(scene_clips, method='compose', padding=-0.5)
        
        update_job_progress(job_id, 85, "Encoding final video...")
        
        # Write final video
        final_video_path = f"/tmp/final_output.mp4"
        # Apply final color grade and slight sharpening using PIL pipeline if needed
        final_clip = final_clip.fx(vfx.colorx, 1.02)
        final_clip.write_videofile(final_video_path, fps=fps, codec='libx264', audio_codec='aac', bitrate=bitrate)
        
        # Upload final video
        storage.upload_file(user_id, project_id, "videos", final_video_path)
        
        update_job_progress(job_id, 95, "Finalizing...")
        
        # Update project status
        project.update(status="completed")
        
        mark_job_complete(job_id, {
            "video_file": "final_output.mp4",
            "resolution": resolution,
            "fps": fps,
            "bitrate": bitrate,
            "scenes": total_scenes
        })
        
        logger.info(f"Video stitching completed for project {project_id}")
        
    except Exception as e:
        logger.exception(f"Video stitching failed: {e}")
        mark_job_failed(job_id, str(e))

def _create_scene_clip(image_path: str, audio_path: str, video_res: tuple, fps: int):
    """Create a single scene video clip with image, audio, and effects"""
    
    try:
        # Load audio and compute duration
        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration

        # Load image using PIL to ensure 4K resolution and convert
        img = Image.open(image_path).convert('RGB')
        # If image smaller than target, upscale with Lanczos
        target_w, target_h = video_res
        if img.width < target_w or img.height < target_h:
            img = img.resize((target_w, target_h), resample=Image.LANCZOS)

        # Optional: apply glow/soften to create divine aura
        glow = img.filter(ImageFilter.GaussianBlur(radius=2))
        blended = Image.blend(img, glow, alpha=0.08)

        tmp_img = f"/tmp/scene_img_{os.getpid()}_{int(time.time())}.png"
        blended.save(tmp_img, format='PNG')

        # Create ImageClip and set duration
        img_clip = ImageClip(tmp_img).set_duration(duration)
        img_clip = img_clip.resize(newsize=video_res)

        # Apply Ken-Burns (subtle zoom over duration)
        zoom_factor = 1.03
        def scaling(t):
            return 1.0 + (zoom_factor - 1.0) * (t / max(0.0001, duration))

        zoomed = img_clip.resize(scaling)

        # Attach audio
        clip = zoomed.set_audio(audio_clip)

        # If subtitle path exists, we could overlay text burn here (optional)
        return clip
        
    except Exception as e:
        logger.error(f"Failed to create scene clip: {e}")
        return None

def _apply_ken_burns(clip, zoom_factor=1.03):
    """Apply Ken-Burns zoom effect to video clip"""
    
    try:
        def zoom_in(get_frame, t):
            """Zoom in slightly over time"""
            frame = get_frame(t)
            h, w = frame.shape[:2]
            
            # Calculate zoom amount based on time progress
            zoom = 1.0 + (zoom_factor - 1.0) * (t / clip.duration)
            
            # Calculate crop region (center zoom)
            new_h = int(h / zoom)
            new_w = int(w / zoom)
            start_h = (h - new_h) // 2
            start_w = (w - new_w) // 2
            
            cropped = frame[start_h:start_h+new_h, start_w:start_w+new_w]
            
            # Resize back to original dimensions
            from moviepy.video.io.ImageSequenceClip import resize
            return resize(cropped, newsize=(w, h))
        
        return clip.transform(zoom_in)
        
    except Exception as e:
        logger.warning(f"Ken-Burns effect failed: {e}, returning original clip")
        return clip
