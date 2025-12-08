"""
Celery + Redis queue backend with in-memory fallback.
Implements same interface as InMemoryQueue for seamless swapping.
"""
import logging
import time
import os
from typing import Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Redis URL; if absent, use in-memory fallback
REDIS_URL = os.getenv("REDIS_URL", "")


class JobStatus(str, Enum):
    """Job execution states."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    CANCELED = "canceled"


class JobStep(str, Enum):
    """Render pipeline steps."""
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
    cost_estimate: Optional[float] = None


class CeleryQueueBackend:
    """Celery + Redis backend for job queue."""

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis = None
        self.celery_app = None
        self._init_redis()

    def _init_redis(self):
        """Initialize Redis client and Celery app."""
        try:
            import redis
            from celery import Celery
            
            self.redis = redis.from_url(self.redis_url, decode_responses=True)
            # Test connection
            self.redis.ping()
            logger.info("Redis connected: %s", self.redis_url)
            
            # Initialize Celery app
            self.celery_app = Celery(
                "bhakti_renderer",
                broker=self.redis_url,
                backend=self.redis_url,
            )
            self.celery_app.conf.update(
                task_serializer="json",
                accept_content=["json"],
                result_serializer="json",
                timezone="UTC",
                enable_utc=True,
                task_track_started=True,
                worker_prefetch_multiplier=1,
                worker_max_tasks_per_child=100,
            )
            logger.info("Celery initialized")
        except Exception as e:
            logger.error("Celery/Redis init failed: %s; falling back to in-memory", e)
            self.redis = None
            self.celery_app = None

    def enqueue(self, plan: Dict[str, Any]) -> str:
        """Enqueue render job; return job_id."""
        import uuid
        job_id = plan.get("job_id") or str(uuid.uuid4())
        
        if not self.redis:
            return self._fallback_enqueue(job_id, plan)
        
        try:
            # Store plan in Redis
            self.redis.hset(
                f"job:{job_id}",
                mapping={
                    "plan_json": __import__("json").dumps(plan),
                    "state": JobStatus.PENDING,
                    "step": JobStep.QUEUED,
                    "progress": "0.0",
                    "created_at": str(time.time()),
                    "logs": "[]",
                    "assets": "{}",
                }
            )
            # Set expiry (7 days)
            self.redis.expire(f"job:{job_id}", 604800)
            logger.info("Job enqueued to Celery: %s", job_id)
            return job_id
        except Exception as e:
            logger.error("Celery enqueue failed: %s", e)
            return self._fallback_enqueue(job_id, plan)

    def get_status(self, job_id: str) -> Optional[JobStatus_]:
        """Fetch job status from Redis or memory."""
        if not self.redis:
            return self._fallback_get_status(job_id)
        
        try:
            data = self.redis.hgetall(f"job:{job_id}")
            if not data:
                return None
            
            import json
            return JobStatus_(
                job_id=job_id,
                state=JobStatus(data.get("state", "pending")),
                step=JobStep(data.get("step", "queued")),
                progress_pct=float(data.get("progress", 0.0)),
                assets=json.loads(data.get("assets", "{}")),
                final_video_url=data.get("final_video_url"),
                youtube_url=data.get("youtube_url"),
                logs=json.loads(data.get("logs", "[]")),
                started_at=float(data["started_at"]) if "started_at" in data else None,
                completed_at=float(data["completed_at"]) if "completed_at" in data else None,
                error=data.get("error"),
                cost_estimate=float(data["cost_estimate"]) if "cost_estimate" in data else None,
            )
        except Exception as e:
            logger.error("Redis get_status failed: %s", e)
            return self._fallback_get_status(job_id)

    def update_step(self, job_id: str, step: str, progress: float = None, assets: Dict = None):
        """Update job progress during execution."""
        if not self.redis:
            return self._fallback_update_step(job_id, step, progress, assets)
        
        try:
            import json
            mapping = {"step": step, "last_update": str(time.time())}
            if progress is not None:
                mapping["progress"] = str(progress)
            if assets:
                current_assets = json.loads(self.redis.hget(f"job:{job_id}", "assets") or "{}")
                current_assets.update(assets)
                mapping["assets"] = json.dumps(current_assets)
            
            self.redis.hset(f"job:{job_id}", mapping=mapping)
        except Exception as e:
            logger.error("Redis update_step failed: %s", e)
            self._fallback_update_step(job_id, step, progress, assets)

    def mark_running(self, job_id: str):
        """Mark job as running."""
        if not self.redis:
            return self._fallback_mark_running(job_id)
        
        try:
            self.redis.hset(
                f"job:{job_id}",
                mapping={"state": JobStatus.RUNNING, "started_at": str(time.time())}
            )
        except Exception as e:
            logger.error("Redis mark_running failed: %s", e)
            self._fallback_mark_running(job_id)

    def mark_success(self, job_id: str, final_video_url: str = None, youtube_url: str = None):
        """Mark job as successfully completed."""
        if not self.redis:
            return self._fallback_mark_success(job_id, final_video_url, youtube_url)
        
        try:
            mapping = {
                "state": JobStatus.SUCCESS,
                "step": JobStep.COMPLETED,
                "completed_at": str(time.time()),
            }
            if final_video_url:
                mapping["final_video_url"] = final_video_url
            if youtube_url:
                mapping["youtube_url"] = youtube_url
            
            self.redis.hset(f"job:{job_id}", mapping=mapping)
        except Exception as e:
            logger.error("Redis mark_success failed: %s", e)
            self._fallback_mark_success(job_id, final_video_url, youtube_url)

    def mark_error(self, job_id: str, error: str):
        """Mark job as failed."""
        if not self.redis:
            return self._fallback_mark_error(job_id, error)
        
        try:
            self.redis.hset(
                f"job:{job_id}",
                mapping={
                    "state": JobStatus.ERROR,
                    "completed_at": str(time.time()),
                    "error": error,
                }
            )
        except Exception as e:
            logger.error("Redis mark_error failed: %s", e)
            self._fallback_mark_error(job_id, error)

    def mark_canceled(self, job_id: str):
        """Mark job as canceled by user."""
        if not self.redis:
            return self._fallback_mark_canceled(job_id)
        
        try:
            self.redis.hset(
                f"job:{job_id}",
                mapping={
                    "state": JobStatus.CANCELED,
                    "completed_at": str(time.time()),
                }
            )
        except Exception as e:
            logger.error("Redis mark_canceled failed: %s", e)
            self._fallback_mark_canceled(job_id)

    def log_message(self, job_id: str, message: str):
        """Append structured log entry."""
        if not self.redis:
            return self._fallback_log_message(job_id, message)
        
        try:
            import json
            logs = json.loads(self.redis.hget(f"job:{job_id}", "logs") or "[]")
            logs.append(f"[{time.time():.0f}] {message}")
            self.redis.hset(f"job:{job_id}", "logs", json.dumps(logs[-1000:]))  # Keep last 1000
        except Exception as e:
            logger.error("Redis log_message failed: %s", e)

    def cancel(self, job_id: str) -> bool:
        """Request task cancellation; return True if canceled or already done."""
        if not self.redis:
            return self._fallback_cancel(job_id)
        
        try:
            status = self.get_status(job_id)
            if not status:
                logger.warning("Job not found for cancel: %s", job_id)
                return False
            
            if status.state in [JobStatus.SUCCESS, JobStatus.ERROR, JobStatus.CANCELED]:
                logger.info("Job already done; skipping cancel: %s", job_id)
                return True
            
            # Try to revoke Celery task if it exists
            if self.celery_app:
                try:
                    # Revoke task by job_id
                    self.celery_app.control.revoke(job_id, terminate=True)
                    logger.info("Celery task revoked: %s", job_id)
                except Exception as e:
                    logger.error("Celery revoke failed: %s", e)
            
            # Mark as canceled in Redis
            self.mark_canceled(job_id)
            return True
        except Exception as e:
            logger.error("Cancel failed: %s", e)
            return False

    # ========== Fallback in-memory implementations ==========

    _fallback_jobs: Dict[str, Dict] = {}
    _fallback_lock = __import__("threading").Lock()

    def _fallback_enqueue(self, job_id: str, plan: Dict) -> str:
        with self._fallback_lock:
            self._fallback_jobs[job_id] = {
                "plan": plan,
                "state": JobStatus.PENDING,
                "step": JobStep.QUEUED,
                "progress": 0.0,
                "created_at": time.time(),
                "logs": [],
                "assets": {},
            }
        logger.info("Job enqueued (in-memory fallback): %s", job_id)
        return job_id

    def _fallback_get_status(self, job_id: str) -> Optional[JobStatus_]:
        with self._fallback_lock:
            job = self._fallback_jobs.get(job_id)
            if not job:
                return None
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
                cost_estimate=job.get("cost_estimate"),
            )

    def _fallback_update_step(self, job_id: str, step: str, progress: float = None, assets: Dict = None):
        with self._fallback_lock:
            if job_id in self._fallback_jobs:
                self._fallback_jobs[job_id]["step"] = step
                if progress is not None:
                    self._fallback_jobs[job_id]["progress"] = progress
                if assets:
                    self._fallback_jobs[job_id]["assets"].update(assets)

    def _fallback_mark_running(self, job_id: str):
        with self._fallback_lock:
            if job_id in self._fallback_jobs:
                self._fallback_jobs[job_id]["state"] = JobStatus.RUNNING
                self._fallback_jobs[job_id]["started_at"] = time.time()

    def _fallback_mark_success(self, job_id: str, final_video_url: str = None, youtube_url: str = None):
        with self._fallback_lock:
            if job_id in self._fallback_jobs:
                self._fallback_jobs[job_id]["state"] = JobStatus.SUCCESS
                self._fallback_jobs[job_id]["completed_at"] = time.time()
                self._fallback_jobs[job_id]["step"] = JobStep.COMPLETED
                if final_video_url:
                    self._fallback_jobs[job_id]["final_video_url"] = final_video_url
                if youtube_url:
                    self._fallback_jobs[job_id]["youtube_url"] = youtube_url

    def _fallback_mark_error(self, job_id: str, error: str):
        with self._fallback_lock:
            if job_id in self._fallback_jobs:
                self._fallback_jobs[job_id]["state"] = JobStatus.ERROR
                self._fallback_jobs[job_id]["completed_at"] = time.time()
                self._fallback_jobs[job_id]["error"] = error

    def _fallback_mark_canceled(self, job_id: str):
        with self._fallback_lock:
            if job_id in self._fallback_jobs:
                self._fallback_jobs[job_id]["state"] = JobStatus.CANCELED
                self._fallback_jobs[job_id]["completed_at"] = time.time()

    def _fallback_log_message(self, job_id: str, message: str):
        with self._fallback_lock:
            if job_id in self._fallback_jobs:
                self._fallback_jobs[job_id]["logs"].append(f"[{time.time():.0f}] {message}")

    def _fallback_cancel(self, job_id: str) -> bool:
        with self._fallback_lock:
            if job_id not in self._fallback_jobs:
                return False
            job = self._fallback_jobs[job_id]
            if job["state"] not in [JobStatus.SUCCESS, JobStatus.ERROR, JobStatus.CANCELED]:
                job["state"] = JobStatus.CANCELED
                job["completed_at"] = time.time()
            return True


# Global queue instance; initialized based on REDIS_URL
_queue_instance: Optional[CeleryQueueBackend] = None


def get_queue() -> CeleryQueueBackend:
    """Get or initialize global queue."""
    global _queue_instance
    if _queue_instance is None:
        if REDIS_URL:
            _queue_instance = CeleryQueueBackend(REDIS_URL)
        else:
            # Create in-memory-only instance (no Redis)
            _queue_instance = CeleryQueueBackend("")
            _queue_instance.redis = None  # Force fallback
    return _queue_instance
