"""
Tests for activity log endpoint
"""
import uuid
import sys
from pathlib import Path
import pytest
import requests

# Add platform root to path so we can import from backend
PLATFORM_ROOT = Path(__file__).resolve().parents[2]
if str(PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(PLATFORM_ROOT))

from backend.app.logs.activity import log_event

# Base URL for API (adjust if needed)
API_BASE = "http://127.0.0.1:8000"


def test_activity_endpoint_basic():
    """Test GET /render/{job_id}/activity returns events"""
    # Create a unique job_id
    job_id = str(uuid.uuid4())
    
    # Log several events
    log_event(job_id, "job_created", "Job created", {"topic": "Test"})
    log_event(job_id, "tts_started", "TTS started", {"voice": "Swara"})
    log_event(job_id, "tts_completed", "TTS completed", {"duration_sec": 10.5})
    
    # Call the endpoint
    response = requests.get(f"{API_BASE}/render/{job_id}/activity?limit=10")
    
    # Assert response
    assert response.status_code == 200
    data = response.json()
    
    assert "events" in data
    assert len(data["events"]) == 3
    
    # Verify newest first (tts_completed should be first)
    assert data["events"][0]["event_type"] == "tts_completed"
    assert data["events"][0]["job_id"] == job_id
    assert data["events"][0]["message"] == "TTS completed"
    assert data["events"][0]["meta"]["duration_sec"] == 10.5
    
    # Verify middle event
    assert data["events"][1]["event_type"] == "tts_started"
    
    # Verify oldest event
    assert data["events"][2]["event_type"] == "job_created"


def test_activity_endpoint_limit():
    """Test limit parameter works correctly"""
    job_id = str(uuid.uuid4())
    
    # Log many events
    for i in range(10):
        log_event(job_id, "test_event", f"Event {i}")
    
    # Request only 5 events
    response = requests.get(f"{API_BASE}/render/{job_id}/activity?limit=5")
    
    assert response.status_code == 200
    data = response.json()
    
    assert len(data["events"]) == 5


def test_activity_endpoint_no_events():
    """Test endpoint handles job with no events"""
    job_id = str(uuid.uuid4())
    
    # Don't log any events
    response = requests.get(f"{API_BASE}/render/{job_id}/activity")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "events" in data
    assert len(data["events"]) == 0


def test_activity_endpoint_metadata():
    """Test events include metadata correctly"""
    job_id = str(uuid.uuid4())
    
    log_event(
        job_id,
        "render_completed",
        "Video ready",
        meta={
            "video_path": "final_video.mp4",
            "duration_sec": 30.5,
            "resolution": "1080p"
        }
    )
    
    response = requests.get(f"{API_BASE}/render/{job_id}/activity")
    
    assert response.status_code == 200
    data = response.json()
    
    assert len(data["events"]) == 1
    event = data["events"][0]
    
    assert event["meta"]["video_path"] == "final_video.mp4"
    assert event["meta"]["duration_sec"] == 30.5
    assert event["meta"]["resolution"] == "1080p"


if __name__ == "__main__":
    # Run tests manually with: python -m pytest test_activity_endpoint.py -xvs
    pytest.main([__file__, "-xvs"])
