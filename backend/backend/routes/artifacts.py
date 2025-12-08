from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from app.db import get_conn
from app.auth.security import get_current_user
from app.auth.guards import forbid
from app.artifacts_storage.factory import get_storage
from app.artifacts_storage.s3 import S3Storage
from app.plans.guards import require_feature

# OUTPUT_ROOT is configured in app.settings and exported as ARTIFACTS_ROOT in main
try:
    from app.settings import OUTPUT_ROOT as ARTIFACTS_ROOT
except Exception:
    # Fallback if import path differs
    ARTIFACTS_ROOT = Path(__file__).resolve().parents[2] / 'backend' / 'data' / 'artifacts'

router = APIRouter()

ALLOWED_FILES = {"thumb.png", "final.mp4", "tts.wav"}


def _ensure_owner(job_id: str, user) -> None:
    if not user:
        forbid()
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT user_id FROM jobs_index WHERE id = ?",
            (job_id,),
        ).fetchone()
        if not row:
            # Unknown job; do not leak existence
            forbid()
        if row["user_id"] != user["id"]:
            forbid()
    finally:
        conn.close()


@router.get("/{job_id}/manifest")
def get_manifest(job_id: str, user=Depends(get_current_user)):
    _ensure_owner(job_id, user)
    storage = get_storage()
    # If storage is S3 (presigned URLs), require feature access
    try:
        if isinstance(storage, S3Storage):
            require_feature(user.get("plan_id", "free"), "s3_urls")
    except HTTPException:
        # Feature gating should propagate to client
        raise
    except Exception:
        # In case of import/type issues, be permissive to avoid accidental lockouts
        pass
    # Keys follow pattern: {job_id}/<filename>
    return {
        "thumbnail": storage.get_url(f"{job_id}/thumb.png"),
        "video": storage.get_url(f"{job_id}/final.mp4"),
        "audio": storage.get_url(f"{job_id}/tts.wav"),
    }


@router.get("/{job_id}/{filename}")
def get_artifact(job_id: str, filename: str, user=Depends(get_current_user)):
    _ensure_owner(job_id, user)
    # Validate filename to a small allowlist
    if filename not in ALLOWED_FILES:
        raise HTTPException(status_code=404, detail="Artifact not found")

    path = ARTIFACTS_ROOT / job_id / filename
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Artifact not found")

    return FileResponse(path)
