from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from datetime import datetime
import uuid

from app.db import get_conn
from app.auth.security import get_current_user
from app.projects.models import Project, ProjectCreate, ProjectUpdate

router = APIRouter()


@router.post("", response_model=Project)
def create_project(payload: ProjectCreate, user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    conn = get_conn()
    try:
        pid = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        conn.execute(
            "INSERT INTO projects (id, user_id, title, description, cover_thumb, created_at) VALUES (?,?,?,?,?,?)",
            (pid, user["id"], payload.title, payload.description, None, now),
        )
        conn.commit()
        return Project(id=pid, title=payload.title, description=payload.description, cover_thumb=None, created_at=now, video_count=0)
    finally:
        conn.close()


@router.get("", response_model=list[Project])
def list_projects(user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    conn = get_conn()
    try:
        rows = conn.execute(
            (
                """
                SELECT p.id, p.title, p.description, p.cover_thumb, p.created_at,
                    (
                        SELECT COUNT(1)
                        FROM jobs_index j
                        WHERE j.user_id = p.user_id AND j.project_id = p.id
                    ) AS video_count
                FROM projects p
                WHERE p.user_id = ?
                ORDER BY p.created_at DESC
                """
            ),
            (user["id"],),
        ).fetchall()
        return [Project(**dict(r)) for r in rows]
    finally:
        conn.close()


@router.get("/{project_id}")
def get_project_detail(project_id: str, user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    conn = get_conn()
    try:
        proj = conn.execute(
            "SELECT id, title, description, cover_thumb, created_at FROM projects WHERE id = ? AND user_id = ?",
            (project_id, user["id"]),
        ).fetchone()
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        entries = conn.execute(
            "SELECT id, title, created_at FROM jobs_index WHERE user_id = ? AND project_id = ? ORDER BY created_at DESC",
            (user["id"], project_id),
        ).fetchall()
        return {
            "project": Project(**dict(proj)),
            "entries": [dict(e) for e in entries],
            "total": len(entries),
        }
    finally:
        conn.close()


@router.patch("/{project_id}", response_model=Project)
def update_project(project_id: str, payload: ProjectUpdate, user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM projects WHERE id = ? AND user_id = ?", (project_id, user["id"]) ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Project not found")
        title = payload.title if payload.title is not None else row["title"]
        desc = payload.description if payload.description is not None else row["description"]
        cover = payload.cover_thumb if payload.cover_thumb is not None else row["cover_thumb"]
        conn.execute(
            "UPDATE projects SET title = ?, description = ?, cover_thumb = ? WHERE id = ? AND user_id = ?",
            (title, desc, cover, project_id, user["id"]),
        )
        conn.commit()
        return Project(id=project_id, title=title, description=desc, cover_thumb=cover, created_at=row["created_at"])
    finally:
        conn.close()


@router.delete("/{project_id}")
def delete_project(project_id: str, user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    conn = get_conn()
    try:
        # Ensure ownership
        proj = conn.execute("SELECT id FROM projects WHERE id = ? AND user_id = ?", (project_id, user["id"]) ).fetchone()
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        count = conn.execute(
            "SELECT COUNT(1) AS c FROM jobs_index WHERE user_id = ? AND project_id = ?",
            (user["id"], project_id),
        ).fetchone()["c"]
        if count > 0:
            raise HTTPException(status_code=409, detail="Project has linked videos")
        conn.execute("DELETE FROM projects WHERE id = ? AND user_id = ?", (project_id, user["id"]))
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()
