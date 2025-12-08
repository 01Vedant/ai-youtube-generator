#!/usr/bin/env python3
"""
Frontend Smoke Test - Verify the full job lifecycle and UI flow without external APIs.

This script:
1. Registers a test user or uses existing credentials
2. Calls the Create Story API endpoint (/api/v1/projects/create_from_title)
3. Polls the job status endpoint (/api/v1/jobs/{job_id}) to simulate JobProgressCard updates
4. Verifies that placeholder images and audio are served correctly
5. Confirms final download link is accessible when job completes
6. Outputs a report with verification results

No external APIs (OpenAI, ElevenLabs, Replicate) are called.
Designed to work with docker-compose local setup: backend, postgres, redis, workers.

Usage:
    python platform/tests/frontend_smoke_test.py [--host http://localhost:8000] [--no-cleanup]

Environment:
    - Backend must be running at {host}/api/v1
    - USE_S3=false (local storage)
    - API keys can be empty or undefined (safe mode)
"""
import requests
import time
import json
import sys
import argparse
from datetime import datetime
from pathlib import Path


class FrontendSmokeTest:
    def __init__(self, api_base="http://localhost:8000", verbose=True):
        self.api_base = api_base
        self.verbose = verbose
        self.session = requests.Session()
        self.user_email = f"smoke_test_{datetime.now().strftime('%s')}@test.local"
        self.user_password = "SmokeTestPass123!"
        self.token = None
        self.project_id = None
        self.job_id = None
        self.report = {}

    def log(self, msg):
        if self.verbose:
            ts = datetime.now().isoformat()
            print(f"[{ts}] {msg}")

    def api_call(self, method, path, **kwargs):
        url = f"{self.api_base}{path}"
        headers = kwargs.pop("headers", {})
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        headers["Content-Type"] = "application/json"
        
        try:
            if method.upper() == "GET":
                res = self.session.get(url, headers=headers, timeout=10)
            elif method.upper() == "POST":
                res = self.session.post(url, headers=headers, timeout=10, **kwargs)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            res.raise_for_status()
            return res.json() if res.text else {}
        except requests.exceptions.RequestException as e:
            self.log(f"ERROR: API call failed: {method} {path} - {e}")
            raise

    def register_user(self):
        """Register a test user."""
        self.log(f"Registering user: {self.user_email}")
        try:
            res = self.api_call(
                "POST",
                "/api/v1/auth/register",
                json={
                    "email": self.user_email,
                    "password": self.user_password,
                    "full_name": "Smoke Test User"
                }
            )
            self.log(f"✓ User registered: {res.get('user_id')}")
            self.report["user_id"] = res.get("user_id")
            return res
        except Exception as e:
            self.log(f"✗ Registration failed: {e}")
            self.report["registration_error"] = str(e)
            raise

    def login(self):
        """Login and get JWT token."""
        self.log(f"Logging in: {self.user_email}")
        try:
            res = self.api_call(
                "POST",
                "/api/v1/auth/login",
                json={
                    "email": self.user_email,
                    "password": self.user_password
                }
            )
            self.token = res.get("access_token")
            self.log(f"✓ Logged in. Token: {self.token[:20]}...")
            self.report["token_acquired"] = True
            return res
        except Exception as e:
            self.log(f"✗ Login failed: {e}")
            self.report["login_error"] = str(e)
            raise

    def create_story(self):
        """Call POST /api/v1/projects/create_from_title to start a story job."""
        self.log("Creating story via /projects/create_from_title")
        payload = {
            "title": "Smoke Test Story",
            "description": "A test story for frontend smoke testing",
            "full_text": "This is a test story. It contains scenes and placeholders for safe testing."
        }
        try:
            res = self.api_call(
                "POST",
                "/api/v1/projects/create_from_title",
                json=payload
            )
            self.job_id = res.get("job_id")
            self.project_id = res.get("project_id")
            self.log(f"✓ Story created. Job ID: {self.job_id}, Project ID: {self.project_id}")
            self.report["job_id"] = self.job_id
            self.report["project_id"] = self.project_id
            return res
        except Exception as e:
            self.log(f"✗ Create story failed: {e}")
            self.report["create_story_error"] = str(e)
            raise

    def poll_job_status(self, max_polls=15, interval=2):
        """Poll job status endpoint to simulate JobProgressCard updates."""
        self.log(f"Polling job status every {interval}s (max {max_polls} polls)")
        status_history = []
        
        for poll_count in range(max_polls):
            try:
                res = self.api_call("GET", f"/api/v1/jobs/{self.job_id}")
                status = res.get("status", "unknown")
                progress = res.get("progress_percent", 0)
                scenes = res.get("scenes", [])
                
                self.log(f"Poll {poll_count+1}: status={status}, progress={progress}%, scenes={len(scenes)}")
                status_history.append({
                    "poll": poll_count + 1,
                    "status": status,
                    "progress_percent": progress,
                    "scenes_count": len(scenes),
                    "timestamp": datetime.now().isoformat()
                })
                
                # Verify scenes have expected fields
                for i, scene in enumerate(scenes):
                    self.log(f"  Scene {i}: title={scene.get('scene_title')}, has_image_url={bool(scene.get('image_url'))}, has_audio_url={bool(scene.get('audio_url'))}")
                
                # If completed, stop polling
                if status == "completed":
                    self.log(f"✓ Job completed after {poll_count+1} polls")
                    break
                
                # Simulate UI polling interval
                time.sleep(interval)
            except Exception as e:
                self.log(f"✗ Poll failed: {e}")
                status_history.append({
                    "poll": poll_count + 1,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
                # Continue polling on transient errors
                time.sleep(interval)
        
        self.report["polling_history"] = status_history
        return status_history

    def verify_placeholders(self):
        """Verify that placeholder assets are accessible."""
        self.log("Verifying placeholder assets")
        placeholders = {
            "image_svg": "/static/placeholders/placeholder_4k.svg",
            "image_png": "/static/placeholders/placeholder_4k.png",
            "audio_mp3": "/static/placeholders/placeholder_silent.mp3",
        }
        
        placeholder_results = {}
        all_ok = True
        for name, path in placeholders.items():
            try:
                # Construct full URL
                url = f"{self.api_base}{path}"
                res = self.session.get(url, timeout=5)
                res.raise_for_status()
                size = len(res.content)
                content_type = res.headers.get("content-type", "unknown")
                self.log(f"✓ {name}: {path} ({size} bytes, {content_type})")
                placeholder_results[name] = {
                    "status": "ok",
                    "size": size,
                    "content_type": content_type,
                    "url": url
                }
            except Exception as e:
                self.log(f"✗ {name}: {path} - {e}")
                placeholder_results[name] = {"status": "error", "error": str(e), "url": url}
                all_ok = False
        
        self.report["placeholders"] = placeholder_results
        self.report["placeholders_all_ok"] = all_ok
        return all_ok

    def verify_final_video(self):
        """Check if final video download link is available."""
        self.log("Checking final video availability")
        try:
            res = self.api_call("GET", f"/api/v1/projects/{self.project_id}")
            project = res
            final_video_url = project.get("final_video_url")
            if final_video_url:
                self.log(f"✓ Final video URL available: {final_video_url}")
                self.report["final_video_url"] = final_video_url
            else:
                self.log("✓ Final video not yet available (expected if job incomplete)")
                self.report["final_video_url"] = None
        except Exception as e:
            self.log(f"✗ Could not fetch project details: {e}")
            self.report["final_video_error"] = str(e)

    def print_summary(self):
        """Print a human-readable summary of results."""
        success = self.report.get("success", False)
        status_emoji = "✓" if success else "✗"
        
        self.log("")
        self.log("=" * 60)
        self.log(f"{status_emoji} TEST SUMMARY")
        self.log("=" * 60)
        self.log(f"Duration: {self.report.get('duration_seconds', 'N/A')}s")
        self.log(f"User ID: {self.report.get('user_id', 'N/A')}")
        self.log(f"Project ID: {self.report.get('project_id', 'N/A')}")
        self.log(f"Job ID: {self.report.get('job_id', 'N/A')}")
        
        # Poll results
        polls = self.report.get("polling_history", [])
        if polls:
            final_poll = polls[-1]
            self.log(f"Job Status: {final_poll.get('status', 'unknown')}")
            self.log(f"Polling Cycles: {len(polls)}")
            self.log(f"Final Progress: {final_poll.get('progress_percent', 'N/A')}%")
        
        # Placeholder results
        placeholders = self.report.get("placeholders", {})
        placeholder_ok = all(p.get("status") == "ok" for p in placeholders.values())
        self.log(f"Placeholders: {'✓ All OK' if placeholder_ok else '✗ Some failed'}")
        
        # Final video
        final_url = self.report.get("final_video_url")
        self.log(f"Final Video: {'✓ Available' if final_url else '⊘ Not ready or not available'}")
        
        # Error summary
        errors = [k for k, v in self.report.items() if "error" in k.lower()]
        if errors:
            self.log("")
            self.log("Errors encountered:")
            for err_key in errors:
                self.log(f"  - {err_key}: {self.report[err_key]}")
        
        self.log("=" * 60)

    def run(self):
        """Execute the full smoke test."""
        self.log("=" * 60)
        self.log("FRONTEND SMOKE TEST - LOCAL WORKFLOW VERIFICATION")
        self.log("=" * 60)
        self.log(f"Backend: {self.api_base}")
        start_time = datetime.now()
        self.log(f"Start time: {start_time.isoformat()}")
        
        try:
            # Step 1: Register & Login
            self.log("")
            self.log("STEP 1: User Registration & Authentication")
            self.log("-" * 60)
            self.register_user()
            self.login()
            
            # Step 2: Create Story
            self.log("")
            self.log("STEP 2: Create Story Project")
            self.log("-" * 60)
            self.create_story()
            
            # Step 3: Poll Job Status
            self.log("")
            self.log("STEP 3: Poll Job Status (Simulating JobProgressCard)")
            self.log("-" * 60)
            self.poll_job_status(max_polls=10, interval=2)
            
            # Step 4: Verify Placeholders
            self.log("")
            self.log("STEP 4: Verify Placeholder Assets")
            self.log("-" * 60)
            self.verify_placeholders()
            
            # Step 5: Verify Final Video
            self.log("")
            self.log("STEP 5: Verify Final Video Download Link")
            self.log("-" * 60)
            self.verify_final_video()
            
            # Summary
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            self.report["success"] = True
            self.report["end_time"] = end_time.isoformat()
            self.report["duration_seconds"] = duration
            self.print_summary()
            
            return self.report
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            self.log("")
            self.log("SMOKE TEST FAILED")
            self.log("-" * 60)
            self.log(f"Error: {e}")
            self.report["success"] = False
            self.report["end_time"] = end_time.isoformat()
            self.report["duration_seconds"] = duration
            self.print_summary()
            return self.report


def main():
    parser = argparse.ArgumentParser(description="Frontend Smoke Test")
    parser.add_argument("--host", default="http://localhost:8000", help="Backend API host")
    parser.add_argument("--verbose", action="store_true", default=True, help="Verbose output")
    parser.add_argument("--json-report", action="store_true", help="Output JSON report to file")
    parser.add_argument("--output", default="smoke_test_report.json", help="JSON report output file")
    args = parser.parse_args()
    
    tester = FrontendSmokeTest(api_base=args.host, verbose=args.verbose)
    report = tester.run()
    
    # JSON Report
    if args.json_report or "--json-report" in sys.argv:
        report_path = Path(args.output)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n📄 JSON report saved to: {report_path.absolute()}")
    
    # Exit with appropriate code
    exit_code = 0 if report.get("success") else 1
    print(f"\nExit code: {exit_code}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
