import os
import sys
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from app.artifacts_storage.factory import get_storage
from app.artifacts_storage.base import Storage


def jsonlog(obj: dict) -> None:
    try:
        sys.stdout.write(json.dumps(obj, separators=(",", ":")) + "\n")
    except Exception:
        pass


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


def purge(dry_run: bool | None = None, older_than_days: int | None = None) -> Dict[str, Any]:
    storage: Storage = get_storage()
    retention_days = older_than_days if older_than_days is not None else _env_int("RETENTION_DAYS", 30)
    safety_hours = _env_int("RETENTION_SAFETY_HOURS", 2)
    min_jobs = _env_int("RETENTION_MIN_JOBS", 50)
    is_dry = dry_run if dry_run is not None else (_env_int("RETENTION_DRY_RUN", 0) == 1)

    cutoff = now_utc() - timedelta(days=retention_days)
    cutoff_safe = cutoff - timedelta(hours=safety_hours)

    # Query DB for candidates
    from app.db import db
    # Ensure purged_at column exists (safe migration)
    try:
        db.execute("ALTER TABLE jobs_index ADD COLUMN purged_at TEXT NULL")
    except Exception:
        pass

    total_completed = db.scalar("SELECT COUNT(1) FROM job_queue WHERE status='completed' AND completed_at IS NOT NULL") or 0
    candidates: List[Dict[str, Any]] = []
    if total_completed >= min_jobs:
        rows = db.query(
            """
            SELECT id, completed_at
            FROM job_queue
            WHERE status='completed' AND completed_at IS NOT NULL
              AND completed_at < :cutoff_safe
            """,
            {"cutoff_safe": cutoff_safe.isoformat()},
        )
        for r in rows:
            candidates.append({"job_id": r["id"], "completed_at": r["completed_at"]})

    deleted_files = 0
    scanned = len(candidates)
    eligible = 0

    for c in candidates:
        job_id = c["job_id"]
        eligible += 1
        keys = [f"{job_id}/final.mp4", f"{job_id}/thumb.png", f"{job_id}/tts.wav"]
        for k in keys:
            if storage.exists(k):
                if is_dry:
                    jsonlog({"type": "purge_dry_run", "job_id": job_id, "key": k})
                else:
                    storage.delete(k)
                    deleted_files += 1
                    jsonlog({"type": "purge_delete", "job_id": job_id, "key": k})
        # Mark index row purged
        try:
            db.execute("UPDATE jobs_index SET purged_at=:t WHERE job_id=:jid", {"t": now_utc().isoformat(), "jid": job_id})
            # Write activity log (best-effort)
            db.execute("INSERT INTO job_activity(job_id, type, message, created_at) VALUES(:jid, 'purged', 'artifacts purged', :t)", {"jid": job_id, "t": now_utc().isoformat()})
        except Exception:
            pass

    summary = {"scanned": scanned, "eligible": eligible, "deleted_files": deleted_files, "dry_run": is_dry, "cutoff": cutoff_safe.isoformat()}
    jsonlog({"type": "purge_summary", **summary})
    return summary
