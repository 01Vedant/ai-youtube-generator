import json
import uuid
from datetime import datetime

from app.db import enqueue_job, get_conn, get_job_row, init_db
from backend.routes import render as render_module


def test_cancel_endpoint_marks_job_canceled(client):
    init_db()

    app = client.app
    app.dependency_overrides[render_module.get_current_user] = lambda: {"id": "test-user"}

    try:
        job_id = str(uuid.uuid4())
        user_id = "test-user"

        payload = {
            "job_id": job_id,
            "topic": "t",
            "scenes": [{"image_prompt": "a", "narration": "b", "duration_sec": 1.0}],
        }

        # create durable queue row
        enqueue_job(job_id, user_id, json.dumps(payload))

        # create jobs_index row so ownership checks pass
        conn = get_conn()
        try:
            now = datetime.utcnow().isoformat()
            conn.execute(
                """
                INSERT OR REPLACE INTO jobs_index
                (id, user_id, project_id, title, created_at, input_json, parent_job_id)
                VALUES (?,?,?,?,?,?,?)
                """,
                (job_id, user_id, None, "t", now, json.dumps(payload), None),
            )
            conn.commit()
        finally:
            conn.close()

        # cancel is idempotent
        r1 = client.post(f"/render/{job_id}/cancel")
        assert r1.status_code == 200

        r2 = client.post(f"/render/{job_id}/cancel")
        assert r2.status_code == 200

        row = get_job_row(job_id)
        assert row is not None
        assert row["status"] in ("canceled", "cancelled")
    finally:
        app.dependency_overrides.pop(render_module.get_current_user, None)
