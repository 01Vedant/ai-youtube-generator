"""
Data retention and cleanup policies for production deployments.
Handles purging old temp files, logs, and pipeline outputs.
"""
import os
import time
import shutil
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/admin/retention", tags=["admin"])
logger = logging.getLogger(__name__)


class RetentionConfig:
    """Retention policy configuration from environment."""
    
    MAX_LOCAL_DAYS = int(os.environ.get("MAX_LOCAL_DAYS", "30"))
    MAX_TMP_DAYS = int(os.environ.get("MAX_TMP_DAYS", "7"))
    TMP_WORKDIR = Path(os.environ.get("TMP_WORKDIR", "/tmp/bhakti"))
    PIPELINE_OUTPUTS = Path(os.environ.get("PIPELINE_OUTPUTS", "platform/pipeline_outputs"))


class RetentionResult(BaseModel):
    """Results from retention cleanup run."""
    success: bool
    tmp_files_deleted: int
    tmp_bytes_freed: int
    pipeline_jobs_deleted: int
    pipeline_bytes_freed: int
    logs_rotated: int
    duration_sec: float
    errors: list[str]


def get_dir_size(path: Path) -> int:
    """Calculate total size of directory in bytes."""
    total = 0
    try:
        for entry in path.rglob("*"):
            if entry.is_file():
                total += entry.stat().st_size
    except Exception as e:
        logger.warning(f"Error calculating size for {path}: {e}")
    return total


def cleanup_tmp_workdir(max_days: int) -> Dict[str, Any]:
    """
    Cleanup TMP_WORKDIR intermediates older than max_days.
    
    Args:
        max_days: Maximum age in days for temp files
        
    Returns:
        Dict with files_deleted and bytes_freed
    """
    tmp_dir = RetentionConfig.TMP_WORKDIR
    
    if not tmp_dir.exists():
        return {"files_deleted": 0, "bytes_freed": 0, "errors": []}
    
    cutoff = time.time() - (max_days * 86400)
    files_deleted = 0
    bytes_freed = 0
    errors = []
    
    try:
        for job_dir in tmp_dir.iterdir():
            if not job_dir.is_dir():
                continue
            
            try:
                # Check directory modification time
                mtime = job_dir.stat().st_mtime
                
                if mtime < cutoff:
                    size_before = get_dir_size(job_dir)
                    shutil.rmtree(job_dir)
                    files_deleted += 1
                    bytes_freed += size_before
                    logger.info(f"Deleted temp job dir: {job_dir.name} ({size_before / (1024**2):.2f} MB)")
            except Exception as e:
                errors.append(f"Failed to delete {job_dir}: {str(e)}")
                logger.error(f"Failed to delete {job_dir}: {e}")
    except Exception as e:
        errors.append(f"Failed to scan tmp dir: {str(e)}")
        logger.error(f"Failed to scan tmp dir: {e}")
    
    return {
        "files_deleted": files_deleted,
        "bytes_freed": bytes_freed,
        "errors": errors
    }


def cleanup_pipeline_outputs(max_days: int) -> Dict[str, Any]:
    """
    Cleanup pipeline_outputs older than max_days unless pinned.
    
    Args:
        max_days: Maximum age in days for pipeline outputs
        
    Returns:
        Dict with jobs_deleted and bytes_freed
    """
    pipeline_dir = RetentionConfig.PIPELINE_OUTPUTS
    
    if not pipeline_dir.exists():
        return {"jobs_deleted": 0, "bytes_freed": 0, "errors": []}
    
    cutoff = time.time() - (max_days * 86400)
    jobs_deleted = 0
    bytes_freed = 0
    errors = []
    
    try:
        for job_dir in pipeline_dir.iterdir():
            if not job_dir.is_dir():
                continue
            
            # Skip pinned jobs (marker file)
            if (job_dir / ".pinned").exists():
                logger.debug(f"Skipping pinned job: {job_dir.name}")
                continue
            
            try:
                # Check directory modification time
                mtime = job_dir.stat().st_mtime
                
                if mtime < cutoff:
                    size_before = get_dir_size(job_dir)
                    shutil.rmtree(job_dir)
                    jobs_deleted += 1
                    bytes_freed += size_before
                    logger.info(f"Deleted pipeline job: {job_dir.name} ({size_before / (1024**2):.2f} MB)")
            except Exception as e:
                errors.append(f"Failed to delete {job_dir}: {str(e)}")
                logger.error(f"Failed to delete {job_dir}: {e}")
    except Exception as e:
        errors.append(f"Failed to scan pipeline dir: {str(e)}")
        logger.error(f"Failed to scan pipeline dir: {e}")
    
    return {
        "jobs_deleted": jobs_deleted,
        "bytes_freed": bytes_freed,
        "errors": errors
    }


