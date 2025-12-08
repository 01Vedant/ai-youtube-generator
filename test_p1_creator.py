"""
Test P1 Creator Mode: Library routes and Publish routes
Validates GET /library, POST /library/{job_id}/duplicate, DELETE /library/{job_id}
and POST /publish/{job_id}/schedule, GET /publish/{job_id}
"""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import json
import shutil
from datetime import datetime, timedelta, timezone


@pytest.fixture
def setup_test_jobs():
    """Create test job summaries for library testing."""
    output_dir = Path("platform/pipeline_outputs")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create test job 1 (success)
    job1_id = "test-job-001"
    job1_dir = output_dir / job1_id
    job1_dir.mkdir(exist_ok=True)
    
    job1_summary = {
        "job_id": job1_id,
        "state": "success",
        "started_at": "2025-01-01T10:00:00Z",
        "elapsed_sec": 45.2,
        "encoder": "ffmpeg",
        "fast_path": True,
        "resolution": "1080x1920",
        "final_video_url": f"/artifacts/{job1_id}/final.mp4",
        "thumbnail_url": f"/artifacts/{job1_id}/thumbnail.jpg",
        "plan": {
            "topic": "Test Video About Sanatan Dharma",
            "language": "en",
            "voice": "F",
            "length": 60,
            "style": "cinematic",
            "scenes": []
        }
    }
    
    with open(job1_dir / "job_summary.json", "w") as f:
        json.dump(job1_summary, f)
    
    # Create test job 2 (running)
    job2_id = "test-job-002"
    job2_dir = output_dir / job2_id
    job2_dir.mkdir(exist_ok=True)
    
    job2_summary = {
        "job_id": job2_id,
        "state": "running",
        "started_at": "2025-01-01T10:05:00Z",
        "encoder": "moviepy",
        "fast_path": False,
        "plan": {
            "topic": "Another Test Video",
            "language": "hi",
            "voice": "M",
            "length": 30,
            "style": "documentary",
            "scenes": []
        }
    }
    
    with open(job2_dir / "job_summary.json", "w") as f:
        json.dump(job2_summary, f)
    
    yield {
        "job1_id": job1_id,
        "job2_id": job2_id,
        "output_dir": output_dir
    }
    
    # Cleanup
    if job1_dir.exists():
        shutil.rmtree(job1_dir)
    if job2_dir.exists():
        shutil.rmtree(job2_dir)


def test_library_list(client: TestClient, setup_test_jobs):
    """Test GET /library pagination and search."""
    # Get all jobs
    resp = client.get("/library?page=1&per_page=20")
    assert resp.status_code == 200
    
    data = resp.json()
    assert "entries" in data
    assert "total" in data
    assert "page" in data
    assert "per_page" in data
    
    # Should have at least our 2 test jobs
    assert data["total"] >= 2
    assert len(data["entries"]) >= 2
    
    # Check structure of entries
    first_entry = data["entries"][0]
    assert "job_id" in first_entry
    assert "state" in first_entry
    assert "created_at" in first_entry
    assert "topic" in first_entry
    
    # Test search by topic
    resp = client.get("/library?query=Sanatan")
    assert resp.status_code == 200
    search_data = resp.json()
    
    # Should find job 1
    found_ids = [e["job_id"] for e in search_data["entries"]]
    assert setup_test_jobs["job1_id"] in found_ids


def test_library_duplicate(client: TestClient, setup_test_jobs):
    """Test POST /library/{job_id}/duplicate."""
    job_id = setup_test_jobs["job1_id"]
    
    resp = client.post(f"/library/{job_id}/duplicate")
    assert resp.status_code == 200
    
    data = resp.json()
    assert "new_job_id" in data
    assert "status" in data
    assert data["status"] == "queued"
    assert data["new_job_id"] != job_id  # Should be different ID


def test_library_duplicate_not_found(client: TestClient):
    """Test duplicate with non-existent job."""
    resp = client.post("/library/nonexistent-job/duplicate")
    assert resp.status_code == 404


