"""
Schedule routes - Lightweight alias to publish endpoints for UI clarity.
Maps /schedule/{job_id} to per-job schedule.json files in pipeline_outputs.
"""

import logging
import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Import OUTPUT_ROOT from settings
PLATFORM_ROOT = Path(__file__).resolve().parents[1]
if str(PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(PLATFORM_ROOT))
from backend.app.settings import OUTPUT_ROOT

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/schedule", tags=["schedule"])

PIPELINE_OUTPUTS = OUTPUT_ROOT


class ScheduleResponse(BaseModel):
    """Schedule status for a job."""
    job_id: str
    scheduled_at: Optional[str] = None


class ScheduleRequest(BaseModel):
    """Request to schedule a job."""
    scheduled_at: str  # ISO 8601 UTC datetime


def _get_schedule_file(job_id: str) -> Path:
    """Get path to schedule.json for a job."""
    return PIPELINE_OUTPUTS / job_id / "schedule.json"


def _validate_job_exists(job_id: str) -> None:
    """Ensure job exists by checking for job_summary.json."""
    job_dir = PIPELINE_OUTPUTS / job_id
    summary_file = job_dir / "job_summary.json"
    
    if not summary_file.exists():
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")


@router.get("/{job_id}")
async def get_schedule(job_id: str) -> ScheduleResponse:
    """
    GET /schedule/{job_id}
    
    Returns scheduled_at timestamp if job has a schedule, null otherwise.
    """
    try:
        _validate_job_exists(job_id)
        
        schedule_file = _get_schedule_file(job_id)
        
        if not schedule_file.exists():
            return ScheduleResponse(job_id=job_id, scheduled_at=None)
        
        with open(schedule_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return ScheduleResponse(
            job_id=job_id,
            scheduled_at=data.get("scheduled_at")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get schedule for {job_id}")
        raise HTTPException(status_code=500, detail=f"Failed to get schedule: {str(e)}")


@router.post("/{job_id}")
async def set_schedule(job_id: str, req: ScheduleRequest) -> ScheduleResponse:
    """
    POST /schedule/{job_id}
    
    Writes schedule.json with ISO 8601 UTC datetime.
    Validates datetime format and ensures it's in the future.
    """
    try:
        _validate_job_exists(job_id)
        
        # Validate ISO 8601 format
        try:
            scheduled_time = datetime.fromisoformat(req.scheduled_at.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid ISO 8601 datetime: {req.scheduled_at}"
            )
        
        # Ensure future time
        now = datetime.now(timezone.utc)
        if scheduled_time <= now:
            raise HTTPException(
                status_code=400,
                detail="Scheduled time must be in the future"
            )
        
        # Write schedule.json
        schedule_file = _get_schedule_file(job_id)
        schedule_file.parent.mkdir(parents=True, exist_ok=True)
        
        schedule_data = {
            "job_id": job_id,
            "scheduled_at": req.scheduled_at,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        with open(schedule_file, "w", encoding="utf-8") as f:
            json.dump(schedule_data, f, indent=2)
        
        logger.info(f"Scheduled job {job_id} for {req.scheduled_at}")
        
        return ScheduleResponse(
            job_id=job_id,
            scheduled_at=req.scheduled_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to set schedule for {job_id}")
        raise HTTPException(status_code=500, detail=f"Failed to set schedule: {str(e)}")


@router.delete("/{job_id}")
async def delete_schedule(job_id: str) -> dict:
    """
    DELETE /schedule/{job_id}
    
    Removes schedule.json file. No-op if no schedule exists.
    """
    try:
        _validate_job_exists(job_id)
        
        schedule_file = _get_schedule_file(job_id)
        
        if schedule_file.exists():
            schedule_file.unlink()
            logger.info(f"Removed schedule for job {job_id}")
            return {"status": "unscheduled", "job_id": job_id}
        else:
            return {"status": "no_schedule", "job_id": job_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to delete schedule for {job_id}")
        raise HTTPException(status_code=500, detail=f"Failed to delete schedule: {str(e)}")
