"""
Locust load test for video rendering endpoints.
Supports environment configuration for flexible testing.
"""
import os
import json
import time
from locust import HttpUser, task, between, events

# Configuration from environment
HOST = os.environ.get("HOST", "http://localhost:8000")
USERS_PER_MIN = int(os.environ.get("USERS_PER_MIN", "10"))
DURATION_SEC = int(os.environ.get("DURATION_SEC", "300"))

# Minimal test plan
MINIMAL_PLAN = {
    "topic": "Load Test Video",
    "language": "en",
    "voice": "F",
    "length": 10,
    "style": "minimal",
    "fast_path": True,
    "render_mode": "PROXY",
    "target_res": "720p",
    "scenes": [
        {
            "prompt": "Simple test scene",
            "narration": "Test narration",
            "duration": 3
        }
    ]
}


class VideoRenderUser(HttpUser):
    """Simulates user creating and monitoring video renders."""
    
    wait_time = between(5, 15)
    
    @task(3)
    def check_health(self):
        """Check backend health endpoint."""
        self.client.get("/health", name="/health")
    
    @task(2)
    def check_readyz(self):
        """Check readiness endpoint."""
        self.client.get("/readyz", name="/readyz")
    
    @task(1)
    def preflight_check(self):
        """Run preflight diagnostics."""
        self.client.get("/diagnostics/preflight", name="/diagnostics/preflight")
    
    @task(1)
    def create_and_poll_render(self):
        """Create render job and poll status."""
        # Submit render
        response = self.client.post(
            "/api/render",
            json=MINIMAL_PLAN,
            name="/api/render"
        )
        
        if response.status_code != 200:
            return
        
        try:
            result = response.json()
            job_id = result.get("job_id")
            
            if not job_id:
                return
            
            # Poll status a few times (don't wait for completion in load test)
            for _ in range(3):
                time.sleep(2)
                self.client.get(
                    f"/api/status/{job_id}",
                    name="/api/status/[job_id]"
                )
        except Exception:
            pass


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Log test configuration on start."""
    print(f"\n{'='*60}")
    print(f"Load Test Configuration:")
    print(f"  HOST: {HOST}")
    print(f"  USERS_PER_MIN: {USERS_PER_MIN}")
    print(f"  DURATION_SEC: {DURATION_SEC}")
    print(f"{'='*60}\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Log test summary on stop."""
    stats = environment.stats
    print(f"\n{'='*60}")
    print(f"Load Test Summary:")
    print(f"  Total Requests: {stats.total.num_requests}")
    print(f"  Failures: {stats.total.num_failures}")
    print(f"  Avg Response Time: {stats.total.avg_response_time:.2f}ms")
    print(f"  P95 Response Time: {stats.total.get_response_time_percentile(0.95):.2f}ms")
    print(f"  P99 Response Time: {stats.total.get_response_time_percentile(0.99):.2f}ms")
    print(f"  RPS: {stats.total.total_rps:.2f}")
    print(f"{'='*60}\n")