def test_library_delete(client: TestClient, setup_test_jobs):
    """Test DELETE /library/{job_id} soft delete."""
    job_id = setup_test_jobs["job2_id"]
    job_dir = setup_test_jobs["output_dir"] / job_id
    
    # Verify job exists
    assert job_dir.exists()
    assert (job_dir / "job_summary.json").exists()
    
    # Delete job
    resp = client.delete(f"/library/{job_id}")
    assert resp.status_code == 200
    
    data = resp.json()
    assert data["status"] == "deleted"
    assert data["job_id"] == job_id
    
    # Verify .deleted marker exists
    deleted_marker = job_dir / ".deleted"
    assert deleted_marker.exists()
    
    # Verify job_summary.json still exists (soft delete)
    assert (job_dir / "job_summary.json").exists()
    
    # Verify job no longer appears in library
    resp = client.get("/library?page=1&per_page=100")
    assert resp.status_code == 200
    entries = resp.json()["entries"]
    job_ids = [e["job_id"] for e in entries]
    assert job_id not in job_ids  # Should be filtered out


def test_publish_schedule(client: TestClient, setup_test_jobs):
    """Test POST /publish/{job_id}/schedule."""
    job_id = setup_test_jobs["job1_id"]
    
    # Schedule for 1 hour in the future
    future_time = datetime.now(timezone.utc) + timedelta(hours=1)
    iso_datetime = future_time.isoformat().replace("+00:00", "Z")
    
    resp = client.post(
        f"/publish/{job_id}/schedule",
        json={
            "iso_datetime": iso_datetime,
            "title": "Test Video",
            "description": "Test Description",
            "tags": ["test", "video"]
        }
    )
    assert resp.status_code == 200
    
    data = resp.json()
    assert data["job_id"] == job_id
    assert data["state"] == "scheduled"
    assert data["scheduled_at"] == iso_datetime


def test_publish_schedule_past_time(client: TestClient, setup_test_jobs):
    """Test scheduling with past datetime (should fail)."""
    job_id = setup_test_jobs["job1_id"]
    
    # Try to schedule in the past
    past_time = datetime.now(timezone.utc) - timedelta(hours=1)
    iso_datetime = past_time.isoformat().replace("+00:00", "Z")
    
    resp = client.post(
        f"/publish/{job_id}/schedule",
        json={"iso_datetime": iso_datetime}
    )
    assert resp.status_code == 400
    assert "future" in resp.json()["detail"].lower()


def test_publish_schedule_invalid_job(client: TestClient):
    """Test scheduling with non-existent job."""
    future_time = datetime.now(timezone.utc) + timedelta(hours=1)
    iso_datetime = future_time.isoformat().replace("+00:00", "Z")
    
    resp = client.post(
        "/publish/nonexistent-job/schedule",
        json={"iso_datetime": iso_datetime}
    )
    assert resp.status_code == 404


def test_publish_get_status(client: TestClient, setup_test_jobs):
    """Test GET /publish/{job_id} status."""
    job_id = setup_test_jobs["job1_id"]
    
    # First schedule a publish
    future_time = datetime.now(timezone.utc) + timedelta(hours=1)
    iso_datetime = future_time.isoformat().replace("+00:00", "Z")
    
    client.post(
        f"/publish/{job_id}/schedule",
        json={"iso_datetime": iso_datetime}
    )
    
    # Get status
    resp = client.get(f"/publish/{job_id}")
    assert resp.status_code == 200
    
    data = resp.json()
    assert data["job_id"] == job_id
    assert data["state"] == "scheduled"
    assert data["scheduled_at"] == iso_datetime


def test_publish_cancel(client: TestClient, setup_test_jobs):
    """Test DELETE /publish/{job_id}/cancel."""
    job_id = setup_test_jobs["job1_id"]
    
    # Schedule a publish
    future_time = datetime.now(timezone.utc) + timedelta(hours=1)
    iso_datetime = future_time.isoformat().replace("+00:00", "Z")
    
    client.post(
        f"/publish/{job_id}/schedule",
        json={"iso_datetime": iso_datetime}
    )
    
    # Cancel it
    resp = client.delete(f"/publish/{job_id}/cancel")
    assert resp.status_code == 200
    
    data = resp.json()
    assert data["state"] == "canceled"
    
    # Verify status is canceled
    resp = client.get(f"/publish/{job_id}")
    assert resp.status_code == 200
    assert resp.json()["state"] == "canceled"


def test_publish_providers(client: TestClient):
    """Test GET /publish/providers."""
    resp = client.get("/publish/providers")
    assert resp.status_code == 200
    
    data = resp.json()
    assert "providers" in data
    assert "youtube" in data["providers"]
    
    youtube = data["providers"]["youtube"]
    assert "configured" in youtube
    assert "enabled" in youtube
    assert "authenticated" in youtube
    assert "ready" in youtube


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
