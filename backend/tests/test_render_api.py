import os, sys, importlib
import pytest
from fastapi.testclient import TestClient

def _load_app():
    os.environ["SIMULATE_RENDER"] = "1"
    os.environ.setdefault("ARTIFACTS_ROOT", "artifacts")
    # drop any half-loaded modules to avoid stale state
    for mod in ("app.routes.render", "app.main"):
        if mod in sys.modules:
            del sys.modules[mod]
    main_mod = importlib.import_module("app.main")
    importlib.reload(main_mod)
    return main_mod.app

@pytest.mark.skipif(os.environ.get("SIMULATE_RENDER") != "1", reason="Skip heavy render tests in simulation mode")
def test_render_start():
    app = _load_app()
    client = TestClient(app)
    r = client.post("/render", json={"script": "Test script", "template_id": "basic", "duration_sec": 10})
    assert r.status_code == 200
    job_id = r.json()["job_id"]
    assert job_id

@pytest.mark.skipif(os.environ.get("SIMULATE_RENDER") != "1", reason="Skip heavy render tests in simulation mode")
def test_render_poll():
    app = _load_app()
    client = TestClient(app)
    r = client.post("/render", json={"script": "Test script", "template_id": "basic", "duration_sec": 10})
    job_id = r.json()["job_id"]
    poll = client.get(f"/render/{job_id}")
    assert poll.status_code == 200
    data = poll.json()
    assert data["status"] in ("queued", "running", "success")
    if data["status"] == "success":
        assert "artifact" in data["artifacts"]
        assert "video" in data["artifacts"]
        assert "audio" in data["artifacts"]

@pytest.mark.skipif(os.environ.get("SIMULATE_RENDER") != "1", reason="Skip heavy render tests in simulation mode")
def test_artifacts_serve():
    app = _load_app()
    client = TestClient(app)
    # Use placeholder file from stub
    r = client.get("/artifacts/placeholder_4k.png")
    assert r.status_code == 200
    r = client.get("/artifacts/does_not_exist.png")
    assert r.status_code == 404
    
    # Step 3: Poll job status until completion or timeout
    print("\n[3] Polling job status...")
    start_time = time.time()
    last_progress = 0
    
    while time.time() - start_time < TIMEOUT:
        try:
            resp = requests.get(
                f"{BASE_URL}/render/{job_id}/status",
                timeout=10
            )
            assert resp.status_code == 200, f"GET /status failed: {resp.status_code}"
            status = resp.json()
            
            current_progress = status.get("progress_pct", 0)
            current_state = status.get("state", "unknown")
            current_step = status.get("step", "unknown")
            
            # Log progress updates
            if current_progress > last_progress:
                print(f"  Progress: {current_progress:.0f}% | State: {current_state} | Step: {current_step}")
                last_progress = current_progress
            
            # Check for completion
            if current_state == "success":
                print(f"✓ Job completed successfully")
                
                # Verify final video URL exists
                final_url = status.get("final_video_url")
                assert final_url, "No final_video_url in success response"
                print(f"  Final video: {final_url}")
                break
            
            elif current_state == "error":
                error_msg = status.get("error", "Unknown error")
                print(f"✗ Job failed: {error_msg}")
                assert False, f"Job failed: {error_msg}"
            
            time.sleep(2)  # Poll every 2 seconds
        
        except Exception as e:
            print(f"✗ Status polling failed: {e}")
            assert False, f"Status polling failed: {e}"
    
    else:
        print(f"✗ Job timed out after {TIMEOUT} seconds")
        assert False, f"Job timed out after {TIMEOUT} seconds"
    
    # Step 4: Check metrics
    print("\n[4] Checking metrics...")
    try:
        resp = requests.get(f"{BASE_URL}/metrics", timeout=5)
        assert resp.status_code == 200, f"GET /metrics failed: {resp.status_code}"
        metrics = resp.json()
        print(f"  Jobs started: {metrics.get('jobs_started', 0)}")
        print(f"  Jobs completed: {metrics.get('jobs_completed', 0)}")
        print(f"  Success rate: {metrics.get('success_rate', 0):.1f}%")
        print("✓ Metrics endpoint working")
    except Exception as e:
        print(f"⚠ Metrics check failed: {e}")
    
    # Step 5: Test Prometheus export
    print("\n[5] Checking Prometheus metrics export...")
    try:
        resp = requests.get(f"{BASE_URL}/metrics/prometheus", timeout=5)
        assert resp.status_code == 200, f"GET /metrics/prometheus failed: {resp.status_code}"
        metrics_text = resp.text
        assert "bhakti_jobs_" in metrics_text, "Missing Prometheus metrics"
        print("✓ Prometheus export working")
    except Exception as e:
        print(f"⚠ Prometheus check failed: {e}")
    
    # Final summary
    print("\n" + "="*60)
    print("✓ SMOKE TEST PASSED")
    print("="*60)
    return True


if __name__ == "__main__":
    success = test_render_api()
    exit(0 if success else 1)
