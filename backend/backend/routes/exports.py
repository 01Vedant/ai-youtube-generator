from __future__ import annotations
from typing import Literal, Optional, List
from pathlib import Path
import json
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from app.main import OUTPUT_ROOT
from app.exports.service import create_export
from app.auth.security import get_current_user
from app.db import get_conn
from app.auth.guards import forbid
from app.plans.guards import require_feature as require_plan_feature
from app.auth.guards import require_feature as require_global_feature

router = APIRouter()


class ExportYouTubeReq(BaseModel):
    job_id: str
    title: str
    description: Optional[str] = ""
    tags: Optional[List[str]] = Field(default_factory=list)
    visibility: Optional[Literal["public", "unlisted", "private"]] = "unlisted"


class ExportYouTubeRes(BaseModel):
    export_id: str
    status: Literal["completed", "failed", "queued"]
    youtube_url: Optional[str]


@router.post("/youtube", response_model=ExportYouTubeRes)
def export_youtube(req: ExportYouTubeReq, user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    # Feature gate
    # Global feature flag
    require_global_feature("youtube_export")
    # Plan gate
    require_plan_feature(user.get("plan_id", "free"), "youtube_export")
    # Validate video exists
    video_path = OUTPUT_ROOT / req.job_id / "final.mp4"
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video not found")
    # Ensure job belongs to user via jobs_index
    conn = get_conn()
    try:
        row = conn.execute("SELECT user_id FROM jobs_index WHERE id = ?", (req.job_id,)).fetchone()
        if not row or row["user_id"] != user["id"]:
            forbid()
    finally:
        conn.close()

    result = create_export(req.job_id, req.dict() | {"user_id": user["id"]})
    return result


@router.get("/{export_id}")
def get_export(export_id: str, user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    exports_root = Path(__file__).resolve().parents[1] / "data" / "exports"
    record_path = exports_root / f"{export_id}.json"
    if not record_path.exists():
        raise HTTPException(status_code=404, detail="Export not found")
    data = json.loads(record_path.read_text(encoding="utf-8"))
    if data.get("user_id") != user["id"]:
        forbid()
    return data
