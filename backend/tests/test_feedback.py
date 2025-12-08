from typing import Dict, Any
from app.routes.feedback import post_feedback, get_feedback_route, get_current_user
from app.db import init_db, list_feedback

def test_post_and_get_feedback():
    init_db()
    # Fake users
    user: Dict[str, Any] = {"id": "u1", "roles": []}
    admin: Dict[str, Any] = {"id": "admin", "roles": ["admin"]}

    payload = {"message": "Something is confusing on /render/abc", "meta": {"route": "/render/abc", "category": "confusion"}}
    # Inject user via dependency override style by directly passing as arg
    res = post_feedback(payload, user)
    assert res == {"ok": True}

    rows = list_feedback(10)
    assert any(r["message"].startswith("Something is confusing") for r in rows)
    assert any(r.get("meta_json") for r in rows)

    # Admin can fetch
    admin_rows = get_feedback_route(admin)
    assert isinstance(admin_rows, list)
    assert len(admin_rows) >= 1

def test_get_feedback_rejects_non_admin():
    init_db()
    user: Dict[str, Any] = {"id": "u1", "roles": []}
    try:
        _ = get_feedback_route(user)
        assert False, "Expected HTTPException for non-admin"
    except Exception as e:
        from fastapi import HTTPException
        assert isinstance(e, HTTPException)
        assert e.status_code == 403