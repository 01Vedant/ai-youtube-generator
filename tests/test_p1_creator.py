"""
Lightweight P1 Creator Mode tests - No external dependencies required.
Tests library, duplicate, schedule, and soft delete functionality.
"""

import pytest
import json
import shutil
from pathlib import Path
from datetime import datetime, timedelta, timezone
import tempfile
import sys

# Add platform to path for imports
PLATFORM_ROOT = Path(__file__).resolve().parent / "platform"
sys.path.insert(0, str(PLATFORM_ROOT))

# Import after path setup
from fastapi.testclient import TestClient


@pytest.fixture
def temp_outputs_dir():
    """Create temporary pipeline_outputs directory."""
    temp_dir = Path(tempfile.mkdtemp())
    outputs_dir = temp_dir / "platform" / "pipeline_outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    
    yield outputs_dir
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def create_test_job(temp_outputs_dir):
    """Factory to create test jobs."""
    def _create_job(job_id: str, state: str = "success", topic: str = "Test Video"):
        job_dir = temp_outputs_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        
        job_summary = {
            "job_id": job_id,
            "state": state,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "elapsed_sec": 45.2,
            "encoder": "ffmpeg",
            "fast_path": True,
            "resolution": "1080x1920",
            "final_video_url": f"/artifacts/{job_id}/final.mp4",
            "thumbnail_url": f"/artifacts/{job_id}/thumbnail.jpg",
            "plan": {
                "topic": topic,
                "language": "en",
                "voice": "F",
                "length": 60,
                "style": "cinematic",
                "scenes": []
            }
        }
        
        with open(job_dir / "job_summary.json", "w") as f:
            json.dump(job_summary, f, indent=2)
        
        return job_dir
    
    return _create_job


@pytest.fixture
def client(temp_outputs_dir, monkeypatch):
    """Create test client with mocked pipeline_outputs."""
    # Patch PIPELINE_OUTPUTS path
    monkeypatch.setattr("routes.library.PIPELINE_OUTPUTS", temp_outputs_dir)
    monkeypatch.setattr("routes.schedule.PIPELINE_OUTPUTS", temp_outputs_dir)
    
    # Import app after patching
    from backend.app.main import app
    return TestClient(app)


def test_library_empty(client):
    """Test GET /library with no jobs."""
    response = client.get("/library?page=1&per_page=20")
    assert response.status_code == 200
    
    data = response.json()
    assert data["entries"] == []
    assert data["total"] == 0
    assert data["page"] == 1


def test_library_list_jobs(client, create_test_job):
    """Test GET /library returns created jobs."""
    # Create test jobs
    create_test_job("job-001", "success", "Sanatan Dharma Principles")
    create_test_job("job-002", "running", "Bhagavad Gita Wisdom")
    
    response = client.get("/library?page=1&per_page=20")
    assert response.status_code == 200
    
    data = response.json()
    assert data["total"] == 2
    assert len(data["entries"]) == 2
    
    # Check structure
    entry = data["entries"][0]
    assert "job_id" in entry
    assert "state" in entry
    assert "topic" in entry
    assert "created_at" in entry


def test_library_search_by_topic(client, create_test_job):
    """Test GET /library with query filter."""
    create_test_job("job-001", "success", "Sanatan Dharma")
    create_test_job("job-002", "success", "Bhagavad Gita")
    
    response = client.get("/library?query=Sanatan")
    assert response.status_code == 200
    
    data = response.json()
    assert data["total"] == 1
    assert "Sanatan" in data["entries"][0]["topic"]


def test_library_soft_delete(client, create_test_job, temp_outputs_dir):
    """Test DELETE /library/{job_id} creates .deleted marker."""
    job_dir = create_test_job("job-to-delete", "success")
    
    # Verify job exists
    response = client.get("/library")
    assert response.json()["total"] == 1
    
    # Delete job
    response = client.delete("/library/job-to-delete")
    assert response.status_code == 200
    assert response.json()["status"] == "deleted"
    
    # Verify .deleted marker exists
    assert (job_dir / ".deleted").exists()
    
    # Verify job_summary.json still exists (soft delete)
    assert (job_dir / "job_summary.json").exists()
    
    # Verify job no longer in list
    response = client.get("/library")
    assert response.json()["total"] == 0


def test_library_duplicate(client, create_test_job):
    """Test POST /library/{job_id}/duplicate creates new job."""
    create_test_job("original-job", "success", "Original Topic")
    
    response = client.post("/library/original-job/duplicate")
    assert response.status_code == 200
    
    data = response.json()
    assert "new_job_id" in data
    assert data["status"] == "queued"
    assert data["new_job_id"] != "original-job"


