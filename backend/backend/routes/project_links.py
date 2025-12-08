from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from datetime import datetime

from app.db import get_conn
from app.auth.security import get_current_user

router = APIRouter()


@router.post("/{project_id}/assign")
def assign_to_project(project_id: str, body: dict, user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    job_id = body.get("job_id")
    if not job_id:
        raise HTTPException(status_code=400, detail="job_id required")
    conn = get_conn()
    try:
        # Ensure project ownership
        proj = conn.execute("SELECT id FROM projects WHERE id = ? AND user_id = ?", (project_id, user["id"]) ).fetchone()
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        # Upsert job into index and set project
        existing = conn.execute("SELECT id FROM jobs_index WHERE id = ? AND user_id = ?", (job_id, user["id"]) ).fetchone()
        now = datetime.utcnow().isoformat()
        if not existing:
            conn.execute(
                "INSERT INTO jobs_index (id, user_id, project_id, title, created_at) VALUES (?,?,?,?,?)",
                (job_id, user["id"], project_id, job_id, now),
            )
        else:
            conn.execute(
                "UPDATE jobs_index SET project_id = ? WHERE id = ? AND user_id = ?",
                (project_id, job_id, user["id"]),
            )
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@router.post("/{project_id}/unassign")
def unassign_from_project(project_id: str, body: dict, user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    job_id = body.get("job_id")
    if not job_id:
        raise HTTPException(status_code=400, detail="job_id required")
    conn = get_conn()
    try:
        # Ensure project ownership
        proj = conn.execute("SELECT id FROM projects WHERE id = ? AND user_id = ?", (project_id, user["id"]) ).fetchone()
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        conn.execute(
            "UPDATE jobs_index SET project_id = NULL WHERE id = ? AND user_id = ? AND project_id = ?",
            (job_id, user["id"], project_id),
        )
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()
