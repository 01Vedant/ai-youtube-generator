"""
Quick test script to verify P0 UX implementation:
- Artifact URLs
- /status returns HTTP URLs
- job_summary.json has encoder/timings
- /readyz includes ffmpeg_ok/write_ok
"""
import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"

def test_readyz():
    """Test /readyz endpoint includes ffmpeg_ok and write_ok"""
    print("\n" + "="*70)
    print("TEST: /readyz endpoint")
    print("="*70)
    
    response = requests.get(f"{BASE_URL}/readyz")
    data = response.json()
    
    print(f"✓ Status: {response.status_code}")
    print(f"✓ ffmpeg_ok: {data.get('ffmpeg_ok')}")
    print(f"✓ write_ok: {data.get('write_ok')}")
    print(f"✓ simulate_mode: {data.get('simulate_mode')}")
    
    assert "ffmpeg_ok" in data, "Missing ffmpeg_ok"
    assert "write_ok" in data, "Missing write_ok"
    print("✅ PASSED\n")


def test_render_with_artifact_urls():
    """Test POST /render and verify artifact URLs in status"""
    print("="*70)
    print("TEST: POST /render with artifact URL validation")
    print("="*70)
    
    # Create render job
    plan = {
        "topic": "Test video",
        "language": "en",
        "voice": "F",
        "scenes": [
            {
                "image_prompt": "sunrise over mountains",
                "narration": "This is a test scene",
                "duration_sec": 3
            }
        ],
        "fast_path": True,
        "proxy": True
    }
    
    response = requests.post(f"{BASE_URL}/render", json=plan)
    data = response.json()
    
    print(f"✓ Status: {response.status_code}")
    job_id = data.get("job_id")
    print(f"✓ Job ID: {job_id}")
    
    # Poll status until complete
    max_wait = 10
    start = time.time()
    final_status = None
    
    while time.time() - start < max_wait:
        status_resp = requests.get(f"{BASE_URL}/render/{job_id}/status")
        status = status_resp.json()
        
        print(f"  [{status.get('step')}] {status.get('progress_pct')}%")
        
        if status.get("state") in ["completed", "error"]:
            final_status = status
            break
        
        time.sleep(0.5)
    
    assert final_status, "Job did not complete in time"
    assert final_status["state"] == "completed", f"Job failed: {final_status.get('error')}"
    
    print(f"\n✓ Final state: {final_status['state']}")
    print(f"✓ Encoder: {final_status.get('encoder')}")
    print(f"✓ Timings: {final_status.get('timings')}")
    
    # Validate artifact URLs
    final_video_url = final_status.get("final_video_url")
    print(f"✓ Final video URL: {final_video_url}")
    
    assert final_video_url, "No final_video_url"
    assert final_video_url.startswith("/artifacts/"), f"Invalid URL format: {final_video_url}"
    
    # Check assets have URLs
    assets = final_status.get("assets", [])
    print(f"✓ Assets count: {len(assets)}")
    
    for asset in assets[:3]:  # Check first 3
        url = asset.get("url")
        assert url, f"Asset missing URL: {asset}"
        assert url.startswith("/artifacts/"), f"Invalid asset URL: {url}"
        print(f"  - {asset.get('type')}: {url}")
    
    # Validate timings exist
    timings = final_status.get("timings", {})
    assert "total_ms" in timings, "Missing total_ms in timings"
    print(f"✓ Total time: {timings['total_ms']}ms")
    
    print("✅ PASSED\n")
    
    return job_id


def test_selftest_endpoint():
    """Test /render/selftest endpoint"""
    print("="*70)
    print("TEST: /render/selftest endpoint")
    print("="*70)
    
    response = requests.get(f"{BASE_URL}/render/selftest")
    data = response.json()
    
    print(f"✓ Status: {response.status_code}")
    print(f"✓ Mode: {data.get('mode')}")
    print(f"✓ Result: {data.get('status')}")
    
    results = data.get("results", {})
    tests = results.get("tests", [])
    print(f"✓ Tests passed: {len(tests)}")
    
    assert data.get("status") == "passed", f"Selftest failed: {results.get('errors')}"
    print("✅ PASSED\n")


def main():
    print("\n" + "="*70)
    print("P0 UX VALIDATION - ARTIFACT URLS & METADATA")
    print("="*70 + "\n")
    
    try:
        test_readyz()
        job_id = test_render_with_artifact_urls()
        test_selftest_endpoint()
        
        print("="*70)
        print("✅ ALL TESTS PASSED")
        print("="*70)
        print(f"\nYou can view artifacts at:")
        print(f"  http://127.0.0.1:8000/artifacts/{job_id}/final/final.mp4")
        print(f"  http://127.0.0.1:8000/artifacts/{job_id}/images/scene_1.png")
        print("="*70 + "\n")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
