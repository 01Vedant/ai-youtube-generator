"""
Test voice_id + language roundtrip through POST /render → GET /status
"""
import pytest
import requests
import time

API_BASE = "http://127.0.0.1:8000"


def test_voice_id_language_roundtrip():
    """POST language='hi', voice_id='hi-IN-SwaraNeural' and assert they appear in /status"""
    
    # Create render job with Hindi TTS
    payload = {
        "topic": "Test Hindi Roundtrip",
        "language": "hi",
        "voice_id": "hi-IN-SwaraNeural",
        "voice": "F",
        "scenes": [
            {
                "image_prompt": "temple at sunrise",
                "narration": "भोर की शांति",
                "duration_sec": 3
            }
        ],
        "fast_path": True,
        "proxy": True,
        "quality": "preview"
    }
    
    # Submit job
    response = requests.post(f"{API_BASE}/render", json=payload)
    assert response.status_code == 200, f"Failed to create job: {response.text}"
    
    data = response.json()
    job_id = data["job_id"]
    assert job_id, "No job_id in response"
    
    # Poll for completion (max 30 seconds)
    for _ in range(30):
        status_response = requests.get(f"{API_BASE}/render/{job_id}/status")
        assert status_response.status_code == 200, f"Failed to get status: {status_response.text}"
        
        status = status_response.json()
        state = status.get("state")
        
        if state in ("completed", "success"):
            # Verify language and voice_id are preserved
            assert status.get("language") == "hi", f"Expected language='hi', got {status.get('language')}"
            
            # Verify audio metadata exists
            audio = status.get("audio")
            assert audio is not None, "audio metadata missing from status"
            assert audio.get("lang") == "hi", f"Expected audio.lang='hi', got {audio.get('lang')}"
            
            voice_id = audio.get("voice_id")
            assert voice_id is not None, "audio.voice_id is None"
            assert "hi-IN" in voice_id, f"Expected voice_id to contain 'hi-IN', got {voice_id}"
            
            provider = audio.get("provider")
            assert provider in ["edge", "mock"], f"Expected provider 'edge' or 'mock', got {provider}"
            
            print(f"✓ Roundtrip test passed!")
            print(f"  Job ID: {job_id}")
            print(f"  Language: {status.get('language')}")
            print(f"  Audio: lang={audio['lang']}, voice_id={audio['voice_id']}, provider={audio['provider']}")
            return
        
        if state == "error":
            pytest.fail(f"Job failed: {status.get('error')}")
        
        time.sleep(1)
    
    pytest.fail("Job did not complete within 30 seconds")


if __name__ == "__main__":
    test_voice_id_language_roundtrip()
