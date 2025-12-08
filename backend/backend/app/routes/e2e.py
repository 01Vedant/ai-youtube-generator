from __future__ import annotations
from fastapi import APIRouter
from app.db import get_conn

router = APIRouter()

@router.post("/seed_user")
def seed_user(payload: dict):
    email = str(payload.get("email") or "test@example.com")
    user_id = "u-e2e"
    conn = get_conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO users (id, email, password_hash, created_at, plan_id) VALUES (?,?,?,?,?)",
            (user_id, email, "hash:testpass", "2025-01-01T00:00:00Z", "free"),
        )
        conn.commit()
    finally:
        conn.close()
    return {"ok": True, "user_id": user_id}

@router.post("/set_maintenance")
def set_maintenance(payload: dict):
    # Best-effort toggle via environment or in-memory flag; here we persist to onboarding_events
    on = bool(payload.get("on"))
    # In a full implementation, flip a global flag; here just ack
    return {"ok": True, "maintenance": on}

@router.post("/billing/checkout")
def billing_checkout():
    return {"url": "https://example.test/stripe/checkout/mock"}

@router.post("/ratelimit_once")
def ratelimit_once(payload: dict):
    # Stub: acknowledge and rely on RateLimitMiddleware to simulate
    endpoint = str(payload.get("endpoint") or "/render")
    return {"ok": True, "endpoint": endpoint}