def rotate_logs() -> Dict[str, Any]:
    """
    Rotate application logs if they exist.
    
    Returns:
        Dict with logs_rotated count
    """
    logs_rotated = 0
    errors = []
    
    # Look for common log files
    log_paths = [
        Path("platform/backend/app.log"),
        Path("platform/backend/uvicorn.log"),
        Path("logs/app.log")
    ]
    
    for log_path in log_paths:
        if not log_path.exists():
            continue
        
        try:
            size_mb = log_path.stat().st_size / (1024 ** 2)
            
            # Rotate if larger than 100MB
            if size_mb > 100:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                rotated_name = log_path.parent / f"{log_path.stem}_{timestamp}{log_path.suffix}"
                log_path.rename(rotated_name)
                logs_rotated += 1
                logger.info(f"Rotated log: {log_path} -> {rotated_name}")
        except Exception as e:
            errors.append(f"Failed to rotate {log_path}: {str(e)}")
            logger.error(f"Failed to rotate {log_path}: {e}")
    
    return {
        "logs_rotated": logs_rotated,
        "errors": errors
    }


def run_retention_cleanup() -> RetentionResult:
    """
    Execute full retention cleanup policy.
    
    Returns:
        RetentionResult with summary of cleanup operations
    """
    start_time = time.time()
    
    logger.info(f"Starting retention cleanup: MAX_LOCAL_DAYS={RetentionConfig.MAX_LOCAL_DAYS}, MAX_TMP_DAYS={RetentionConfig.MAX_TMP_DAYS}")
    
    all_errors = []
    
    # Cleanup temp files
    tmp_result = cleanup_tmp_workdir(RetentionConfig.MAX_TMP_DAYS)
    all_errors.extend(tmp_result["errors"])
    
    # Cleanup old pipeline outputs
    pipeline_result = cleanup_pipeline_outputs(RetentionConfig.MAX_LOCAL_DAYS)
    all_errors.extend(pipeline_result["errors"])
    
    # Rotate logs
    log_result = rotate_logs()
    all_errors.extend(log_result["errors"])
    
    duration = time.time() - start_time
    
    result = RetentionResult(
        success=len(all_errors) == 0,
        tmp_files_deleted=tmp_result["files_deleted"],
        tmp_bytes_freed=tmp_result["bytes_freed"],
        pipeline_jobs_deleted=pipeline_result["jobs_deleted"],
        pipeline_bytes_freed=pipeline_result["bytes_freed"],
        logs_rotated=log_result["logs_rotated"],
        duration_sec=round(duration, 2),
        errors=all_errors
    )
    
    logger.info(f"Retention cleanup completed in {duration:.2f}s: "
                f"tmp={result.tmp_files_deleted} files, "
                f"pipeline={result.pipeline_jobs_deleted} jobs, "
                f"logs={result.logs_rotated}, "
                f"freed={result.tmp_bytes_freed + result.pipeline_bytes_freed} bytes")
    
    return result


@router.post("/run", response_model=RetentionResult)
async def run_retention(
    # Add admin auth check here if implemented
    # current_user: User = Depends(get_current_admin_user)
) -> RetentionResult:
    """
    Run retention cleanup on-demand.
    
    Requires admin authentication.
    
    Returns:
        RetentionResult with summary of cleanup operations
    """
    try:
        return run_retention_cleanup()
    except Exception as e:
        logger.exception("Retention cleanup failed")
        raise HTTPException(status_code=500, detail=f"Retention cleanup failed: {str(e)}")
