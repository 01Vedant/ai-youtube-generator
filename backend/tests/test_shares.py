from fastapi.testclient import TestClient
from backend.backend.main import app

client = TestClient(app)


def test_create_share_ok():
    resp = client.post("/shares", json={"artifact_id": "a1", "visibility": "unlisted"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["share_id"] == "shr_a1"
    assert data["url"].endswith("/shr_a1")