def test_library_duplicate_not_found(client):
    """Test duplicate fails on non-existent job."""
    response = client.post("/library/nonexistent/duplicate")
    assert response.status_code == 404


def test_schedule_get_none(client, create_test_job):
    """Test GET /schedule/{job_id} when no schedule exists."""
    create_test_job("job-001", "success")
    
    response = client.get("/schedule/job-001")
    assert response.status_code == 200
    
    data = response.json()
    assert data["job_id"] == "job-001"
    assert data["scheduled_at"] is None


def test_schedule_set_and_get(client, create_test_job):
    """Test POST /schedule/{job_id} and GET returns it."""
    job_dir = create_test_job("job-001", "success")
    
    # Schedule for future
    future_time = datetime.now(timezone.utc) + timedelta(hours=2)
    scheduled_at = future_time.isoformat().replace("+00:00", "Z")
    
    response = client.post(
        "/schedule/job-001",
        json={"scheduled_at": scheduled_at}
    )
    assert response.status_code == 200
    assert response.json()["scheduled_at"] == scheduled_at
    
    # Verify schedule.json written
    schedule_file = job_dir / "schedule.json"
    assert schedule_file.exists()
    
    with open(schedule_file) as f:
        schedule_data = json.load(f)
    assert schedule_data["scheduled_at"] == scheduled_at
    
    # GET should return same schedule
    response = client.get("/schedule/job-001")
    assert response.status_code == 200
    assert response.json()["scheduled_at"] == scheduled_at


def test_schedule_past_time_fails(client, create_test_job):
    """Test scheduling past time is rejected."""
    create_test_job("job-001", "success")
    
    past_time = datetime.now(timezone.utc) - timedelta(hours=1)
    scheduled_at = past_time.isoformat().replace("+00:00", "Z")
    
    response = client.post(
        "/schedule/job-001",
        json={"scheduled_at": scheduled_at}
    )
    assert response.status_code == 400
    assert "future" in response.json()["detail"].lower()


def test_schedule_invalid_iso_format(client, create_test_job):
    """Test invalid ISO 8601 format is rejected."""
    create_test_job("job-001", "success")
    
    response = client.post(
        "/schedule/job-001",
        json={"scheduled_at": "not-a-datetime"}
    )
    assert response.status_code == 400


def test_schedule_delete(client, create_test_job):
    """Test DELETE /schedule/{job_id} removes schedule."""
    job_dir = create_test_job("job-001", "success")
    
    # Create schedule
    future_time = datetime.now(timezone.utc) + timedelta(hours=2)
    scheduled_at = future_time.isoformat().replace("+00:00", "Z")
    
    client.post("/schedule/job-001", json={"scheduled_at": scheduled_at})
    assert (job_dir / "schedule.json").exists()
    
    # Delete schedule
    response = client.delete("/schedule/job-001")
    assert response.status_code == 200
    assert response.json()["status"] in ["unscheduled", "canceled"]
    
    # Verify file removed
    assert not (job_dir / "schedule.json").exists()
    
    # GET should return None
    response = client.get("/schedule/job-001")
    assert response.json()["scheduled_at"] is None


def test_schedule_job_not_found(client):
    """Test schedule operations fail on non-existent job."""
    future_time = datetime.now(timezone.utc) + timedelta(hours=2)
    scheduled_at = future_time.isoformat().replace("+00:00", "Z")
    
    # POST should fail
    response = client.post("/schedule/nonexistent", json={"scheduled_at": scheduled_at})
    assert response.status_code == 404
    
    # GET should fail
    response = client.get("/schedule/nonexistent")
    assert response.status_code == 404
    
    # DELETE should fail
    response = client.delete("/schedule/nonexistent")
    assert response.status_code == 404


def test_library_pagination(client, create_test_job):
    """Test library pagination works correctly."""
    # Create 25 jobs
    for i in range(25):
        create_test_job(f"job-{i:03d}", "success", f"Video {i}")
    
    # First page
    response = client.get("/library?page=1&per_page=10")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 25
    assert len(data["entries"]) == 10
    assert data["page"] == 1
    
    # Second page
    response = client.get("/library?page=2&per_page=10")
    data = response.json()
    assert len(data["entries"]) == 10
    
    # Third page
    response = client.get("/library?page=3&per_page=10")
    data = response.json()
    assert len(data["entries"]) == 5  # Remaining


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
