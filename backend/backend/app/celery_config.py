"""
Celery configuration and async task management for DevotionalAI Platform
Handles queuing, progress tracking, and result persistence
Production-safe with graceful fallbacks for development
"""

from celery import Celery, Task
from kombu import Exchange, Queue
from app.config import settings
from app.models import JobStatus
import uuid
import logging
import os

logger = logging.getLogger(__name__)

# Graceful fallback: Use memory:// broker for dev if Redis unavailable
broker_url = os.getenv("REDIS_URL") or settings.CELERY_BROKER_URL
backend_url = os.getenv("CELERY_BACKEND") or settings.CELERY_RESULT_BACKEND or None

# Initialize Celery app
celery_app = Celery(
    "bhakti",
    broker=broker_url,
    backend=backend_url,
    include=["app.tasks"]
)

# Enable eager execution for memory:// broker (dev mode)
is_memory_broker = broker_url.startswith("memory://")

celery_app.conf.update(
    broker_url=broker_url,
    result_backend=backend_url,
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_always_eager=is_memory_broker,  # Synchronous execution in dev
    task_eager_propagates=is_memory_broker,
    task_time_limit=30 * 60,  # 30 min hard limit
    task_soft_time_limit=getattr(settings, 'JOB_TIMEOUT_MINUTES', 25) * 60,
)

# Task routing
celery_app.conf.task_routes = {
    'workers.tts_worker.*': {'queue': 'tts'},
    'workers.image_worker.*': {'queue': 'images'},
    'workers.video_worker.*': {'queue': 'videos'},
    'workers.story_worker.*': {'queue': 'default'},
}

# Queue definitions
celery_app.conf.task_queues = (
    Queue('default', Exchange('default'), routing_key='default'),
    Queue('tts', Exchange('tts'), routing_key='tts.*'),
    Queue('images', Exchange('images'), routing_key='images.*'),
    Queue('videos', Exchange('videos'), routing_key='videos.*'),
)

class DevotionalTask(Task):
    """Base task class with custom state management"""
    
    def before_start(self, task_id, args, kwargs):
        """Called before task starts"""
        logger.info(f"Starting task {task_id}")
    
    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        """Called after task returns"""
        logger.info(f"Task {task_id} finished with status {status}")

celery_app.Task = DevotionalTask

def create_task(task_type: str, user_id: str, project_id: str, params: dict = None):
    """
    Create and queue an async task
    Returns job_id for tracking
    """
    job_id = str(uuid.uuid4())
    
    # Persist job record
    JobStatus.create(job_id, user_id, project_id, task_type)
    
    # Queue appropriate worker
    if task_type == "tts":
        from workers.tts_worker import generate_tts_async
        generate_tts_async.delay(job_id, user_id, project_id, params or {})
    
    elif task_type == "image_generation":
        from workers.image_worker import generate_images_async
        generate_images_async.delay(job_id, user_id, project_id, params or {})
    
    elif task_type == "story_generation":
        from workers.story_worker import generate_story_async
        generate_story_async.delay(job_id, user_id, project_id, params or {})
    
    elif task_type == "subtitles":
        from workers.subtitle_worker import generate_subtitles_async
        generate_subtitles_async.delay(job_id, user_id, project_id, params or {})
    
    elif task_type == "video_stitch":
        from workers.video_worker import stitch_video_async
        stitch_video_async.delay(job_id, user_id, project_id, params or {})
    
    logger.info(f"Created task {job_id} (type={task_type}) for user {user_id}")
    return job_id

def update_job_progress(job_id: str, progress: int, message: str = None):
    """Update job progress"""
    job = JobStatus.get(job_id)
    if job:
        job.update_status(
            status="running",
            progress=min(progress, 100),
            message=message
        )

def mark_job_complete(job_id: str, result: dict = None):
    """Mark job as completed"""
    job = JobStatus.get(job_id)
    if job:
        job.update_status(
            status="completed",
            progress=100,
            result=result
        )
        logger.info(f"Job {job_id} completed")

def mark_job_failed(job_id: str, error: str):
    """Mark job as failed"""
    job = JobStatus.get(job_id)
    if job:
        job.update_status(
            status="failed",
            progress=0,
            message=f"Error: {error}"
        )
        logger.error(f"Job {job_id} failed: {error}")


def queue_health() -> dict:
    """
    Report queue health status
    Returns broker, backend, and eager flag for monitoring
    """
    return {
        "broker": broker_url,
        "backend": backend_url or "none",
        "task_always_eager": is_memory_broker,
        "mode": "development" if is_memory_broker else "production",
        "status": "ok"
    }
