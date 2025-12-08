from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_public_404_for_unknown():
    resp = client.get("/s/nope")
    assert resp.status_code == 404

# Note: The rest of the test logic for create/revoke shares should be implemented via API endpoints if available.
