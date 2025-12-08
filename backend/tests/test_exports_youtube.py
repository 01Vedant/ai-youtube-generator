from pathlib import Path
from fastapi.testclient import TestClient
from backend.backend.main import app, OUTPUT_ROOT

client = TestClient(app)


def setup_video(job_id: str):
    job_dir = OUTPUT_ROOT / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / 'final.mp4').write_bytes(b'MP4')


def test_export_and_fetch():
    job_id = 'ytjob123'
    setup_video(job_id)

    payload = {
        'job_id': job_id,
        'title': 'Test Export',
        'description': 'Desc',
        'tags': ['devotional', 'bhakti'],
        'visibility': 'unlisted',
    }
    res = client.post('/exports/youtube', json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data['status'] == 'completed'
    assert data['export_id']
    assert data['youtube_url'].startswith('https://youtube.com/watch?v=mock-')

    # Fetch by id
    res2 = client.get(f"/exports/{data['export_id']}")
    assert res2.status_code == 200
    rec = res2.json()
    assert rec['provider'] == 'youtube'
    assert rec['status'] == 'completed'
    assert rec['youtube_url'] == data['youtube_url']
