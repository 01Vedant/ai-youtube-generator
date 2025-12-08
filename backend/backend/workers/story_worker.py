"""
Story generation worker: turns a title/description into a multi-scene project template
Each scene includes: scene_number, scene_title, image_prompt, voiceover (Hindi), notes, duration

This worker uses OpenAI (chat completion) when available, otherwise falls back to a simple heuristic.
After creating the story, it saves the project.story_data and enqueues the full pipeline (images -> tts -> subtitles -> stitch).
"""

from celery_config import celery_app, update_job_progress, mark_job_complete, mark_job_failed
from models import Project, JobStatus
from storage import S3Storage, LocalStorage
from config import settings
from pathlib import Path
import logging
import time
import json

logger = logging.getLogger(__name__)
storage = S3Storage() if settings.USE_S3 else LocalStorage()


@celery_app.task(bind=True, queue='default')
def generate_story_async(self, job_id: str, user_id: str, project_id: str, params: dict):
    """Create scenes from title + description and run full pipeline."""
    try:
        update_job_progress(job_id, 5, "Creating story from title...")

        title = params.get('title')
        description = params.get('description', '')
        full_text = params.get('full_text', '')
        max_scenes = int(params.get('max_scenes', 6))

        if not title and not full_text:
            raise ValueError("Either a title or full_text is required to generate story")

        # Generate scenes using OpenAI if available
        scenes = []
        if settings.OPENAI_API_KEY:
            try:
                import openai
                openai.api_key = settings.OPENAI_API_KEY
                if full_text:
                    user_prompt = full_text
                else:
                    user_prompt = f"Title: {title}. Description: {description}."

                prompt = (
                    f"You are an expert storyteller for Indian mythological devotional videos. "
                    f"Split the following content into {max_scenes} cinematic scenes. For each scene return JSON with: scene_number (int), scene_title (short), voiceover (Hindi, 1-2 emotive sentences), notes (production notes including camera, mood, duration like 'Duration: 8-10s'), image_prompt (detailed English prompt for an AI image engine). "
                    f"Content: {user_prompt}. Output only a JSON object with key 'scenes' as an array."
                )

                resp = openai.ChatCompletion.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=1400
                )

                text = resp.choices[0].message.content
                data = json.loads(text)
                scenes = data.get('scenes', [])
            except Exception as e:
                logger.exception(f"OpenAI story generation failed: {e}")

        # Fallback simple split if OpenAI not available or parse failed
        if not scenes:
            logger.info("Falling back to heuristic scene generation")
            # create a simple set of scenes based on title
            for i in range(1, max_scenes + 1):
                scenes.append({
                    "scene_number": i,
                    "scene_title": f"{title} — Part {i}",
                    "voiceover": f"यह भाग {i} है: {title} — संक्षेप में कहानी।",
                    "notes": "Vibrant temple scene, devotional music, cinematic closeups.",
                    "duration_seconds": 10
                })

        # Attach generated prompts using existing image prompt builder logic if available
        for s in scenes:
            if 'image_prompt' not in s or not s.get('image_prompt'):
                # build a portable prompt
                base = f"{s.get('scene_title','')}. {s.get('notes','')}"
                s['image_prompt'] = f"{base} | Indian mythological, Sanatan Dharma, vibrant devotional, cinematic, ultra-detailed, 4K"

        # Save story_data in project
        project = Project.get(user_id, project_id)
        if not project:
            raise ValueError("Project not found")

        project.update(story_data={"scenes": scenes})
        update_job_progress(job_id, 30, "Story saved. Queuing image generation...")

        # Queue image generation -> tts -> subtitles -> stitch sequentially and wait for completion between phases
        from celery_config import create_task

        img_job = create_task("image_generation", user_id, project_id, {"engine": settings.DEFAULT_IMAGE_ENGINE, "quality": "final"})

        # poll for image job completion
        timeout = 60 * 30  # 30 minutes
        interval = 5
        waited = 0
        while waited < timeout:
            job = JobStatus.get(img_job)
            if job and job.status == 'completed':
                break
            if job and job.status == 'failed':
                raise RuntimeError(f"Image generation failed: {job.message}")
            time.sleep(interval)
            waited += interval

        update_job_progress(job_id, 60, "Images ready. Queuing TTS...")

        tts_job = create_task("tts", user_id, project_id, {"voice": settings.DEFAULT_TTS_VOICE})

        # wait for TTS
        waited = 0
        while waited < timeout:
            job = JobStatus.get(tts_job)
            if job and job.status == 'completed':
                break
            if job and job.status == 'failed':
                raise RuntimeError(f"TTS failed: {job.message}")
            time.sleep(interval)
            waited += interval

        update_job_progress(job_id, 80, "TTS ready. Queuing subtitles and final stitch...")

        sub_job = create_task("subtitles", user_id, project_id, {"language": "hindi"})
        stitch_job = create_task("video_stitch", user_id, project_id, {"resolution": "4k", "fps": 24})

        mark_job_complete(job_id, {"image_job": img_job, "tts_job": tts_job, "sub_job": sub_job, "stitch_job": stitch_job})
        logger.info(f"Story generation and pipeline started for project {project_id}")

    except Exception as e:
        logger.exception(f"Story generation failed: {e}")
        mark_job_failed(job_id, str(e))
