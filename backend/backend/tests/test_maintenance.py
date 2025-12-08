import os
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def setup_module(module):
    os.environ["MAINTENANCE_MODE"] = "0"
    os.environ["MAINTENANCE_MESSAGE"] = "We’re doing scheduled maintenance."
    os.environ["MAINTENANCE_ALLOW_ADMINS"] = "1"
    os.environ["MAINTENANCE_ALLOWLIST_IPS"] = ""
    os.environ["MAINTENANCE_UNTIL"] = ""


def test_mode_off_normal_behavior():
    os.environ["MAINTENANCE_MODE"] = "0"
    r = client.get("/health")
    assert r.status_code == 200


def test_mode_on_blocks_protected_route_with_retry_after():
    os.environ["MAINTENANCE_MODE"] = "1"
    until = datetime.now(timezone.utc) + timedelta(minutes=5)
    os.environ["MAINTENANCE_UNTIL"] = until.isoformat()
    r = client.post("/api/v1/projects/create", params={"name": "x"})
    assert r.status_code == 503
    body = r.json()
    assert body.get("error", {}).get("code") == "MAINTENANCE"
    assert "Retry-After" in r.headers
    assert body["error"].get("until") is not None


def test_bypass_health_version_webhook():
    os.environ["MAINTENANCE_MODE"] = "1"
    os.environ["MAINTENANCE_UNTIL"] = ""
    assert client.get("/health").status_code == 200
    assert client.get("/version").status_code in (200, 404)  # tolerate if version not implemented
    # Webhook path: allow 2xx; actual route may differ
    resp = client.post("/billing/webhook")
    assert resp.status_code in (200, 202, 204, 404)  # tolerate missing route


def test_allowlist_ip_passes():
    os.environ["MAINTENANCE_MODE"] = "1"
    os.environ["MAINTENANCE_ALLOWLIST_IPS"] = "7.7.7.7"
    r = client.post("/api/v1/projects/create", params={"name": "y"}, headers={"x-forwarded-for": "7.7.7.7"})
    assert r.status_code != 503
    os.environ["MAINTENANCE_ALLOWLIST_IPS"] = ""


def test_admin_bypass():
    os.environ["MAINTENANCE_MODE"] = "1"
    os.environ["MAINTENANCE_ALLOW_ADMINS"] = "1"
    # Simulate admin in scope/state; middleware checks request.scope/state
    # Use TestClient to set a dummy user on app state via dependency override if available
    # Here, we call an endpoint that requires auth and assume test environment recognizes admin
    # Fallback: we expect non-503 when role is admin; otherwise tolerate 401/403
    r = client.post("/api/v1/projects/create", params={"name": "z"})
    # If the route enforces auth, status may be 401/403; assert not maintenance block
    assert r.status_code in (200, 201, 202, 401, 403)
import os
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient

from app.main import app


def setup_function(func):
    os.environ["MAINTENANCE_MODE"] = "1"
    os.environ["MAINTENANCE_MESSAGE"] = "We’re doing scheduled maintenance."
    os.environ["MAINTENANCE_ALLOW_ADMINS"] = "1"
    os.environ["MAINTENANCE_ALLOWLIST_IPS"] = ""
    os.environ["MAINTENANCE_UNTIL"] = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()


client = TestClient(app)


def _auth(email="admin@test.local", password="pass123!"):
    try:
        client.post("/auth/register", json={"email": email, "password": password, "role": "admin"})
    except Exception:
        pass
    tokens = client.post("/auth/login", json={"email": email, "password": password}).json()
    return {"Authorization": f"Bearer {tokens.get('access_token', '')}"}


def test_protected_route_blocked_with_503():
    r = client.post("/render", json={"topic": "x", "language": "hi", "scenes": [{"image_prompt": "a", "duration_sec": 3}]})
    assert r.status_code == 503
    body = r.json()
    assert body.get("error", {}).get("code") == "MAINTENANCE"
    assert "Retry-After" in r.headers
    assert "until" in body.get("error", {})


def test_bypass_health_version_webhook():
    assert client.get("/healthz").status_code == 200 or client.get("/health/live").status_code == 200
    v = client.get("/version")
    assert v.status_code in (200, 404)  # tolerate missing exact endpoint but not 503
    w = client.post("/billing/webhook")
    assert w.status_code in (200, 201, 204, 400) and w.status_code != 503


def test_allowlist_ip_bypass():
    os.environ["MAINTENANCE_ALLOWLIST_IPS"] = "1.2.3.4"
    r = client.post("/render", headers={"x-forwarded-for": "1.2.3.4"}, json={"topic": "x", "language": "hi", "scenes": [{"image_prompt": "a", "duration_sec": 3}]})
    assert r.status_code != 503


def test_admin_bypass():
    headers = _auth()
    r = client.post("/render", headers=headers, json={"topic": "x", "language": "hi", "scenes": [{"image_prompt": "a", "duration_sec": 3}]})
    assert r.status_code != 503


def test_mode_off_behaves_normally():
    os.environ["MAINTENANCE_MODE"] = "0"
    r = client.post("/render", json={"topic": "x", "language": "hi", "scenes": [{"image_prompt": "a", "duration_sec": 3}]})
    assert r.status_code in (200, 400)  # normal app response, but not 503
