"""
Smoke test for fast-path GPU rendering end-to-end.
Tests full pipeline with FAST_PATH=1 and verifies metadata.
"""
import os
import time
import pytest
import requests

# Set fast-path env vars for test
os.environ["FAST_PATH"] = "1"
os.environ["RENDER_MODE"] = "PROXY"
os.environ["TARGET_RES"] = "1080p"
os.environ["ENCODER"] = "h264_nvenc"  # Will fallback to libx264 if unavailable

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
POLL_INTERVAL = 2  # seconds
MAX_WAIT = 300  # 5 minutes max


def test_fastpath_render_2scene_plan():
    """POST a minimal 2-scene plan with FAST_PATH, poll until success, verify metadata."""
    
    # Minimal 2-scene plan
    plan = {
        "topic": "Sanatan Dharma Principles",
        "language": "en",
        "voice": "F",
        "length": 10,
        "style": "cinematic",
        "fast_path": True,
        "render_mode": "PROXY",
        "target_res": "1080p",
        "scenes": [
            {
                "prompt": "Ancient temple at sunrise, cinematic",
                "narration": "Sanatan Dharma teaches eternal wisdom",
                "duration": 3
            },
            {
                "prompt": "Meditation by a sacred river, serene",
                "narration": "Through meditation we find peace",
                "duration": 3
            }
        ]
    }
    
    # Submit render job
    print(f"\n[TEST] Submitting 2-scene fast-path render to {BACKEND_URL}/api/render")
    response = requests.post(f"{BACKEND_URL}/api/render", json=plan, timeout=30)
    assert response.status_code == 200, f"Render POST failed: {response.status_code} {response.text}"
    
    result = response.json()
    job_id = result.get("job_id")
    assert job_id, "No job_id in response"
    print(f"[TEST] Job created: {job_id}")
    
    # Poll for completion
    start_time = time.time()
    final_status = None
    
    while time.time() - start_time < MAX_WAIT:
        print(f"[TEST] Polling status at {time.time() - start_time:.1f}s...")
        status_response = requests.get(f"{BACKEND_URL}/api/status/{job_id}", timeout=10)
        assert status_response.status_code == 200, f"Status GET failed: {status_response.status_code}"
        
        status = status_response.json()
        state = status.get("state", "unknown")
        print(f"[TEST] State: {state}")
        
        if state == "success":
            final_status = status
            break
        elif state == "error":
            error_msg = status.get("error", "Unknown error")
            pytest.fail(f"Render failed: {error_msg}")
        elif state == "canceled":
            pytest.fail("Render was canceled unexpectedly")
        
        time.sleep(POLL_INTERVAL)
    
    assert final_status is not None, f"Render did not complete within {MAX_WAIT}s"
    
    # Verify fast-path metadata
    print(f"[TEST] Verifying fast-path metadata...")
    assert final_status.get("fast_path") is True, f"Expected fast_path=True, got {final_status.get('fast_path')}"
    
    encoder = final_status.get("encoder")
    assert encoder in ["h264_nvenc", "hevc_nvenc", "libx264"], f"Unexpected encoder: {encoder}"
    print(f"[TEST] Encoder: {encoder}")
    
    resolution = final_status.get("resolution")
    assert resolution == "1080p", f"Expected resolution=1080p, got {resolution}"
    print(f"[TEST] Resolution: {resolution}")
    
    render_mode = final_status.get("render_mode")
    assert render_mode == "PROXY", f"Expected render_mode=PROXY, got {render_mode}"
    print(f"[TEST] Render mode: {render_mode}")
    
    # Verify timings present
    timings = final_status.get("render_timings")
    assert timings is not None, "Expected render_timings in response"
    assert "scene_rendering_sec" in timings, "Missing scene_rendering_sec"
    assert "concat_sec" in timings, "Missing concat_sec"
    assert "total_sec" in timings, "Missing total_sec"
    print(f"[TEST] Render timings: {timings}")
    
    # Verify final video URL exists
    final_video_url = final_status.get("final_video_url")
    assert final_video_url, "Missing final_video_url"
    print(f"[TEST] Final video URL: {final_video_url}")
    
    print(f"[TEST] ✓ Fast-path E2E test passed in {time.time() - start_time:.1f}s")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
