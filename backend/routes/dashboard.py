"""
Dashboard router: Creator dashboard endpoints for job management.
GET /dashboard/jobs - List all jobs with filters/search
POST /dashboard/jobs/{job_id}/retry - Retry failed job
POST /dashboard/jobs/{job_id}/duplicate - Duplicate existing job
DELETE /dashboard/jobs/{job_id} - Archive job
GET /dashboard/stats - Dashboard statistics
"""
import os
import sys
import logging
import json
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

# Import OUTPUT_ROOT from settings
PLATFORM_ROOT = Path(__file__).resolve().parents[1]
if str(PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(PLATFORM_ROOT))
from backend.app.settings import OUTPUT_ROOT

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# ==============================================================================
# Configuration
# ==============================================================================
PIPELINE_OUTPUTS = OUTPUT_ROOT
JOBS_INDEX_FILE = PIPELINE_OUTPUTS / ".jobs_index.json"

# ==============================================================================
# Pydantic Models
# ==============================================================================
class JobSummary(BaseModel):
    """Summary of a render job for dashboard"""
    job_id: str
    topic: str
    state: str  # queued, running, completed, error, archived
    created_at: str
    updated_at: Optional[str] = None
    num_scenes: int = 0
    duration_sec: Optional[float] = None
    encoder: Optional[str] = None
    resolution: Optional[str] = None
    final_video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    error: Optional[str] = None
    tags: List[str] = []
    is_draft: bool = False
    archived: bool = False


class JobListResponse(BaseModel):
    """Paginated job list response"""
    jobs: List[JobSummary]
    total: int
    page: int
    page_size: int
    has_more: bool


class DashboardStats(BaseModel):
    """Dashboard statistics"""
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    running_jobs: int
    success_rate: float
    total_render_time_sec: float
    avg_render_time_sec: float


class RetryResponse(BaseModel):
    """Response from retry operation"""
    new_job_id: str
    status: str
    message: str


class DuplicateResponse(BaseModel):
    """Response from duplicate operation"""
    new_job_id: str
    status: str
    message: str


# ==============================================================================
# Job Index Management
# ==============================================================================
def load_jobs_index() -> Dict[str, Dict[str, Any]]:
    """Load jobs index from disk"""
    if not JOBS_INDEX_FILE.exists():
        return {}
    
    try:
        return json.loads(JOBS_INDEX_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error(f"Failed to load jobs index: {e}")
        return {}


def save_jobs_index(index: Dict[str, Dict[str, Any]]):
    """Save jobs index to disk"""
    try:
        PIPELINE_OUTPUTS.mkdir(parents=True, exist_ok=True)
        JOBS_INDEX_FILE.write_text(json.dumps(index, indent=2), encoding="utf-8")
    except Exception as e:
        logger.error(f"Failed to save jobs index: {e}")


def scan_pipeline_outputs() -> Dict[str, Dict[str, Any]]:
    """Scan pipeline_outputs directory and build index from job_summary.json files"""
    index = {}
    
    if not PIPELINE_OUTPUTS.exists():
        return index
    
    for job_dir in PIPELINE_OUTPUTS.iterdir():
        if not job_dir.is_dir() or job_dir.name.startswith("."):
            continue
        
        summary_path = job_dir / "job_summary.json"
        if not summary_path.exists():
            continue
        
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            job_id = summary.get("job_id", job_dir.name)
            
            # Extract metadata for index
            index[job_id] = {
                "job_id": job_id,
                "topic": summary.get("plan", {}).get("topic", "Untitled"),
                "state": summary.get("state", "unknown"),
                "created_at": summary.get("started_at", datetime.utcnow().isoformat()),
                "updated_at": summary.get("finished_at"),
                "num_scenes": len(summary.get("plan", {}).get("scenes", [])),
                "duration_sec": summary.get("elapsed_sec"),
                "encoder": summary.get("encoder"),
                "resolution": summary.get("resolution"),
                "final_video_url": summary.get("final_video_url"),
                "error": summary.get("error"),
                "tags": summary.get("tags", []),
                "is_draft": summary.get("is_draft", False),
                "archived": summary.get("archived", False)
            }
        except Exception as e:
            logger.warning(f"Failed to parse {summary_path}: {e}")
    
    return index


def rebuild_index():
    """Rebuild jobs index by scanning filesystem"""
    logger.info("Rebuilding jobs index...")
    index = scan_pipeline_outputs()
    save_jobs_index(index)
    logger.info(f"Rebuilt index with {len(index)} jobs")
    return index


def get_jobs_index(refresh: bool = False) -> Dict[str, Dict[str, Any]]:
    """Get jobs index (cached or rebuild)"""
    if refresh or not JOBS_INDEX_FILE.exists():
        return rebuild_index()
    return load_jobs_index()


# ==============================================================================
# API Endpoints
# ==============================================================================
@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    state: Optional[str] = Query(None, description="Filter by state"),
    search: Optional[str] = Query(None, description="Search by topic"),
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    refresh: bool = Query(False, description="Rebuild index from filesystem")
):
    """
    GET /dashboard/jobs
    
    List all render jobs with pagination, filtering, and search.
    
    Query params:
        - page: Page number (default: 1)
        - page_size: Items per page (default: 20, max: 100)
        - state: Filter by state (queued, running, completed, error, archived)
        - search: Search by topic (case-insensitive substring match)
        - tags: Filter by tags (comma-separated, OR match)
        - refresh: Rebuild index from filesystem (default: false)
    
    Returns:
        JobListResponse with jobs array and pagination metadata
    """
    try:
        # Get jobs index
        index = get_jobs_index(refresh=refresh)
        all_jobs = list(index.values())
        
        # Filter by state
        if state:
            all_jobs = [j for j in all_jobs if j.get("state") == state]
        
        # Filter by search
        if search:
            search_lower = search.lower()
            all_jobs = [j for j in all_jobs if search_lower in j.get("topic", "").lower()]
        
        # Filter by tags
        if tags:
            tag_list = [t.strip() for t in tags.split(",")]
            all_jobs = [
                j for j in all_jobs
                if any(tag in j.get("tags", []) for tag in tag_list)
            ]
        
        # Exclude archived by default unless explicitly filtering
        if state != "archived":
            all_jobs = [j for j in all_jobs if not j.get("archived", False)]
        
        # Sort by created_at descending
        all_jobs.sort(key=lambda j: j.get("created_at", ""), reverse=True)
        
        # Paginate
        total = len(all_jobs)
        offset = (page - 1) * page_size
        page_jobs = all_jobs[offset:offset + page_size]
        
        # Convert to JobSummary models
        jobs = [JobSummary(**j) for j in page_jobs]
        
        return JobListResponse(
            jobs=jobs,
            total=total,
            page=page,
            page_size=page_size,
            has_more=offset + page_size < total
        )
        
    except Exception as e:
        logger.exception("Failed to list jobs")
        raise HTTPException(status_code=500, detail=f"Failed to list jobs: {str(e)}")


