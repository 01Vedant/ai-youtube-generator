from fastapi.testclient import TestClient
from backend.backend.main import app

client = TestClient(app)

def test_usage_today_endpoint_isolated_between_users():
    # Authenticate as user A
    headers_a = {"X-User-Id": "user-a"}
    resp_a = client.get("/usage/today", headers=headers_a)
    assert resp_a.status_code == 200
    j1 = resp_a.json()
    assert set(j1.keys()) == { 'day', 'renders', 'tts_sec', 'limit_renders', 'limit_tts_sec', 'reset_at' }
    assert isinstance(j1['day'], str) and len(j1['day']) == 10
    assert j1['reset_at'].endswith('T00:00:00Z')

    # Authenticate as user B
    headers_b = {"X-User-Id": "user-b"}
    resp_b = client.get("/usage/today", headers=headers_b)
    assert resp_b.status_code == 200
    j2 = resp_b.json()
    assert j2['renders'] == 0
    assert j2['tts_sec'] == 0
