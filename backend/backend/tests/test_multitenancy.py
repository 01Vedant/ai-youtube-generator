from fastapi.testclient import TestClient
from app.main import app, OUTPUT_ROOT
from app.db import get_conn
import uuid

client = TestClient(app)


def auth(email: str) -> dict:
    client.post('/auth/register', json={'email': email, 'password': 'pass1234'})
    r = client.post('/auth/login', json={'email': email, 'password': 'pass1234'})
    assert r.status_code == 200
    tokens = r.json()
    return {'Authorization': f"Bearer {tokens['access_token']}"}


def seed_job_for_user(user_id: str) -> str:
    job_id = uuid.uuid4().hex[:12]
    # create artifacts dir and a dummy files
    job_dir = OUTPUT_ROOT / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / 'thumb.png').write_bytes(b'PNG')
    (job_dir / 'final.mp4').write_bytes(b'MP4')
    (job_dir / 'tts.wav').write_bytes(b'WAV')
    # index row
    conn = get_conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO jobs_index (id, user_id, project_id, title, created_at) VALUES (?,?,?,?, datetime('now'))",
            (job_id, user_id, None, job_id),
        )
        conn.commit()
    finally:
        conn.close()
    return job_id


def test_cross_user_forbidden_everywhere():
    # users
    headers_a = auth('a.mt@example.com')
    headers_b = auth('b.mt@example.com')

    # create a project for A
    r = client.post('/projects', json={'title': 'A Project'}, headers=headers_a)
    assert r.status_code == 200
    proj_id = r.json()['id']

    # seed a job/artifacts for A
    # fetch A's user id via /auth/me
    me_a = client.get('/auth/me', headers=headers_a).json()
    job_a = seed_job_for_user(me_a['id'])

    # link job to project (owner can)
    r = client.post(f'/projects/{proj_id}/assign', json={'job_id': job_a}, headers=headers_a)
    assert r.status_code == 200

    # B cannot see A's project detail
    r = client.get(f'/projects/{proj_id}', headers=headers_b)
    assert r.status_code == 404 or r.status_code == 403

    # B cannot assign to A's project
    # prepare B job
    me_b = client.get('/auth/me', headers=headers_b).json()
    job_b = seed_job_for_user(me_b['id'])
    r = client.post(f'/projects/{proj_id}/assign', json={'job_id': job_b}, headers=headers_b)
    assert r.status_code in (403, 404)

    # Artifacts: B cannot access A's manifest or file
    r = client.get(f'/artifacts/{job_a}/manifest', headers=headers_b)
    assert r.status_code == 403
    r = client.get(f'/artifacts/{job_a}/final.mp4', headers=headers_b)
    assert r.status_code == 403

    # A can access own manifest and file
    r = client.get(f'/artifacts/{job_a}/manifest', headers=headers_a)
    assert r.status_code == 200
    r = client.get(f'/artifacts/{job_a}/final.mp4', headers=headers_a)
    assert r.status_code == 200

    # Exports: A can export, B cannot read A's export
    r = client.post('/exports/youtube', json={'job_id': job_a, 'title': 't'}, headers=headers_a)
    assert r.status_code == 200
    export_id = r.json()['export_id']
    r = client.get(f'/exports/{export_id}', headers=headers_b)
    assert r.status_code == 403
    r = client.get(f'/exports/{export_id}', headers=headers_a)
    assert r.status_code == 200
