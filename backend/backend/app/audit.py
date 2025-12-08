"""
Audit logging: JSONL entries per action with daily rotation.
Writes to platform/audit/audit-YYYYMMDD.jsonl
"""
import logging
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

AUDIT_DIR = Path("platform/audit")


def ensure_audit_dir():
    """Ensure audit directory exists."""
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)


def get_audit_file_path() -> Path:
    """Get today's audit file path."""
    today = datetime.utcnow().strftime("%Y%m%d")
    return AUDIT_DIR / f"audit-{today}.jsonl"


def append_audit_log(
    action: str,
    job_id: Optional[str] = None,
    user_id: Optional[str] = None,
    request_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    status: str = "success",
    error: Optional[str] = None,
):
    """
    Append structured audit entry to JSONL log.
    
    Args:
        action: Action type (enqueue, status, cancel, publish, etc.)
        job_id: Associated job ID
        user_id: Associated user ID
        request_id: Correlated request ID
        details: Additional context dict
        status: success, failure, denied, etc.
        error: Error message if applicable
    """
    try:
        ensure_audit_dir()
        
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "action": action,
            "job_id": job_id,
            "user_id": user_id,
            "request_id": request_id,
            "status": status,
            "error": error,
            **(details or {}),
        }
        
        # Append to file
        audit_file = get_audit_file_path()
        with open(audit_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
        
        logger.debug("Audit logged: %s (job=%s)", action, job_id)
    except Exception as e:
        logger.error("Audit log failed: %s", e)


def log_job_enqueued(
    job_id: str,
    user_id: Optional[str] = None,
    request_id: Optional[str] = None,
    topic: Optional[str] = None,
    num_scenes: int = 0,
    cost_estimate: Optional[float] = None,
):
    """Log job enqueued event."""
    append_audit_log(
        action="job_enqueued",
        job_id=job_id,
        user_id=user_id,
        request_id=request_id,
        details={
            "topic": topic,
            "num_scenes": num_scenes,
            "cost_estimate_usd": cost_estimate,
        },
    )


def log_job_status_checked(
    job_id: str,
    user_id: Optional[str] = None,
    request_id: Optional[str] = None,
    state: Optional[str] = None,
):
    """Log job status read event."""
    append_audit_log(
        action="job_status_read",
        job_id=job_id,
        user_id=user_id,
        request_id=request_id,
        details={"state": state},
    )


def log_job_canceled(
    job_id: str,
    user_id: Optional[str] = None,
    request_id: Optional[str] = None,
    reason: Optional[str] = None,
):
    """Log job cancellation event."""
    append_audit_log(
        action="job_cancel_requested",
        job_id=job_id,
        user_id=user_id,
        request_id=request_id,
        details={"reason": reason},
    )


def log_job_completed(
    job_id: str,
    user_id: Optional[str] = None,
    state: str = "success",
    duration_sec: Optional[float] = None,
    error: Optional[str] = None,
):
    """Log job completion event."""
    append_audit_log(
        action="job_completed",
        job_id=job_id,
        user_id=user_id,
        status=state,
        details={"duration_sec": duration_sec},
        error=error,
    )


def log_rate_limit_violation(
    request_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_id: Optional[str] = None,
):
    """Log rate limit violation."""
    append_audit_log(
        action="rate_limit_exceeded",
        user_id=user_id,
        request_id=request_id,
        status="denied",
        details={"ip_address": ip_address},
    )


def log_quota_violation(
    quota_type: str,
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    details: Optional[Dict] = None,
):
    """Log quota violation."""
    append_audit_log(
        action="quota_exceeded",
        user_id=user_id,
        request_id=request_id,
        status="denied",
        details={"quota_type": quota_type, **(details or {})},
    )
