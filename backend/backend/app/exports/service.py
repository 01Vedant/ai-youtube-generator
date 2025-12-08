from __future__ import annotations
from pathlib import Path
from typing import Dict, Any
import json

from .provider import YouTubeProvider, ExportResult
from app.main import OUTPUT_ROOT  # artifacts root
from app.artifacts_storage.factory import get_storage
import logging


def create_export(job_id: str, meta: Dict[str, Any]) -> Dict[str, Any]:
    video_path = OUTPUT_ROOT / job_id / "final.mp4"
    if not video_path.exists():
        # Prefer storage existence when configured; do not download (note only)
        try:
            storage = get_storage()
            # Best-effort check; FS adapter mirrors local dir
            if getattr(storage, "exists", None) and storage.exists(f"{job_id}/final.mp4"):
                logging.info(
                    "Export: final.mp4 exists in storage but not locally for job %s; skipping download as per constraints",
                    job_id,
                )
        except Exception:
            pass
        # Maintain current behavior for tests: require local file
        raise FileNotFoundError(f"Video not found for job {job_id}: {video_path}")

    provider = YouTubeProvider(simulate=True)
    result: ExportResult = provider.upload(
        video_path=str(video_path),
        title=meta.get("title", f"Job {job_id}"),
        description=meta.get("description", ""),
        tags=meta.get("tags", []),
        visibility=meta.get("visibility", "unlisted"),
        user_id=meta.get("user_id"),
    )

    combined = {
        **result,
        "job_id": job_id,
    }

    # Persist combined under exports root (already written by provider)
    return {
        "export_id": combined["export_id"],
        "status": combined["status"],
        "youtube_url": combined.get("youtube_url"),
    }
