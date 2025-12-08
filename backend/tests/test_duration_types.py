"""
Unit tests to ensure duration_sec accepts both string and numeric types
"""
import pytest
import requests
import time

API_BASE = "http://127.0.0.1:8000"


def test_render_accepts_string_duration():
    """POST /render with duration_sec as string "3" should succeed"""
    payload = {
        "topic": "duration type test - string",
        "language": "hi",
        "voice_id": "hi-IN-SwaraNeural",
        "scenes": [
            {
                "image_prompt": "test scene",
                "narration": "test narration",
                "duration_sec": "3"  # String
            }
        ]
    }
    
    response = requests.post(f"{API_BASE}/render", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    job_id = response.json()["job_id"]
    
    # Poll for completion (max 30s)
    for _ in range(15):
        time.sleep(2)
        status_response = requests.get(f"{API_BASE}/render/{job_id}/status")
        status = status_response.json()
        
        if status["state"] in ["completed", "success"]:
            # Should not have type error
            error_msg = status.get("error") or ""
            assert "unsupported operand" not in error_msg, \
                f"Type error occurred: {error_msg}"
            print(f"✓ String duration test passed: {job_id}")
            return
        
        if status["state"] == "error":
            pytest.fail(f"Job failed: {status.get('error')}")
    
    pytest.fail("Timeout waiting for job completion")


def test_render_accepts_numeric_duration():
    """POST /render with duration_sec as number 3 should succeed"""
    payload = {
        "topic": "duration type test - numeric",
        "language": "hi",
        "voice_id": "hi-IN-SwaraNeural",
        "scenes": [
            {
                "image_prompt": "test scene",
                "narration": "test narration",
                "duration_sec": 3  # Number
            }
        ]
    }
    
    response = requests.post(f"{API_BASE}/render", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    job_id = response.json()["job_id"]
    
    # Poll for completion (max 30s)
    for _ in range(15):
        time.sleep(2)
        status_response = requests.get(f"{API_BASE}/render/{job_id}/status")
        status = status_response.json()
        
        if status["state"] in ["completed", "success"]:
            # Should not have type error
            error_msg = status.get("error") or ""
            assert "unsupported operand" not in error_msg, \
                f"Type error occurred: {error_msg}"
            print(f"✓ Numeric duration test passed: {job_id}")
            return
        
        if status["state"] == "error":
            pytest.fail(f"Job failed: {status.get('error')}")
    
    pytest.fail("Timeout waiting for job completion")


def test_render_accepts_float_duration():
    """POST /render with duration_sec as float 3.5 should succeed"""
    payload = {
        "topic": "duration type test - float",
        "language": "hi",
        "voice_id": "hi-IN-SwaraNeural",
        "scenes": [
            {
                "image_prompt": "test scene",
                "narration": "test narration",
                "duration_sec": 3.5  # Float
            }
        ]
    }
    
    response = requests.post(f"{API_BASE}/render", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    job_id = response.json()["job_id"]
    
    # Poll for completion (max 30s)
    for _ in range(15):
        time.sleep(2)
        status_response = requests.get(f"{API_BASE}/render/{job_id}/status")
        status = status_response.json()
        
        if status["state"] in ["completed", "success"]:
            # Should not have type error
            error_msg = status.get("error") or ""
            assert "unsupported operand" not in error_msg, \
                f"Type error occurred: {error_msg}"
            print(f"✓ Float duration test passed: {job_id}")
            return
        
        if status["state"] == "error":
            pytest.fail(f"Job failed: {status.get('error')}")
    
    pytest.fail("Timeout waiting for job completion")
