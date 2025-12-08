"""
Simple manual test for P1 Creator Mode routes
Run this after backend is started: cd platform/backend && uvicorn app.main:app
"""

import requests
import json
from datetime import datetime, timedelta, timezone

BASE_URL = "http://127.0.0.1:8000"

def test_library_list():
    """Test GET /library"""
    print("\n" + "="*70)
    print("TEST: GET /library")
    print("="*70)
    
    try:
        response = requests.get(f"{BASE_URL}/library?page=1&per_page=10")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Total jobs: {data.get('total')}")
            print(f"✓ Page: {data.get('page')}")
            print(f"✓ Per page: {data.get('per_page')}")
            print(f"✓ Jobs returned: {len(data.get('entries', []))}")
            
            if data.get('entries'):
                first_job = data['entries'][0]
                print(f"✓ First job ID: {first_job.get('job_id')}")
                print(f"✓ First job topic: {first_job.get('topic')}")
                print(f"✓ First job state: {first_job.get('state')}")
            
            print("✅ PASSED\n")
            return data.get('entries', [])
        else:
            print(f"❌ FAILED: {response.text}\n")
            return []
    except Exception as e:
        print(f"❌ ERROR: {e}\n")
        return []


def test_library_search():
    """Test GET /library with search"""
    print("="*70)
    print("TEST: GET /library with query")
    print("="*70)
    
    try:
        response = requests.get(f"{BASE_URL}/library?query=test")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Search results: {len(data.get('entries', []))}")
            print("✅ PASSED\n")
        else:
            print(f"❌ FAILED: {response.text}\n")
    except Exception as e:
        print(f"❌ ERROR: {e}\n")


def test_library_duplicate(job_id: str):
    """Test POST /library/{job_id}/duplicate"""
    print("="*70)
    print(f"TEST: POST /library/{job_id}/duplicate")
    print("="*70)
    
    try:
        response = requests.post(f"{BASE_URL}/library/{job_id}/duplicate")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ New job ID: {data.get('new_job_id')}")
            print(f"✓ Status: {data.get('status')}")
            print(f"✓ Message: {data.get('message')}")
            print("✅ PASSED\n")
            return data.get('new_job_id')
        else:
            print(f"❌ FAILED: {response.text}\n")
            return None
    except Exception as e:
        print(f"❌ ERROR: {e}\n")
        return None


def test_library_delete(job_id: str):
    """Test DELETE /library/{job_id}"""
    print("="*70)
    print(f"TEST: DELETE /library/{job_id}")
    print("="*70)
    
    try:
        response = requests.delete(f"{BASE_URL}/library/{job_id}")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Status: {data.get('status')}")
            print(f"✓ Message: {data.get('message')}")
            print("✅ PASSED\n")
        else:
            print(f"❌ FAILED: {response.text}\n")
    except Exception as e:
        print(f"❌ ERROR: {e}\n")


def test_publish_schedule(job_id: str):
    """Test POST /publish/{job_id}/schedule"""
    print("="*70)
    print(f"TEST: POST /publish/{job_id}/schedule")
    print("="*70)
    
    # Schedule 1 hour in future
    future_time = datetime.now(timezone.utc) + timedelta(hours=1)
    iso_datetime = future_time.isoformat().replace("+00:00", "Z")
    
    try:
        response = requests.post(
            f"{BASE_URL}/publish/{job_id}/schedule",
            json={
                "iso_datetime": iso_datetime,
                "title": "Test Video",
                "description": "Test description",
                "tags": ["test", "demo"]
            }
        )
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Job ID: {data.get('job_id')}")
            print(f"✓ State: {data.get('state')}")
            print(f"✓ Scheduled at: {data.get('scheduled_at')}")
            print("✅ PASSED\n")
        else:
            print(f"❌ FAILED: {response.text}\n")
    except Exception as e:
        print(f"❌ ERROR: {e}\n")


def test_publish_get_status(job_id: str):
    """Test GET /publish/{job_id}"""
    print("="*70)
    print(f"TEST: GET /publish/{job_id}")
    print("="*70)
    
    try:
        response = requests.get(f"{BASE_URL}/publish/{job_id}")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Job ID: {data.get('job_id')}")
            print(f"✓ State: {data.get('state')}")
            print(f"✓ Scheduled at: {data.get('scheduled_at', 'N/A')}")
            print("✅ PASSED\n")
        else:
            print(f"❌ FAILED: {response.text}\n")
    except Exception as e:
        print(f"❌ ERROR: {e}\n")


def test_publish_cancel(job_id: str):
    """Test DELETE /publish/{job_id}/cancel"""
    print("="*70)
    print(f"TEST: DELETE /publish/{job_id}/cancel")
    print("="*70)
    
    try:
        response = requests.delete(f"{BASE_URL}/publish/{job_id}/cancel")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ State: {data.get('state')}")
            print("✅ PASSED\n")
        else:
            print(f"❌ FAILED: {response.text}\n")
    except Exception as e:
        print(f"❌ ERROR: {e}\n")


def test_publish_providers():
    """Test GET /publish/providers"""
    print("="*70)
    print("TEST: GET /publish/providers")
    print("="*70)
    
    try:
        response = requests.get(f"{BASE_URL}/publish/providers")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            youtube = data.get('providers', {}).get('youtube', {})
            print(f"✓ YouTube configured: {youtube.get('configured')}")
            print(f"✓ YouTube enabled: {youtube.get('enabled')}")
            print(f"✓ YouTube authenticated: {youtube.get('authenticated')}")
            print(f"✓ YouTube ready: {youtube.get('ready')}")
            print("✅ PASSED\n")
        else:
            print(f"❌ FAILED: {response.text}\n")
    except Exception as e:
        print(f"❌ ERROR: {e}\n")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("P1 CREATOR MODE - MANUAL INTEGRATION TESTS")
    print("="*70)
    print("NOTE: Requires backend running at http://127.0.0.1:8000")
    print("      Start it with: cd platform/backend && uvicorn app.main:app")
    print("="*70)
    
    # Test library listing
    jobs = test_library_list()
    
    # Test search
    test_library_search()
    
    # Test duplicate if we have a job
    if jobs:
        test_job_id = jobs[0]['job_id']
        print(f"\nUsing test job: {test_job_id}\n")
        
        # Test duplicate
        # new_job_id = test_library_duplicate(test_job_id)
        
        # Test publish schedule on successful job
        if jobs[0].get('state') == 'success':
            test_publish_schedule(test_job_id)
            test_publish_get_status(test_job_id)
            test_publish_cancel(test_job_id)
        
        # Test providers
        test_publish_providers()
    else:
        print("\n⚠️  No jobs found. Create a job first to test duplicate/publish features.\n")
    
    print("="*70)
    print("TESTS COMPLETE")
    print("="*70)
