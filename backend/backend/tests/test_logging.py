import os
import json
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _parse_lines(stdout: str):
    lines = [l for l in stdout.splitlines() if l.strip()]
    out = []
    for l in lines:
        try:
            out.append(json.loads(l))
        except Exception:
            pass
    return out


def test_access_log_emitted_for_version(capfd):
    rid = "test-rid-123"
    r = client.get("/version", headers={"X-Request-ID": rid})
    # tolerate missing route; still should log access with status
    assert r.status_code in (200, 404)
    out = capfd.readouterr().out
    logs = _parse_lines(out)
    assert any(l.get("type") == "access" and l.get("request_id") == rid and l.get("method") == "GET" and l.get("path") == "/version" for l in logs)


def test_error_route_logs_uncaught_and_returns_500(capfd):
    # Create ephemeral failing route
    @app.get("/_boom")
    def boom():
        raise RuntimeError("boom")
    rid = "rid-err-1"
    r = client.get("/_boom", headers={"X-Request-ID": rid})
    assert r.status_code == 500
    body = r.json()
    assert body.get("error", {}).get("code") == "INTERNAL_ERROR"
    out = capfd.readouterr().out
    logs = _parse_lines(out)
    assert any(l.get("type") in ("error", "uncaught") and l.get("request_id") == rid for l in logs)


def test_request_id_echoed_and_user_id_present_when_authenticated(capfd):
    # Register/login a user
    email = "log@test.local"
    password = "pass123!"
    try:
        client.post("/auth/register", json={"email": email, "password": password})
    except Exception:
        pass
    tok = client.post("/auth/login", json={"email": email, "password": password}).json().get("access_token")
    headers = {"Authorization": f"Bearer {tok}", "X-Request-ID": "rid-auth-1"}
    r = client.get("/health", headers=headers)
    assert r.headers.get("X-Request-ID") == "rid-auth-1"
    out = capfd.readouterr().out
    logs = _parse_lines(out)
    # Expect an access log with our request_id and a user_id (not null)
    matches = [l for l in logs if l.get("type") == "access" and l.get("request_id") == "rid-auth-1" and l.get("path") == "/health"]
    assert matches, f"no access log with rid-auth-1 found: {logs}"
    assert any(m.get("user_id") for m in matches)
