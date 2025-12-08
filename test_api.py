"""Test script for the render API endpoint"""
import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"

def test_render_endpoint():
    """Test POST /render and GET /render/{job_id}/status"""
    
    # Step 1: Create a render job
    print("=" * 60)
    print("Step 1: Creating render job...")
    print("=" * 60)
    
    payload = {
        "topic": "test flow",
        "style": "cinematic",
        "length": 30,
        "language": "en",
        "voice": "female",
        "scenes": [
            {
                "prompt": "Beautiful temple at sunrise",
                "narration": "Welcome to this peaceful journey",
                "duration": 10.0
            },
            {
                "prompt": "Sacred rituals and prayers",
                "narration": "Experience the divine presence",
                "duration": 10.0
            },
            {
                "prompt": "Meditation and inner peace",
                "narration": "Find your spiritual path",
                "duration": 10.0
            }
        ]
    }
    
    headers = {
        "X-API-Key": "dev-creator-key",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/render",
            json=payload,
            headers=headers,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        try:
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        except:
            print(f"Raw Response: {response.text}")
        
        if response.status_code != 200:
            print(f"\n❌ Failed to create render job")
            return
            
        job_data = response.json()
        job_id = job_data.get("job_id")
        
        if not job_id:
            print("\n❌ No job_id in response")
            return
            
        print(f"\n✅ Job created: {job_id}")
        
        # Step 2: Poll status
        print("\n" + "=" * 60)
        print(f"Step 2: Polling status for job {job_id}...")
        print("=" * 60)
        
        for i in range(10):  # Poll 10 times
            time.sleep(1)
            
            status_response = requests.get(
                f"{BASE_URL}/render/{job_id}/status",
                headers=headers,
                timeout=10
            )
            
            status_data = status_response.json()
            state = status_data.get("state", "unknown")
            step = status_data.get("step", "unknown")
            progress = status_data.get("progress", 0)
            
            print(f"\nPoll #{i+1}: state={state}, step={step}, progress={progress}%")
            
            if state in ["success", "error", "completed"]:
                print(f"\n✅ Job finished with state: {state}")
                print(f"Full response: {json.dumps(status_data, indent=2)}")
                break
                
            if i == 9:
                print(f"\n⚠️  Job still running after 10 polls")
                print(f"Final status: {json.dumps(status_data, indent=2)}")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Could not connect to server. Is it running on http://127.0.0.1:8000?")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")

if __name__ == "__main__":
    test_render_endpoint()
