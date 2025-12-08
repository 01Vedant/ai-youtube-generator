import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.backend.main import app, OUTPUT_ROOT

client = TestClient(app)


def setup_job_dir(job_id: str):
    job_dir = OUTPUT_ROOT / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    # Create dummy files
    (job_dir / 'thumb.png').write_bytes(b'PNG')
    (job_dir / 'final.mp4').write_bytes(b'MP4')
    return job_dir


def test_manifest_returns_urls(tmp_path):
    job_id = 'testjob123'
    setup_job_dir(job_id)

    res = client.get(f"/artifacts/{job_id}/manifest")
    assert res.status_code == 200
    data = res.json()
    assert data["thumbnail"] == f"/artifacts/{job_id}/thumb.png"
    assert data["video"] == f"/artifacts/{job_id}/final.mp4"
    assert data["audio"] == f"/artifacts/{job_id}/tts.wav"


def test_file_serving_and_404(tmp_path):
    job_id = 'testjob456'
    setup_job_dir(job_id)

    ok = client.get(f"/artifacts/{job_id}/final.mp4")
    assert ok.status_code == 200
    assert ok.headers.get('content-type', '').startswith('video/mp4') or ok.content == b'MP4'

    missing = client.get(f"/artifacts/{job_id}/tts.wav")
    assert missing.status_code == 404

    invalid = client.get(f"/artifacts/{job_id}/evil.txt")
    assert invalid.status_code == 404
