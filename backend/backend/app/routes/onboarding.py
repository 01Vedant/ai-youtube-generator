from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict
from datetime import datetime

from app.db import get_conn

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

VALID_EVENTS = {"welcome_seen", "created_project", "rendered_video", "exported_video"}


def _ensure_table(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS onboarding_events(
          user_id TEXT NOT NULL,
          event TEXT NOT NULL,
          created_at TEXT NOT NULL,
          UNIQUE(user_id,event)
        );
        """
    )
    conn.commit()


def record_onboarding_event(conn, user_id: str, event: str) -> None:
    if event not in VALID_EVENTS:
        return
    _ensure_table(conn)
    try:
        conn.execute(
            "INSERT OR IGNORE INTO onboarding_events(user_id,event,created_at) VALUES (?,?,?)",
            (user_id, event, datetime.utcnow().isoformat()),
        )
        conn.commit()
    except Exception:
        pass


def get_onboarding_state(conn, user_id: str) -> Dict:
    _ensure_table(conn)
    cur = conn.execute(
        "SELECT event FROM onboarding_events WHERE user_id=?",
        (user_id,),
    )
    events = {row[0] for row in cur.fetchall()}
    steps = {
        "created_project": "created_project" in events,
        "rendered_video": "rendered_video" in events,
        "exported_video": "exported_video" in events,
    }
    state = {
        "seen_welcome": "welcome_seen" in events,
        "steps": steps,
        "recommended_template_id": None,
    }
    try:
        cur2 = conn.execute(
            "SELECT id FROM templates_builtin ORDER BY popularity DESC LIMIT 1"
        )
        row = cur2.fetchone()
        if row:
            state["recommended_template_id"] = row[0]
    except Exception:
        pass
    return state


def _get_user_id() -> str:
    return "dev-user"


@router.get("/state")
def onboarding_state():
    conn = get_conn()
    state = get_onboarding_state(conn, _get_user_id())
    return JSONResponse(state)


@router.post("/event")
def onboarding_event(payload: Dict[str, str]):
    event = payload.get("event")
    if event not in VALID_EVENTS:
        raise HTTPException(status_code=400, detail="invalid event")
    conn = get_conn()
    record_onboarding_event(conn, _get_user_id(), event)
    return {"ok": True}
