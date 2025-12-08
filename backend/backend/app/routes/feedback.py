from fastapi import APIRouter, Depends, HTTPException
from typing import Any, Dict, List, Optional
from uuid import uuid4
from datetime import datetime, timezone
import json

from app.db import insert_feedback, list_feedback

# Placeholder auth dependency; replace with project-specific user retrieval
def get_current_user() -> Dict[str, Any]:
    # This should be wired to your actual auth
    return {"id": "dev-user", "roles": []}

def require_admin(user: Dict[str, Any]) -> None:
    roles = user.get("roles") or []
    if "admin" not in roles:
        raise HTTPException(status_code=403, detail="Forbidden")

router = APIRouter()


@router.post("")
def post_feedback(payload: Dict[str, Any], user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    message = payload.get("message")
    if not isinstance(message, str) or not message.strip():
        raise HTTPException(status_code=400, detail="message is required")
    meta = payload.get("meta")
    rec = {
        "id": uuid4().hex,
        "user_id": user.get("id"),
        "message": message.strip(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "meta_json": json.dumps(meta) if meta is not None else None,
    }
    insert_feedback(rec)
    return {"ok": True}


@router.get("")
def get_feedback_route(user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    require_admin(user)
    return list_feedback(200)