"""
TTS (Text-to-Speech) async worker for DevotionalAI Platform
Generates audio using ElevenLabs or pyttsx3
"""

from celery_config import celery_app, update_job_progress, mark_job_complete, mark_job_failed
from models import Project, JobStatus
from storage import S3Storage, LocalStorage
from config import settings
import logging
import requests
from pathlib import Path
from moviepy.audio.io.AudioFileClip import AudioFileClip

logger = logging.getLogger(__name__)
storage = S3Storage() if settings.USE_S3 else LocalStorage()


@celery_app.task(bind=True, queue='tts')
def generate_tts_async(self, job_id: str, user_id: str, project_id: str, params: dict):
    """
    Generate TTS audio for all scenes using ElevenLabs exclusively
    """
    try:
        update_job_progress(job_id, 5, "Loading project...")

        project = Project.get(user_id, project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        voice = params.get("voice", settings.DEFAULT_TTS_VOICE)
        scenes = project.story_data.get("scenes", [])

        if not scenes:
            raise ValueError("No scenes found in project")

        total_scenes = len(scenes)
        audio_files = []

        update_job_progress(job_id, 10, f"Generating TTS for {total_scenes} scenes (ElevenLabs)...")

        for idx, scene in enumerate(scenes):
            scene_num = scene.get("scene_number", idx + 1)
            voiceover = scene.get("voiceover", "")

            if not voiceover:
                logger.warning(f"No voiceover for scene {scene_num}")
                continue

            # Generate audio using ElevenLabs
            audio_filename = _generate_elevenlabs(user_id, project_id, scene_num, voiceover, voice)

            # Determine duration by downloading (if S3) or using local path
            local_path = storage.download_file(user_id, project_id, "audio", audio_filename) if hasattr(storage, 'download_file') else None
            duration = None
            try:
                if local_path:
                    clip = AudioFileClip(local_path)
                    duration = float(clip.duration)
                    clip.close()
                else:
                    duration = 10.0
            except Exception:
                duration = 10.0

            audio_files.append({
                "scene": scene_num,
                "file": audio_filename,
                "duration": duration
            })

            progress = 10 + (idx / total_scenes) * 85
            update_job_progress(job_id, int(progress), f"Generated audio for scene {scene_num}/{total_scenes}")

        update_job_progress(job_id, 95, "Finalizing TTS...")

        mark_job_complete(job_id, {
            "audio_files": audio_files,
            "total_scenes": total_scenes,
            "voice": voice
        })

        logger.info(f"TTS generation completed for project {project_id}")

    except Exception as e:
        logger.exception(f"TTS generation failed: {e}")
        mark_job_failed(job_id, str(e))


def _generate_elevenlabs(user_id: str, project_id: str, scene_num: int, text: str, voice: str):
    """Generate audio using ElevenLabs (required). Stores MP3 and returns filename."""

    if not settings.ELEVENLABS_API_KEY:
        raise RuntimeError("ELEVENLABS_API_KEY not configured in settings")

    # Map voice names to ElevenLabs IDs (defaults; allow override via settings)
    voice_map = getattr(settings, 'ELEVENLABS_VOICE_MAP', {
        "aria": "BZeVSRSWNw0VP88qSKp3",
        "daya": "MF3mGyEYCl7XYWbV7PAN",
    })

    voice_id = voice_map.get(voice, list(voice_map.values())[0])

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
    headers = {
        "xi-api-key": settings.ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }

    # Ensure devotional/Hindi clarity by requesting multilingual model and conservative stability
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.35,
            "similarity_boost": 0.7
        }
    }

    response = requests.post(url, json=payload, headers=headers, stream=True, timeout=120)
    response.raise_for_status()

    # Save to storage temp path
    audio_filename = f"scene_{scene_num}.mp3"
    temp_path = f"/tmp/{audio_filename}"

    with open(temp_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    # Upload to cloud storage
    storage.upload_file(user_id, project_id, "audio", temp_path)
    logger.info(f"Generated ElevenLabs audio for scene {scene_num}")

    return audio_filename


