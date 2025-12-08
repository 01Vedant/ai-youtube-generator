"""
Load test: 20 users/min creating tiny plans, polling status
Run with: locust -f platform/load/locustfile.py -u 100 -r 20 --run-time 10m
"""

from locust import HttpUser, task, between
import random
import json

BASE_URL = "http://localhost:8000"


class CreatorUser(HttpUser):
    wait_time = between(2, 5)

    def on_start(self):
        """Login and get access token."""
        resp = self.client.post(
            f"{BASE_URL}/api/auth/magic-link/request",
            json={"email": f"user{random.randint(1, 1000)}@example.com"}
        )
        # In real test, would verify magic link and get token
        # For now, use mock token
        self.token = "mock_token_12345"
        self.project_id = None

    @task(1)
    def create_project(self):
        """Create a new project."""
        resp = self.client.post(
            f"{BASE_URL}/api/v1/projects/create",
            json={
                "name": f"Test Project {random.randint(1, 1000)}",
                "description": "Load test project",
                "story_data": {
                    "scenes": [
                        {
                            "prompt": "Simple test image",
                            "narration": "Test narration",
                            "duration": 3,
                        }
                    ]
                }
            },
            headers={"Authorization": f"Bearer {self.token}"}
        )
        if resp.status_code == 200:
            data = resp.json()
            self.project_id = data.get("project_id")

    @task(3)
    def poll_job_status(self):
        """Poll job status (common creator action)."""
        if self.project_id:
            self.client.get(
                f"{BASE_URL}/api/v1/projects/{self.project_id}",
                headers={"Authorization": f"Bearer {self.token}"}
            )

    @task(1)
    def list_templates(self):
        """Browse templates."""
        self.client.get(f"{BASE_URL}/api/v1/templates")

    @task(1)
    def check_usage(self):
        """Check usage stats."""
        self.client.get(
            f"{BASE_URL}/api/usage",
            headers={"Authorization": f"Bearer {self.token}"}
        )
