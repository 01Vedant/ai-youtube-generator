def test_status_json():
    from fastapi.testclient import TestClient
    from backend.backend.main import app
    client = TestClient(app)
    resp = client.get("/status.json")
    assert resp.status_code == 200
    d = resp.json()
    assert 'jobs_total' in d

def test_legal_routes():
    from fastapi.testclient import TestClient
    from backend.backend.main import app
    client = TestClient(app)
    resp_terms = client.get("/legal/terms")
    resp_privacy = client.get("/legal/privacy")
    assert resp_terms.status_code == 200
    assert resp_privacy.status_code == 200
    assert 'markdown' in resp_terms.json()
    assert 'markdown' in resp_privacy.json()
