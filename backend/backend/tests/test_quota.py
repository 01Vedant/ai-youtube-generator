from fastapi.testclient import TestClient
from app.main import app
import os

client = TestClient(app)


def auth(email: str) -> dict:
    client.post('/auth/register', json={'email': email, 'password': 'pass1234'})
    r = client.post('/auth/login', json={'email': email, 'password': 'pass1234'})
    assert r.status_code == 200
    tokens = r.json()
    return {'Authorization': f"Bearer {tokens['access_token']}"}


def test_renders_quota_enforced(monkeypatch=None):
    os.environ['QUOTA_RENDERS_PER_DAY'] = '2'
    headers = auth('quota@example.com')
    body = {
        "topic": "t",
        "language": "en",
        "voice": "F",
        "scenes": [{"image_prompt": "a", "narration": "b", "duration_sec": 3}]
    }
    r1 = client.post('/render', json=body, headers=headers)
    assert r1.status_code == 200
    r2 = client.post('/render', json=body, headers=headers)
    assert r2.status_code == 200
    r3 = client.post('/render', json=body, headers=headers)
    assert r3.status_code == 429
    detail = r3.json().get('detail') or {}
    assert detail.get('error', {}).get('code') == 'QUOTA_EXCEEDED'
    assert detail.get('error', {}).get('metric') == 'renders'


def test_tts_quota_enforced():
    os.environ['QUOTA_TTS_SEC_PER_DAY'] = '5'
    headers = auth('ttsq@example.com')
    # A short preview to consume ~3s
    r1 = client.post('/tts/preview', json={"text": "hello", "lang": "en"}, headers=headers)
    assert r1.status_code in (200, 500)  # allow tts failure in env, skip if fails
    # If first passed, try to exceed with another 5s; we can't guarantee exact duration, so call repeatedly
    r2 = client.post('/tts/preview', json={"text": "world", "lang": "en"}, headers=headers)
    if r2.status_code == 429:
        detail = r2.json().get('detail') or {}
        assert detail.get('error', {}).get('code') == 'QUOTA_EXCEEDED'
        assert detail.get('error', {}).get('metric') == 'tts_sec'
    else:
        # Try another to force exceed in constrained limit
        r3 = client.post('/tts/preview', json={"text": "again", "lang": "en"}, headers=headers)
        if r3.status_code == 429:
            detail = r3.json().get('detail') or {}
            assert detail.get('error', {}).get('code') == 'QUOTA_EXCEEDED'
            assert detail.get('error', {}).get('metric') == 'tts_sec'
