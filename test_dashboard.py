"""
Test script for P1 Dashboard endpoints
"""
import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"

def test_dashboard_stats():
    """Test GET /dashboard/stats"""
    print("\n" + "="*70)
    print("TEST: GET /dashboard/stats")
    print("="*70)
    
    response = requests.get(f"{BASE_URL}/dashboard/stats")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Total jobs: {data.get('total_jobs')}")
        print(f"✓ Completed: {data.get('completed_jobs')}")
        print(f"✓ Failed: {data.get('failed_jobs')}")
        print(f"✓ Running: {data.get('running_jobs')}")
        print(f"✓ Success rate: {data.get('success_rate')}%")
        print(f"✓ Avg render time: {data.get('avg_render_time_sec')}s")
        print("✅ PASSED\n")
        return True
    else:
        print(f"❌ FAILED: {response.text}\n")
        return False


def test_dashboard_jobs_list():
    """Test GET /dashboard/jobs"""
    print("="*70)
    print("TEST: GET /dashboard/jobs")
    print("="*70)
    
    # Use refresh=true to rebuild index with latest jobs
    response = requests.get(f"{BASE_URL}/dashboard/jobs?page=1&page_size=10&refresh=true")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Total jobs: {data.get('total')}")
        print(f"✓ Page: {data.get('page')}")
        print(f"✓ Jobs returned: {len(data.get('jobs', []))}")
        print(f"✓ Has more: {data.get('has_more')}")
        
        # Show first job if available
        jobs = data.get('jobs', [])
        if jobs:
            job = jobs[0]
            print(f"\n  First job:")
            print(f"    ID: {job.get('job_id')}")
            print(f"    Topic: {job.get('topic')}")
            print(f"    State: {job.get('state')}")
            print(f"    Created: {job.get('created_at')}")
        
        print("✅ PASSED\n")
        return True, data
    else:
        print(f"❌ FAILED: {response.text}\n")
        return False, None


def test_dashboard_job_duplicate(job_id):
    """Test POST /dashboard/jobs/{job_id}/duplicate"""
    print("="*70)
    print(f"TEST: POST /dashboard/jobs/{job_id}/duplicate")
    print("="*70)
    
    response = requests.post(f"{BASE_URL}/dashboard/jobs/{job_id}/duplicate")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ New job ID: {data.get('new_job_id')}")
        print(f"✓ Status: {data.get('status')}")
        print(f"✓ Message: {data.get('message')}")
        print("✅ PASSED\n")
        return True, data.get('new_job_id')
    else:
        print(f"❌ FAILED: {response.text}\n")
        return False, None


def test_dashboard_job_archive(job_id):
    """Test DELETE /dashboard/jobs/{job_id}"""
    print("="*70)
    print(f"TEST: DELETE /dashboard/jobs/{job_id}")
    print("="*70)
    
    response = requests.delete(f"{BASE_URL}/dashboard/jobs/{job_id}")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Status: {data.get('status')}")
        print(f"✓ Message: {data.get('message')}")
        print("✅ PASSED\n")
        return True
    else:
        print(f"❌ FAILED: {response.text}\n")
        return False


def test_dashboard_job_restore(job_id):
    """Test POST /dashboard/jobs/{job_id}/restore"""
    print("="*70)
    print(f"TEST: POST /dashboard/jobs/{job_id}/restore")
    print("="*70)
    
    response = requests.post(f"{BASE_URL}/dashboard/jobs/{job_id}/restore")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Status: {data.get('status')}")
        print(f"✓ Message: {data.get('message')}")
        print("✅ PASSED\n")
        return True
    else:
        print(f"❌ FAILED: {response.text}\n")
        return False


def test_dashboard_filters():
    """Test filtering and search"""
    print("="*70)
    print("TEST: Dashboard filters and search")
    print("="*70)
    
    # Test state filter
    response = requests.get(f"{BASE_URL}/dashboard/jobs?state=completed")
    print(f"✓ Filter by state=completed: {response.status_code}")
    
    # Test search
    response = requests.get(f"{BASE_URL}/dashboard/jobs?search=test")
    print(f"✓ Search query: {response.status_code}")
    
    # Test refresh
    response = requests.get(f"{BASE_URL}/dashboard/jobs?refresh=true")
    print(f"✓ Refresh index: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ PASSED\n")
        return True
    else:
        print(f"❌ FAILED\n")
        return False


def main():
    print("\n" + "="*70)
    print("P1 DASHBOARD ENDPOINTS TEST")
    print("="*70 + "\n")
    
    all_passed = True
    
    # Wait for server
    print("Waiting for server to be ready...")
    for _ in range(10):
        try:
            requests.get(f"{BASE_URL}/healthz", timeout=1)
            break
        except:
            time.sleep(0.5)
    
    # Run tests
    try:
        # Test stats
        if not test_dashboard_stats():
            all_passed = False
        
        # Test job list
        success, jobs_data = test_dashboard_jobs_list()
        if not success:
            all_passed = False
        
        # If we have jobs, test duplicate and archive
        if jobs_data and jobs_data.get('jobs'):
            first_job_id = jobs_data['jobs'][0]['job_id']
            
            # Test duplicate
            success, new_job_id = test_dashboard_job_duplicate(first_job_id)
            if not success:
                all_passed = False
            
            # Test archive and restore on the FIRST job (which exists on disk)
            # instead of the newly duplicated one
            if test_dashboard_job_archive(first_job_id):
                test_dashboard_job_restore(first_job_id)
            else:
                all_passed = False
        
        # Test filters
        if not test_dashboard_filters():
            all_passed = False
        
        # Summary
        print("="*70)
        if all_passed:
            print("✅ ALL DASHBOARD TESTS PASSED")
        else:
            print("❌ SOME TESTS FAILED")
        print("="*70 + "\n")
        
        return 0 if all_passed else 1
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
