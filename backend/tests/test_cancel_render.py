import json
import uuid
from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.routes.render import router as render_router
from backend.app.db import init_db
from backend.app.auth.security import get_current_user


def test_cancel_render_updates_queue_and_status():
    init_db()
    app = FastAPI()
    app.include_router(render_router)
    app.dependency_overrides[get_current_user] = lambda: {"id": "test-user"}

    client = TestClient(app)

    # create job
    payload = {
        "topic": "cancel me",
        "language": "en",
        "voice": "F",
        "scenes": [
          {"image_prompt": "sunrise", "narration": "hello", "duration_sec": 1.0}
        ]
    }
    r_create = client.post("/render", json=payload)
    assert r_create.status_code == 200
    job_id = r_create.json()["job_id"]

    r_cancel = client.post(f"/render/{job_id}/cancel")
    assert r_cancel.status_code == 200
    body = r_cancel.json()
    assert body["ok"] is True
    assert body["status"] == "canceled"
    assert body["job_id"] == job_id

    status_resp = client.get(f"/render/{job_id}/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "canceled"
