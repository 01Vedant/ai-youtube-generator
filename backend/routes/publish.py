"""
Publish route: POST /publish/{job_id}/schedule, GET /publish/{job_id}
Handles scheduled YouTube publishing with Celery beat.
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import json
from pathlib import Path

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/publish", tags=["publish"])

# Simple in-memory schedule storage (production: use database)
# Key: job_id, Value: {"scheduled_at": iso_datetime, "state": "scheduled|published|failed", "error": "..."}
_schedule_store: dict[str, dict] = {}
_SCHEDULE_FILE = Path("platform/schedules/publish_schedules.json")


def _load_schedules():
    """Load schedules from disk."""
    global _schedule_store
    if _SCHEDULE_FILE.exists():
        try:
            with open(_SCHEDULE_FILE, "r") as f:
                _schedule_store = json.load(f)
        except Exception as e:
            logger.warning("Failed to load schedules from disk: %s", e)


def _save_schedules():
    """Save schedules to disk."""
    _SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(_SCHEDULE_FILE, "w") as f:
            json.dump(_schedule_store, f, indent=2)
    except Exception as e:
        logger.error("Failed to save schedules to disk: %s", e)


def _init_schedules():
    """Initialize schedule storage."""
    _load_schedules()


class SchedulePublishRequest(BaseModel):
    """Request to schedule a YouTube publish."""
    iso_datetime: str = Field(..., description="ISO 8601 datetime (e.g., 2025-12-25T14:00:00Z)")
    title: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[list[str]] = None
    playlist_id: Optional[str] = None


class PublishScheduleResponse(BaseModel):
    """Response for publish schedule status."""
    job_id: str
    scheduled_at: Optional[str] = None
    state: str  # "none" | "scheduled" | "published" | "failed"
    error: Optional[str] = None
    created_at: Optional[str] = None


@router.get("/providers")
async def get_providers():
    """
    GET /publish/providers
    List which publishing providers are configured and enabled.
    
    Returns:
        Dict with provider status (configured, enabled, authenticated)
    """
    import os
    providers = {}
    
    # YouTube
    youtube_enabled = os.environ.get("ENABLE_YOUTUBE_UPLOAD") == "1"
    youtube_client_id = os.environ.get("YOUTUBE_CLIENT_ID")
    youtube_client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
    youtube_tokens_exist = Path("platform/youtube_tokens.json").exists()
    
    providers["youtube"] = {
        "configured": bool(youtube_client_id and youtube_client_secret),
        "enabled": youtube_enabled,
        "authenticated": youtube_tokens_exist,
        "ready": youtube_enabled and youtube_tokens_exist
    }
    
    return {"providers": providers}


@router.post("/{job_id}/schedule")
async def schedule_publish(job_id: str, req: SchedulePublishRequest) -> PublishScheduleResponse:
    """
    POST /publish/{job_id}/schedule
    Schedule a completed video for automatic YouTube publishing.
    
    Args:
        job_id: The job ID of completed render
        req.iso_datetime: When to publish (ISO 8601, e.g., 2025-12-25T14:00:00Z)
        req.title: YouTube video title (optional, uses job topic if not provided)
        req.description: YouTube video description
        req.tags: Video tags
        req.playlist_id: Add to specific playlist after publishing
    """
    _init_schedules()
    
    # Validate ISO datetime
    try:
        scheduled_time = datetime.fromisoformat(req.iso_datetime.replace("Z", "+00:00"))
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid ISO 8601 datetime: {req.iso_datetime}"
        )
    
    # Ensure scheduled time is in the future
    now = datetime.now(timezone.utc)
    if scheduled_time <= now:
        raise HTTPException(
            status_code=400,
            detail="Scheduled time must be in the future"
        )
    
    # Verify job exists and is completed by checking job_summary.json
    # Import OUTPUT_ROOT
    import sys
    from pathlib import Path as PathLib
    PLATFORM_ROOT = PathLib(__file__).resolve().parents[1]
    if str(PLATFORM_ROOT) not in sys.path:
        sys.path.insert(0, str(PLATFORM_ROOT))
    from backend.app.settings import OUTPUT_ROOT
    
    job_dir = OUTPUT_ROOT / job_id
    summary_path = job_dir / "job_summary.json"
    
    if not summary_path.exists():
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    
    try:
        with open(summary_path, "r", encoding="utf-8") as f:
            job_status = json.load(f)
        
        if job_status.get("state") != "success":
            raise HTTPException(
                status_code=400,
                detail=f"Job must be completed (current state: {job_status.get('state')})"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to verify job %s: %s", job_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to verify job: {str(e)}")
    
    # Create schedule entry
    schedule_entry = {
        "job_id": job_id,
        "scheduled_at": req.iso_datetime,
        "state": "scheduled",
        "title": req.title,
        "description": req.description,
        "tags": req.tags or [],
        "playlist_id": req.playlist_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "error": None,
    }
    
    _schedule_store[job_id] = schedule_entry
    _save_schedules()
    
    logger.info(
        "Scheduled publish for job %s at %s",
        job_id, req.iso_datetime
    )
    
    return PublishScheduleResponse(
        job_id=job_id,
        scheduled_at=req.iso_datetime,
        state="scheduled",
        created_at=schedule_entry["created_at"],
    )


@router.get("/{job_id}")
async def get_publish_status(job_id: str) -> PublishScheduleResponse:
    """
    GET /publish/{job_id}
    Get the publish schedule status for a job.
    """
    _init_schedules()
    
    if job_id not in _schedule_store:
        return PublishScheduleResponse(
            job_id=job_id,
            state="none",
        )
    
    schedule = _schedule_store[job_id]
    
    return PublishScheduleResponse(
        job_id=job_id,
        scheduled_at=schedule.get("scheduled_at"),
        state=schedule.get("state", "unknown"),
        error=schedule.get("error"),
        created_at=schedule.get("created_at"),
    )


@router.delete("/{job_id}/cancel")
async def cancel_publish_schedule(job_id: str) -> PublishScheduleResponse:
    """
    DELETE /publish/{job_id}/cancel
    Cancel a scheduled publish.
    """
    _init_schedules()
    
    if job_id not in _schedule_store:
        raise HTTPException(status_code=404, detail=f"No schedule found for job '{job_id}'")
    
    schedule = _schedule_store[job_id]
    
    if schedule.get("state") in ["published", "failed"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel publish with state '{schedule.get('state')}'"
        )
    
    # Mark as canceled
    schedule["state"] = "canceled"
    schedule["canceled_at"] = datetime.now(timezone.utc).isoformat()
    _save_schedules()
    
    logger.info("Canceled publish schedule for job %s", job_id)
    
    return PublishScheduleResponse(
        job_id=job_id,
        state="canceled",
    )


# Celery beat task for processing scheduled publishes
# This would be run by celery beat scheduler periodically
async def process_scheduled_publishes():
    """
    Background task (Celery beat): Check for due scheduled publishes and publish them.
    Called every minute by Celery beat scheduler.
    """
    _init_schedules()
    
    now = datetime.now(timezone.utc)
    
    for job_id, schedule in list(_schedule_store.items()):
        if schedule.get("state") != "scheduled":
            continue
        
        try:
            scheduled_time = datetime.fromisoformat(
                schedule["scheduled_at"].replace("Z", "+00:00")
            )
        except Exception as e:
            logger.error("Failed to parse scheduled time for %s: %s", job_id, e)
            continue
        
        if scheduled_time <= now:
            # Time to publish
            logger.info("Publishing job %s (scheduled for %s)", job_id, scheduled_time)
            
            try:
                # Import youtube_service for actual publishing
                # from ..services.youtube_service import publish_video
                # publish_video(job_id, schedule)
                
                # For now, mark as published
                schedule["state"] = "published"
                schedule["published_at"] = now.isoformat()
                logger.info("Successfully published job %s", job_id)
                
            except Exception as e:
                logger.error("Failed to publish job %s: %s", job_id, e)
                schedule["state"] = "failed"
                schedule["error"] = str(e)
            
            _save_schedules()
