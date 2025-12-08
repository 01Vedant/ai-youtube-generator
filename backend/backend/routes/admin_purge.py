from fastapi import APIRouter, Depends, HTTPException
from app.auth.security import get_current_user
from app.purge.service import purge, now_utc


router = APIRouter(prefix="/admin/purge", tags=["admin"])


def _is_admin(user) -> bool:
    roles = user.get("roles") if isinstance(user, dict) else getattr(user, "roles", [])
    return roles and ("admin" in roles)


@router.post("/run")
async def run_purge(body: dict | None = None, user=Depends(get_current_user)):
    if not _is_admin(user):
        raise HTTPException(status_code=403, detail="Forbidden")
    dry_run = body.get("dry_run") if body else None
    older = body.get("older_than_days") if body else None
    return purge(dry_run=dry_run, older_than_days=older)


@router.get("/preview")
async def preview(user=Depends(get_current_user)):
    if not _is_admin(user):
        raise HTTPException(status_code=403, detail="Forbidden")
    from app.db import db
    import os
    from datetime import timedelta
    days = int(os.getenv("RETENTION_DAYS", "30"))
    safety = int(os.getenv("RETENTION_SAFETY_HOURS", "2"))
    cutoff = now_utc() - timedelta(days=days) - timedelta(hours=safety)
    rows = db.query(
        """
        SELECT id, completed_at
        FROM job_queue
        WHERE status='completed' AND completed_at IS NOT NULL
          AND completed_at < :cutoff
        ORDER BY completed_at ASC
        """,
        {"cutoff": cutoff.isoformat()},
    )
    candidates = [{"job_id": r["id"], "completed_at": r["completed_at"]} for r in rows]
    return {"candidates": candidates, "count": len(candidates), "cutoff": cutoff.isoformat()}