@router.post("/jobs/{job_id}/retry", response_model=RetryResponse)
async def retry_job(job_id: str):
    """
    POST /dashboard/jobs/{job_id}/retry
    
    Retry a failed job by creating a new render with the same plan.
    Only works for jobs in 'error' state.
    
    Returns:
        RetryResponse with new job_id
    """
    try:
        # Load original job summary
        job_dir = PIPELINE_OUTPUTS / job_id
        summary_path = job_dir / "job_summary.json"
        
        if not summary_path.exists():
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        
        # Check state
        if summary.get("state") != "error":
            raise HTTPException(
                status_code=400,
                detail=f"Can only retry failed jobs. Current state: {summary.get('state')}"
            )
        
        # Extract plan
        plan = summary.get("plan")
        if not plan:
            raise HTTPException(status_code=400, detail="Job plan not found in summary")
        
        # Create new render job by calling render endpoint
        from routes.render import post_render, RenderPlan
        
        # Convert plan dict to RenderPlan model
        render_plan = RenderPlan(**plan)
        
        # Create new job (this will handle background processing)
        result = post_render(render_plan, None)
        
        return RetryResponse(
            new_job_id=result["job_id"],
            status="queued",
            message=f"Retry job created from {job_id}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to retry job {job_id}")
        raise HTTPException(status_code=500, detail=f"Retry failed: {str(e)}")


@router.post("/jobs/{job_id}/duplicate", response_model=DuplicateResponse)
async def duplicate_job(job_id: str):
    """
    POST /dashboard/jobs/{job_id}/duplicate
    
    Duplicate an existing job (any state) to create a new render.
    Useful for reusing successful configurations.
    
    Returns:
        DuplicateResponse with new job_id
    """
    try:
        # Load original job summary
        job_dir = PIPELINE_OUTPUTS / job_id
        summary_path = job_dir / "job_summary.json"
        
        if not summary_path.exists():
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        
        # Extract plan
        plan = summary.get("plan")
        if not plan:
            raise HTTPException(status_code=400, detail="Job plan not found in summary")
        
        # Create new render job
        from routes.render import post_render, RenderPlan
        
        render_plan = RenderPlan(**plan)
        result = post_render(render_plan, None)
        
        return DuplicateResponse(
            new_job_id=result["job_id"],
            status="queued",
            message=f"Duplicated from {job_id}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to duplicate job {job_id}")
        raise HTTPException(status_code=500, detail=f"Duplicate failed: {str(e)}")


