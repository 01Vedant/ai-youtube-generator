import json

from backend.backend.main import app
from backend.backend.app.db import get_job_row
from backend.routes.render import get_current_user


def test_simple_render_endpoint(client):
    app.dependency_overrides[get_current_user] = lambda: {"id": "test-user"}
    try:
        resp = client.post("/render/simple", json={"topic": "Test simple mode", "voice": "F"})
        assert resp.status_code == 200
        data = resp.json()
        job_id = data.get("job_id")
        assert job_id

        row = get_job_row(job_id)
        assert row is not None
        assert row.get("status") in ("queued", "running")
        payload = json.loads(row["payload"])
        assert payload.get("scenes")
        assert len(payload["scenes"]) >= 3
    finally:
        app.dependency_overrides.pop(get_current_user, None)
