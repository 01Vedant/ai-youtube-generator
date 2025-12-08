import json
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.backend.main import app
from app.db import init_db, get_conn

client = TestClient(app)


def auth_headers():
    # For this test environment, assume no auth middleware or use a stub
    return {}


def test_template_plan_crud():
    init_db()
    # create
    payload = {
        "title": "Editor Test",
        "plan_json": {"title": "t", "scenes": [{"script": "a", "duration_sec": 1}]}
    }
    r = client.post("/templates", json=payload, headers=auth_headers())
    assert r.status_code in (200, 201)
    data = r.json()
    tpl_id = data["id"]

    # get plan
    r = client.get(f"/templates/{tpl_id}/plan", headers=auth_headers())
    assert r.status_code == 200
    plan = r.json()
    assert isinstance(plan.get("scenes"), list)

    # put plan (add scene)
    new_plan = plan
    new_plan["scenes"].append({"script": "b", "duration_sec": 2})
    r = client.put(f"/templates/{tpl_id}/plan", json=new_plan, headers=auth_headers())
    assert r.status_code == 200
    saved = r.json()
    assert len(saved["plan"]["scenes"]) == 2

    # get reflects changes
    r = client.get(f"/templates/{tpl_id}/plan", headers=auth_headers())
    assert r.status_code == 200
    plan2 = r.json()
    assert len(plan2["scenes"]) == 2


def test_warnings_and_builtin_readonly():
    init_db()
    # Create invalid plan (zero duration)
    payload = {"title": "Warn Test", "plan_json": {"title": "", "duration_sec": 0, "scenes": []}}
    r = client.post("/templates", json=payload, headers=auth_headers())
    assert r.status_code in (200, 201)
    data = r.json()
    assert "warnings" in data

    # Builtin plan is read-only
    # Seed should have inserted builtins; pick one id
    conn = get_conn()
    try:
        row = conn.execute("SELECT id FROM templates WHERE visibility='builtin' LIMIT 1").fetchone()
        if row:
            bid = row["id"]
            r = client.put(f"/templates/{bid}/plan", json={"title": "x", "scenes": []}, headers=auth_headers())
            assert r.status_code == 403
    finally:
        conn.close()
