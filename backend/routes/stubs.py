from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter

router = APIRouter()

@router.get("/usage/today")
def usage_today():
    reset_at = datetime.now(timezone.utc).isoformat()
    return {"used": 0, "limit": 999999, "remaining": 999999, "reset_at": reset_at}

@router.get("/api/templates")
def list_templates():
    return []

@router.get("/projects")
def list_projects():
    return []