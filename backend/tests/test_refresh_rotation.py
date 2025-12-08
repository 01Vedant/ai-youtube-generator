import json
from fastapi.testclient import TestClient

from backend.backend.main import app


client = TestClient(app)


def _csrf():
    r = client.get("/auth/csrf")
    token = r.json().get("csrf_token")
    return token, r.cookies.get("csrf_token")


def test_login_sets_refresh_cookie_and_access():
    email = "rot@test.local"
    password = "p123!"
    try:
        client.post("/auth/register", json={"email": email, "password": password})
    except Exception:
        pass
    r = client.post("/api/v1/auth/login", params={"email": email, "password": password})
    assert r.status_code == 200
    data = json.loads(r.text)
    assert data.get("access_token")
    assert r.cookies.get("refresh_token")


def test_refresh_rotates_and_invalidates_old():
    email = "rot2@test.local"
    password = "p123!"
    try:
        client.post("/auth/register", json={"email": email, "password": password})
    except Exception:
        pass
    login = client.post("/api/v1/auth/login", params={"email": email, "password": password})
    old_cookie = login.cookies.get("refresh_token")
    csrf, csrf_cookie = _csrf()
    r = client.post("/auth/refresh", headers={"X-CSRF-Token": csrf}, cookies={"csrf_token": csrf_cookie})
    assert r.status_code == 200
    new_cookie = r.cookies.get("refresh_token")
    assert new_cookie and new_cookie != old_cookie
    # Second call using old cookie should fail
    r2 = client.post("/auth/refresh", headers={"X-CSRF-Token": csrf}, cookies={"csrf_token": csrf_cookie, "refresh_token": old_cookie})
    assert r2.status_code == 401
    assert r2.json().get("error", {}).get("code") == "INVALID_REFRESH"


def test_logout_revokes_and_expires_cookie():
    email = "rot3@test.local"
    password = "p123!"
    try:
        client.post("/auth/register", json={"email": email, "password": password})
    except Exception:
        pass
    login = client.post("/api/v1/auth/login", params={"email": email, "password": password})
    csrf, csrf_cookie = _csrf()
    lo = client.post("/auth/logout", headers={"X-CSRF-Token": csrf}, cookies={"csrf_token": csrf_cookie})
    assert lo.status_code == 200
    # Subsequent refresh should fail
    r = client.post("/auth/refresh", headers={"X-CSRF-Token": csrf}, cookies={"csrf_token": csrf_cookie})
    assert r.status_code == 401


def test_refresh_requires_csrf():
    email = "rot4@test.local"
    password = "p123!"
    try:
        client.post("/auth/register", json={"email": email, "password": password})
    except Exception:
        pass
    login = client.post("/api/v1/auth/login", params={"email": email, "password": password})
    r = client.post("/auth/refresh")
    assert r.status_code in (403, 401)
