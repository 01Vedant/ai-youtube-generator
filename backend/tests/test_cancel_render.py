import json
import uuid
from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.routes.render import router as render_router
from backend.app.db import get_conn, enqueue_job, get_job_row, init_db
from backend.app.auth.security import get_current_user


def _ensure_tables() -> None:
    conn = get_conn()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS job_queue(
              id TEXT PRIMARY KEY,
              user_id TEXT,
              payload TEXT,
              status TEXT,
              created_at TEXT,
              updated_at TEXT,
              started_at TEXT,
              finished_at TEXT,
              err_code TEXT,
              err_message TEXT,
              lock_token TEXT,
              heartbeat_at TEXT
            );
            CREATE TABLE IF NOT EXISTS jobs_index(
              id TEXT PRIMARY KEY,
              user_id TEXT,
              project_id TEXT,
              title TEXT,
              created_at TEXT,
              input_json TEXT,
              parent_job_id TEXT
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


def test_cancel_render_updates_queue_and_status():
    init_db()
    _ensure_tables()
    job_id = uuid.uuid4().hex
    user_id = "user-cancel"
    payload = json.dumps({"job_id": job_id, "topic": "cancel test"})
    enqueue_job(job_id, user_id, payload)

    conn = get_conn()
    try:
        now = datetime.utcnow().isoformat()
        conn.execute(
            """
            INSERT OR REPLACE INTO jobs_index(id, user_id, project_id, title, created_at, input_json, parent_job_id)
            VALUES(?,?,?,?,?,?,?)
            """,
            (job_id, user_id, None, "cancel test", now, payload, None),
        )
        conn.commit()
    finally:
        conn.close()

    app = FastAPI()
    app.include_router(render_router)
    app.dependency_overrides[get_current_user] = lambda: {"id": user_id}

    client = TestClient(app)

    r = client.post(f"/render/{job_id}/cancel")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "cancelled"

    row = get_job_row(job_id)
    assert row is not None
    assert row["status"] == "cancelled"

    status_resp = client.get(f"/render/{job_id}/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "cancelled"
