"""In-memory job queue with Celery-compatible interface."""
import json
import uuid
import time
import logging
from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from pathlib import Path

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"


class JobStep(str, Enum):
    QUEUED = "queued"
    IMAGES = "images"
    TTS = "tts"
    SUBTITLES = "subtitles"
    STITCH = "stitch"
    UPLOAD = "upload"
    YOUTUBE_PUBLISH = "youtube_publish"
    COMPLETED = "completed"


@dataclass
class JobStatus_:
    """Job status snapshot."""
    job_id: str
    state: JobStatus = JobStatus.PENDING
    step: JobStep = JobStep.QUEUED
    progress_pct: float = 0.0
    assets: Dict[str, str] = field(default_factory=dict)
    final_video_url: Optional[str] = None
    youtube_url: Optional[str] = None
    logs: list = field(default_factory=list)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error: Optional[str] = None


class InMemoryQueue:
    """Simple in-memory queue; Celery-compatible interface."""

    def __init__(self):
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.lock = __import__("threading").Lock()

    def enqueue(self, plan: Dict[str, Any]) -> str:
        """Enqueue a job; return job_id."""
        job_id = plan.get("job_id") or str(uuid.uuid4())
        with self.lock:
            self.jobs[job_id] = {
                "plan": plan,
                "status": JobStatus_.job_id == job_id,
                "created_at": time.time(),
                "step": JobStep.QUEUED,
                "progress": 0.0,
            }
        logger.info("Job enqueued: %s", job_id)
        return job_id

    def get_status(self, job_id: str) -> Optional[JobStatus_]:
        """Get current job status."""
        with self.lock:
            if job_id not in self.jobs:
                return None
            job = self.jobs[job_id]
            return JobStatus_(
                job_id=job_id,
                state=job.get("state", JobStatus.PENDING),
                step=job.get("step", JobStep.QUEUED),
                progress_pct=job.get("progress", 0.0),
                assets=job.get("assets", {}),
                final_video_url=job.get("final_video_url"),
                youtube_url=job.get("youtube_url"),
                logs=job.get("logs", []),
                started_at=job.get("started_at"),
                completed_at=job.get("completed_at"),
                error=job.get("error"),
            )

    def update_step(self, job_id: str, step: str, progress: float = None, assets: Dict = None):
        """Update job step and optional progress."""
        with self.lock:
            if job_id in self.jobs:
                self.jobs[job_id]["step"] = step
                if progress is not None:
                    self.jobs[job_id]["progress"] = progress
                if assets:
                    self.jobs[job_id]["assets"] = {**self.jobs[job_id].get("assets", {}), **assets}
                self.jobs[job_id]["last_update"] = time.time()

    def mark_running(self, job_id: str):
        """Mark job as running."""
        with self.lock:
            if job_id in self.jobs:
                self.jobs[job_id]["state"] = JobStatus.RUNNING
                self.jobs[job_id]["started_at"] = time.time()

    def mark_success(self, job_id: str, final_video_url: str = None, youtube_url: str = None):
        """Mark job as successful."""
        with self.lock:
            if job_id in self.jobs:
                self.jobs[job_id]["state"] = JobStatus.SUCCESS
                self.jobs[job_id]["completed_at"] = time.time()
                self.jobs[job_id]["step"] = JobStep.COMPLETED
                if final_video_url:
                    self.jobs[job_id]["final_video_url"] = final_video_url
                if youtube_url:
                    self.jobs[job_id]["youtube_url"] = youtube_url

    def mark_error(self, job_id: str, error: str):
        """Mark job as failed."""
        with self.lock:
            if job_id in self.jobs:
                self.jobs[job_id]["state"] = JobStatus.ERROR
                self.jobs[job_id]["completed_at"] = time.time()
                self.jobs[job_id]["error"] = error

    def log_message(self, job_id: str, message: str):
        """Append a log message."""
        with self.lock:
            if job_id in self.jobs:
                self.jobs[job_id].setdefault("logs", []).append(message)


# Global queue instance
_queue_instance = InMemoryQueue()


def get_queue() -> InMemoryQueue:
    """Get global queue instance."""
    return _queue_instance
