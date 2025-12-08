import pytest
import re
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.fixture(scope="module")
def share_payload():
    return {"artifact_url": "https://example.com/test.mp4", "title": "Test Title", "description": "Test Desc"}

def test_create_and_fetch_share(share_payload):
    # Simulate auth (patch get_current_user)
    app.dependency_overrides = {}
    from app.auth import User
    app.dependency_overrides["get_current_user"] = lambda: User(id="testuser")
    r = client.post("/shares", json=share_payload)
    assert r.status_code == 200
    data = r.json()
    assert "id" in data and "share_url" in data
    share_id = data["id"]
    # Fetch share page
    r2 = client.get(f"/s/{share_id}")
    assert r2.status_code == 200
    html = r2.text
    assert "og:title" in html and share_payload["artifact_url"] in html
    if share_payload["artifact_url"].endswith(".mp4"):
        assert "og:video" in html
    else:
        assert "og:image" in html
    # oEmbed
    r3 = client.get(f"/oembed?url=http://localhost/s/{share_id}&format=json")
    assert r3.status_code == 200
    oembed = r3.json()
    assert oembed["title"] == share_payload["title"]
    assert oembed["provider_name"] == "BhaktiGen"
    # Sitemap
    r4 = client.get("/sitemap.xml")
    assert r4.status_code == 200
    assert f"/s/{share_id}" in r4.text
    # Invalid id
    r5 = client.get("/s/invalidid")
    assert r5.status_code == 404

def test_admin_shares_csv():
    headers = {"X-Admin": "true"}
    r = client.get("/admin/shares.csv", headers=headers)
    assert r.status_code == 200
    assert "id,created_at,title,artifact_url,meta_json" in r.text