@router.delete("/jobs/{job_id}")
async def archive_job(job_id: str):
    """
    DELETE /dashboard/jobs/{job_id}
    
    Archive a job (soft delete). Job remains on disk but marked as archived.
    To permanently delete, use force=true query param.
    
    Query params:
        - force: If true, permanently delete from disk (default: false)
    
    Returns:
        Success message
    """
    try:
        # Rebuild index to get latest jobs from filesystem
        index = rebuild_index()
        
        # If job exists in index, mark it archived there
        if job_id in index:
            index[job_id]["archived"] = True
            index[job_id]["updated_at"] = datetime.utcnow().isoformat()
            save_jobs_index(index)
        
        # Also mark in job_summary.json if it exists on disk
        job_dir = PIPELINE_OUTPUTS / job_id
        summary_path = job_dir / "job_summary.json"
        
        if job_dir.exists() and summary_path.exists():
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            summary["archived"] = True
            summary["archived_at"] = datetime.utcnow().isoformat()
            summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        elif job_id not in index:
            # Job not in index and not on disk
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        return {
            "status": "archived",
            "job_id": job_id,
            "message": "Job archived successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to archive job {job_id}")
        raise HTTPException(status_code=500, detail=f"Archive failed: {str(e)}")


@router.post("/jobs/{job_id}/restore")
async def restore_job(job_id: str):
    """
    POST /dashboard/jobs/{job_id}/restore
    
    Restore an archived job.
    
    Returns:
        Success message
    """
    try:
        job_dir = PIPELINE_OUTPUTS / job_id
        summary_path = job_dir / "job_summary.json"
        
        if not summary_path.exists():
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        summary["archived"] = False
        summary.pop("archived_at", None)
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        
        # Update index
        index = load_jobs_index()
        if job_id in index:
            index[job_id]["archived"] = False
            index[job_id]["updated_at"] = datetime.utcnow().isoformat()
            save_jobs_index(index)
        
        return {
            "status": "restored",
            "job_id": job_id,
            "message": "Job restored successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to restore job {job_id}")
        raise HTTPException(status_code=500, detail=f"Restore failed: {str(e)}")


@router.get("/stats", response_model=DashboardStats)
async def get_stats():
    """
    GET /dashboard/stats
    
    Get dashboard statistics summary.
    
    Returns:
        DashboardStats with counts and metrics
    """
    try:
        index = get_jobs_index()
        all_jobs = [j for j in index.values() if not j.get("archived", False)]
        
        total_jobs = len(all_jobs)
        completed_jobs = len([j for j in all_jobs if j.get("state") == "completed"])
        failed_jobs = len([j for j in all_jobs if j.get("state") == "error"])
        running_jobs = len([j for j in all_jobs if j.get("state") in ["queued", "running"]])
        
        success_rate = (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0.0
        
        # Calculate render times
        completed_with_time = [
            j for j in all_jobs
            if j.get("state") == "completed" and j.get("duration_sec")
        ]
        total_render_time = sum(j.get("duration_sec", 0) for j in completed_with_time)
        avg_render_time = (
            total_render_time / len(completed_with_time)
            if completed_with_time else 0.0
        )
        
        return DashboardStats(
            total_jobs=total_jobs,
            completed_jobs=completed_jobs,
            failed_jobs=failed_jobs,
            running_jobs=running_jobs,
            success_rate=round(success_rate, 2),
            total_render_time_sec=round(total_render_time, 2),
            avg_render_time_sec=round(avg_render_time, 2)
        )
        
    except Exception as e:
        logger.exception("Failed to get stats")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.post("/rebuild-index")
async def rebuild_index_endpoint():
    """
    POST /dashboard/rebuild-index
    
    Manually trigger jobs index rebuild from filesystem.
    Useful after manual file operations or recovery.
    
    Returns:
        Count of jobs indexed
    """
    try:
        index = rebuild_index()
        return {
            "status": "success",
            "jobs_indexed": len(index),
            "message": "Index rebuilt successfully"
        }
    except Exception as e:
        logger.exception("Failed to rebuild index")
        raise HTTPException(status_code=500, detail=f"Rebuild failed: {str(e)}")
