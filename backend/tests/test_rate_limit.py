import os
from time import time
from fastapi.testclient import TestClient

from backend.backend.main import app


def setup_module(module):
    os.environ["RL_WINDOW_SEC"] = "600"
    os.environ["RL_LOGIN_PER_IP"] = "20"
    os.environ["RL_REGISTER_PER_IP"] = "10"
    os.environ["RL_RENDER_PER_USER"] = "30"
    os.environ["RL_TTS_CALLS_PER_USER"] = "60"
    os.environ["RL_SHARE_PER_USER"] = "50"


client = TestClient(app)


def _login(email: str, password: str, ip: str = "1.2.3.4"):
    resp = client.post("/auth/login", json={"email": email, "password": password}, headers={"x-forwarded-for": ip})
    return resp


def _register(email: str, password: str, ip: str = "1.2.3.4"):
    return client.post("/auth/register", json={"email": email, "password": password}, headers={"x-forwarded-for": ip})


def _auth_headers():
    # Ensure a user exists and logged in
    email = "rl@test.local"
    password = "pass123!"
    _register(email, password)
    r = _login(email, password)
    tok = r.json().get("access_token") if r.status_code == 200 else None
    return {"Authorization": f"Bearer {tok}"} if tok else {}


def test_login_per_ip_limit_enforced():
    headers = {"x-forwarded-for": "9.9.9.9"}
    for i in range(20):
        client.post("/auth/login", json={"email": f"u{i}@x", "password": "p"}, headers=headers)
    r = client.post("/auth/login", json={"email": "overflow@x", "password": "p"}, headers=headers)
    assert r.status_code == 429
    body = r.json()
    assert body["error"]["code"] == "QUOTA_EXCEEDED"
    assert body["error"]["metric"] == "login"
    assert body["error"]["scope"] == "ip"
    assert body["error"]["limit"] == 20
    assert body["error"]["used"] >= 21
    assert isinstance(body["error"]["reset_at"], str)


def test_register_per_ip_limit_enforced():
    headers = {"x-forwarded-for": "8.8.8.8"}
    for i in range(10):
        client.post("/auth/register", json={"email": f"r{i}@x", "password": "p"}, headers=headers)
    r = client.post("/auth/register", json={"email": "overflow@x", "password": "p"}, headers=headers)
    assert r.status_code == 429
    body = r.json()
    assert body["error"]["code"] == "QUOTA_EXCEEDED"
    assert body["error"]["metric"] == "register"
    assert body["error"]["scope"] == "ip"
    assert body["error"]["limit"] == 10


def test_render_per_user_limit_enforced():
    headers = _auth_headers()
    for i in range(30):
        client.post("/render", headers=headers, json={"topic": "x", "language": "hi", "scenes": [{"image_prompt": "a", "duration_sec": 3}]})
    r = client.post("/render", headers=headers, json={"topic": "x", "language": "hi", "scenes": [{"image_prompt": "a", "duration_sec": 3}]})
    assert r.status_code == 429
    body = r.json()
    assert body["error"]["metric"] == "render"
    assert body["error"]["scope"] == "user"


def test_tts_per_user_limit_enforced():
    headers = _auth_headers()
    for i in range(60):
        client.get("/tts/preview", headers=headers, params={"text": "a", "lang": "hi"})
    r = client.get("/tts/preview", headers=headers, params={"text": "a", "lang": "hi"})
    assert r.status_code == 429
    body = r.json()
    assert body["error"]["metric"] == "tts"
    assert body["error"]["scope"] == "user"


def test_share_per_user_limit_enforced():
    headers = _auth_headers()
    for i in range(50):
        client.post("/shares", headers=headers, json={"job_id": "abc"})
    r = client.post("/shares", headers=headers, json={"job_id": "abc"})
    assert r.status_code == 429
    body = r.json()
    assert body["error"]["metric"] == "share"
    assert body["error"]["scope"] == "user"
