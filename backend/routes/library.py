"""
Library routes: GET /library (scan pipeline_outputs), POST /library/{job_id}/duplicate, DELETE /library/{job_id}
Zero changes to P0 render logic - only reads job_summary.json files.
"""

import logging
import json
import sys
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query

# Import OUTPUT_ROOT from settings
PLATFORM_ROOT = Path(__file__).resolve().parents[1]
if str(PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(PLATFORM_ROOT))
from backend.app.settings import OUTPUT_ROOT
from backend.app.api_models.library import LibraryItem, FetchLibraryResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/library", tags=["library"])

PIPELINE_OUTPUTS = OUTPUT_ROOT


def scan_job_summaries(query: Optional[str] = None) -> List[dict]:
    """Scan pipeline_outputs/*/job_summary.json and return job data."""
    jobs = []
    
    if not PIPELINE_OUTPUTS.exists():
        return jobs
    
    for job_dir in PIPELINE_OUTPUTS.iterdir():
        if not job_dir.is_dir() or job_dir.name.startswith("."):
            continue
        
        # Check for soft delete marker
        deleted_marker = job_dir / ".deleted"
        if deleted_marker.exists():
            continue
        
        summary_path = job_dir / "job_summary.json"
        if not summary_path.exists():
            continue
        
        try:
            with open(summary_path, "r", encoding="utf-8") as f:
                summary = json.load(f)
            
            # Filter by query if provided
            if query:
                topic = summary.get("plan", {}).get("topic", "")
                if query.lower() not in topic.lower():
                    continue
            
            jobs.append(summary)
        except Exception as e:
            logger.warning(f"Failed to parse {summary_path}: {e}")
    
    return jobs


@router.get("", response_model=FetchLibraryResponse)
async def list_library(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    pageSize: int = Query(20, ge=1, le=100, description="Items per page"),
    sort: str = Query("created_at:desc", description="Sort field:direction"),
    query: Optional[str] = Query(None, description="Search by topic")
) -> FetchLibraryResponse:
    """
    GET /library?page&pageSize&sort&query
    
    Scan pipeline_outputs/*/job_summary.json and return paginated list.
    Returns standardized FetchLibraryResponse with LibraryItem entries.
    
    Query params:
        - page: Page number (default: 1)
        - pageSize: Items per page (default: 20, max: 100)
        - sort: Sort field and direction (default: "created_at:desc")
        - query: Search filter by topic
    """
    try:
        # Scan all job summaries
        all_jobs = scan_job_summaries(query=query)
        
        # Sort by created_at descending (default)
        all_jobs.sort(key=lambda j: j.get("started_at", ""), reverse=True)
        
        # Paginate
        total = len(all_jobs)
        offset = (page - 1) * pageSize
        page_jobs = all_jobs[offset:offset + pageSize]
        
        # Convert to LibraryItem DTOs
        entries = []
        for job in page_jobs:
            # Extract plan and audio metadata
            plan = job.get("plan", {})
            audio = job.get("audio", {})
            
            # Extract voice from voice_id (hi-IN-SwaraNeural -> Swara, hi-IN-DiyaNeural -> Diya)
            voice_id = plan.get("voice_id") or audio.get("voice_id")
            voice = None
            if voice_id:
                if "Swara" in voice_id:
                    voice = "Swara"
                elif "Diya" in voice_id:
                    voice = "Diya"
            
            # Extract template if used
            template = plan.get("template")
            
            entries.append(LibraryItem(
                id=job.get("job_id", ""),
                title=plan.get("topic", "Untitled"),
                created_at=job.get("started_at", ""),
                duration_sec=audio.get("total_duration_sec") or job.get("elapsed_sec"),
                voice=voice,
                template=template,
                state=job.get("state", "unknown"),
                thumbnail_url=job.get("thumbnail_url"),
                video_url=job.get("final_video_url"),
                error=job.get("error")
            ))
        
        return FetchLibraryResponse(
            entries=entries,
            total=total,
            page=page,
            pageSize=pageSize
        )
        
    except Exception as e:
        logger.exception("Failed to list library")
        raise HTTPException(status_code=500, detail=f"Failed to list library: {str(e)}")


@router.post("/{job_id}/duplicate")
async def duplicate_job(job_id: str):
    """
    POST /library/{job_id}/duplicate
    
    Copy plan from job_summary.json into a new draft render job.
    Returns new job_id for the duplicated job.
    
    This triggers a new render using the same configuration.
    """
    try:
        # Load original job summary
        job_dir = PIPELINE_OUTPUTS / job_id
        summary_path = job_dir / "job_summary.json"
        
        if not summary_path.exists():
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        with open(summary_path, "r", encoding="utf-8") as f:
            summary = json.load(f)
        
        # Extract plan
        plan = summary.get("plan")
        if not plan:
            raise HTTPException(
                status_code=400,
                detail="Job does not contain plan data (may be from older version)"
            )
        
        # Create new render job by calling render endpoint
        from routes.render import post_render, RenderPlan
        
        # Convert plan dict to RenderPlan model
        render_plan = RenderPlan(**plan)
        
        # Create new job (this will handle background processing)
        result = post_render(render_plan, None)
        
        return {
            "new_job_id": result["job_id"],
            "status": "queued",
            "message": f"Duplicated from {job_id}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to duplicate job {job_id}")
        raise HTTPException(status_code=500, detail=f"Duplicate failed: {str(e)}")


@router.delete("/{job_id}")
async def delete_job(job_id: str):
    """
    DELETE /library/{job_id}
    
    Soft delete: write .deleted sidecar file.
    DO NOT delete physical files - just mark as deleted.
    
    The job will be filtered out of library listings but remains recoverable.
    """
    try:
        job_dir = PIPELINE_OUTPUTS / job_id
        
        if not job_dir.exists():
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        # Write .deleted marker
        deleted_marker = job_dir / ".deleted"
        deleted_marker.write_text(
            json.dumps({
                "deleted_at": datetime.utcnow().isoformat(),
                "job_id": job_id
            }),
            encoding="utf-8"
        )
        
        return {
            "status": "deleted",
            "job_id": job_id,
            "message": "Job soft-deleted successfully (files preserved)"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to delete job {job_id}")
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")
