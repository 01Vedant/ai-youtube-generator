from __future__ import annotations
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from app.db import get_conn
from app.settings import FEATURE_TEMPLATES_MARKETPLACE
from app.auth.security import get_current_user
import uuid
import json
from datetime import datetime
try:
    from backend.app.logs.activity import log_event
except Exception:
    def log_event(*args, **kwargs):
        return None

router = APIRouter(prefix="/marketplace", tags=["marketplace"])


def require_marketplace_enabled():
    if not FEATURE_TEMPLATES_MARKETPLACE:
        raise HTTPException(status_code=404, detail="Not found")


def _row_to_dict(r) -> dict:
    return {k: r[k] for k in r.keys()}


@router.get("/templates")
def list_marketplace_templates(q: Optional[str] = None, category: Optional[str] = None, sort: str = "new", page: int = 1, page_size: int = 20):
    require_marketplace_enabled()
    page = max(1, page)
    page_size = max(1, min(50, page_size))
    offset = (page - 1) * page_size
    like = f"%{q}%" if q else None
    conn = get_conn()
    try:
        where = "visibility IN ('builtin','shared')"
        params = []
        if like:
            where += " AND (title LIKE ? OR description LIKE ?)"
            params += [like, like]
        if category:
            where += " AND category = ?"
            params += [category]
        order = "created_at DESC" if sort == "new" else "downloads DESC, created_at DESC"
        total_row = conn.execute(f"SELECT COUNT(1) AS c FROM templates WHERE {where}", tuple(params)).fetchone()
        rows = conn.execute(
            f"SELECT id, title, description, category, thumb, visibility, user_id, downloads, created_at FROM templates WHERE {where} ORDER BY {order} LIMIT ? OFFSET ?",
            tuple(params + [page_size, offset])
        ).fetchall()
        return {
            "items": [_row_to_dict(r) for r in rows],
            "total": int(total_row["c"] if total_row else 0),
            "page": page,
            "page_size": page_size,
        }
    finally:
        conn.close()


@router.get("/templates/{template_id}")
def get_marketplace_template(template_id: str):
    require_marketplace_enabled()
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT id, title, description, category, thumb, plan_json, inputs_schema, visibility, user_id, downloads, created_at FROM templates WHERE id=?",
            (template_id,)
        ).fetchone()
        if not row or row["visibility"] not in ("builtin", "shared"):
            raise HTTPException(status_code=404, detail="Template not found")
        return _row_to_dict(row)
    finally:
        conn.close()


@router.post("/templates/{template_id}/duplicate")
def duplicate_marketplace_template(template_id: str, user=Depends(get_current_user)):
    require_marketplace_enabled()
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    conn = get_conn()
    try:
        src = conn.execute(
            "SELECT id, title, description, category, thumb, plan_json, visibility, user_id FROM templates WHERE id=?",
            (template_id,)
        ).fetchone()
        if not src:
            raise HTTPException(status_code=404, detail="Template not found")
        if src["visibility"] not in ("builtin", "shared") and src["user_id"] != user.get("id"):
            raise HTTPException(status_code=403, detail="Forbidden")
        new_id = str(uuid.uuid4())
        title = f"Copy of {src['title']}"
        if len(title) > 120:
            title = title[:120]
        now = datetime.utcnow().isoformat() + "Z"
        conn.execute(
            (
                "INSERT INTO templates (id, title, description, category, thumb, plan_json, inputs_schema, visibility, user_id, downloads, created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)"
            ),
            (new_id, title, src["description"], src["category"], src["thumb"], src["plan_json"], None, "private", user["id"], 0, now)
        )
        # Best-effort increment downloads for source
        try:
            conn.execute("UPDATE templates SET downloads = COALESCE(downloads,0) + 1 WHERE id=?", (template_id,))
        except Exception:
            pass
        conn.commit()
        row = conn.execute(
            "SELECT id, title, description, category, thumb, plan_json, inputs_schema, visibility, user_id, downloads, created_at FROM templates WHERE id=?",
            (new_id,)
        ).fetchone()
        created = _row_to_dict(row)
        # Best-effort activity log
        try:
            log_event(new_id, "template_duplicated", "Duplicated template", {"src_id": template_id, "new_id": new_id, "user_id": user.get("id")})
        except Exception:
            pass
        return created
    finally:
        conn.close()


@router.get("/templates/{template_id}/stats")
def get_template_stats(template_id: str, user=Depends(get_current_user)):
    require_marketplace_enabled()
    # Owner or admin-only (basic owner guard here)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    conn = get_conn()
    try:
        tpl = conn.execute("SELECT user_id, downloads FROM templates WHERE id=?", (template_id,)).fetchone()
        if not tpl:
            raise HTTPException(status_code=404, detail="Template not found")
        if tpl["user_id"] != user.get("id"):
            # In a full implementation, check admin flag; keep simple here
            raise HTTPException(status_code=403, detail="Forbidden")
        downloads = int(tpl["downloads"] or 0)
        # Best-effort derive renders_from_tpl by counting jobs_index parent_job_id
        row = conn.execute("SELECT COUNT(1) AS c, MAX(created_at) AS last FROM jobs_index WHERE parent_job_id = ?", (f"tpl:{template_id}",)).fetchone()
        return {
            "downloads": downloads,
            "renders_from_tpl": int(row["c"] if row and row["c"] is not None else 0),
            "last_duplicated_at": None,  # placeholder (could track separately)
        }
    finally:
        conn.close()
