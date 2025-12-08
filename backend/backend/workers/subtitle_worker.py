"""
Subtitle generation async worker for DevotionalAI Platform
Generates SRT subtitle files from voiceovers
"""

from celery_config import celery_app, update_job_progress, mark_job_complete, mark_job_failed
from models import Project
from storage import S3Storage, LocalStorage
from config import settings
import logging
import re
from pathlib import Path
from moviepy.audio.io.AudioFileClip import AudioFileClip

logger = logging.getLogger(__name__)
storage = S3Storage() if settings.USE_S3 else LocalStorage()

@celery_app.task(bind=True, queue='default')
def generate_subtitles_async(self, job_id: str, user_id: str, project_id: str, params: dict):
    """
    Generate SRT subtitle files for all scenes
    """
    try:
        update_job_progress(job_id, 5, "Loading project...")
        
        project = Project.get(user_id, project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        language = params.get("language", "hindi")
        scenes = project.story_data.get("scenes", [])
        
        if not scenes:
            raise ValueError("No scenes found in project")
        
        total_scenes = len(scenes)
        subtitle_files = []
        
        update_job_progress(job_id, 10, f"Generating subtitles for {total_scenes} scenes...")
        
        for idx, scene in enumerate(scenes):
            scene_num = scene.get("scene_number", idx + 1)
            voiceover = scene.get("voiceover", "")
            duration_notes = scene.get("notes", "")

            if not voiceover:
                logger.warning(f"No voiceover for scene {scene_num}")
                continue

            # Try to get actual audio duration from storage
            audio_filename = f"scene_{scene_num}.mp3"
            try:
                local_audio = storage.download_file(user_id, project_id, "audio", audio_filename)
                if local_audio:
                    clip = AudioFileClip(local_audio)
                    duration = float(clip.duration)
                    clip.close()
                else:
                    duration = _extract_duration(duration_notes)
            except Exception:
                duration = _extract_duration(duration_notes)

            # Generate SRT
            srt_file = _generate_srt(user_id, project_id, scene_num, voiceover, duration)
            subtitle_files.append({
                "scene": scene_num,
                "file": srt_file
            })
            
            progress = 10 + (idx / total_scenes) * 85
            update_job_progress(job_id, int(progress), f"Generated subtitles for scene {scene_num}/{total_scenes}")
        
        update_job_progress(job_id, 95, "Finalizing...")
        
        mark_job_complete(job_id, {
            "subtitles": subtitle_files,
            "total_scenes": total_scenes,
            "language": language
        })
        
        logger.info(f"Subtitle generation completed for project {project_id}")
        
    except Exception as e:
        logger.exception(f"Subtitle generation failed: {e}")
        mark_job_failed(job_id, str(e))

def _extract_duration(notes: str):
    """Extract duration from scene notes"""
    # Look for "Duration: 10-12s" pattern
    match = re.search(r"Duration:\s*(\d+)(?:[–-](\d+))?s", notes)
    if match:
        a = int(match.group(1))
        b = int(match.group(2)) if match.group(2) else a
        return (a + b) / 2.0
    return 10.0  # Default

def _generate_srt(user_id: str, project_id: str, scene_num: int, 
                  text: str, duration: float):
    """Generate SRT subtitle file for a scene"""
    
    # Split text into sentences
    sentences = re.split(r'(?<=[।.!?])\s+', text.strip())
    
    if not sentences:
        return None
    
    # Wrap text to ~38 chars per line
    lines = []
    for sentence in sentences:
        words = sentence.split()
        current_line = ""
        
        for word in words:
            test_line = (current_line + " " + word).strip()
            if len(test_line) <= 38:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
    
    if not lines:
        return None
    
    # Calculate timing
    per_line_duration = duration / len(lines)
    
    # Build SRT content
    srt_content = []
    current_time = 0.0
    
    for idx, line in enumerate(lines, 1):
        start_time = _format_timestamp(current_time)
        current_time += per_line_duration
        end_time = _format_timestamp(current_time)
        
        srt_content.append(f"{idx}\n{start_time} --> {end_time}\n{line}\n")
    
    # Save SRT file
    srt_filename = f"scene_{scene_num}.srt"
    temp_path = f"/tmp/{srt_filename}"
    
    with open(temp_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(srt_content))
    
    # Upload to storage
    storage.upload_file(user_id, project_id, "subtitles", temp_path)
    logger.info(f"Generated SRT for scene {scene_num}")
    
    return srt_filename

def _format_timestamp(seconds: float):
    """Format timestamp for SRT (HH:MM:SS,MMM)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
