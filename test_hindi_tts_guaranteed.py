"""
Quick test to verify Hindi TTS never returns null audio
"""
import requests
import time
import json

API_BASE = "http://127.0.0.1:8000"

def test_hindi_tts_guaranteed_metadata():
    """Verify audio metadata is ALWAYS present for Hindi language"""
    
    print("\n=== Testing Hindi TTS Guaranteed Metadata ===\n")
    
    # Create Hindi render job
    payload = {
        "topic": "Hindi TTS Metadata Test",
        "language": "hi",
        "voice_id": "hi-IN-SwaraNeural",
        "voice": "F",
        "scenes": [
            {
                "image_prompt": "temple sunrise",
                "narration": "भोर की शांति",
                "duration_sec": 3
            }
        ],
        "quality": "preview"
    }
    
    print("1. Submitting render job...")
    response = requests.post(f"{API_BASE}/render", json=payload)
    assert response.status_code == 200, f"Failed: {response.text}"
    
    data = response.json()
    job_id = data["job_id"]
    print(f"   ✓ Job created: {job_id}\n")
    
    # Poll for completion
    print("2. Polling for completion...")
    for i in range(30):
        time.sleep(1)
        status_response = requests.get(f"{API_BASE}/render/{job_id}/status")
        assert status_response.status_code == 200
        
        status = status_response.json()
        state = status.get("state")
        
        print(f"   State: {state} ({i+1}s)")
        
        if state in ("completed", "success"):
            print(f"\n3. Verifying audio metadata...")
            
            # CRITICAL: audio field must NEVER be null for language=hi
            audio = status.get("audio")
            assert audio is not None, "❌ FAIL: audio metadata is NULL!"
            print(f"   ✓ audio metadata present")
            
            # Verify required fields
            assert audio.get("lang") == "hi", f"Expected lang='hi', got {audio.get('lang')}"
            assert audio.get("voice_id") is not None, "voice_id is None"
            assert audio.get("provider") in ["edge", "mock"], f"Invalid provider: {audio.get('provider')}"
            assert "duration_ms" in audio, "duration_ms missing"
            
            print(f"   ✓ lang: {audio['lang']}")
            print(f"   ✓ voice_id: {audio['voice_id']}")
            print(f"   ✓ provider: {audio['provider']}")
            print(f"   ✓ duration_ms: {audio['duration_ms']}")
            print(f"   ✓ paced: {audio.get('paced', False)}")
            
            # Check for audio_error (expected if edge-tts fails)
            audio_error = status.get("audio_error")
            if audio_error:
                print(f"\n   ⚠️  audio_error present: {audio_error[:100]}...")
                print(f"   → This is OK - fallback metadata was correctly set")
            else:
                print(f"\n   ✓ No audio_error - TTS succeeded!")
            
            print(f"\n✅ TEST PASSED!")
            print(f"\n📋 Job ID for UI verification: {job_id}")
            print(f"   Open: http://localhost:5173/render/{job_id}")
            
            # Print full status for debugging
            print(f"\n📄 Full Status Response:")
            print(json.dumps(status, indent=2))
            
            return job_id
        
        if state == "error":
            print(f"\n❌ Job failed: {status.get('error')}")
            return None
    
    print(f"\n❌ Timeout after 30 seconds")
    return None


if __name__ == "__main__":
    job_id = test_hindi_tts_guaranteed_metadata()
    if job_id:
        print(f"\n🎉 SUCCESS! Job ID: {job_id}")
