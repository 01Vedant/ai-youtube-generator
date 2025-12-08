"""
Direct test of Hindi TTS in orchestrator context
"""
import sys
from pathlib import Path

# Setup path
PLATFORM_ROOT = Path(__file__).resolve().parent / "platform"
sys.path.insert(0, str(PLATFORM_ROOT))

# Test plan
plan = {
    "job_id": "test-hindi-tts",
    "topic": "Test Hindi TTS",
    "language": "hi",
    "voice_id": "hi-IN-SwaraNeural",
    "voice": "F",
    "scenes": [
        {
            "image_prompt": "test",
            "narration": "भोर में मंदिर",
            "duration_sec": 3
        }
    ]
}

print(f"Testing Hindi TTS with plan: {plan}")
print(f"Language: {plan.get('language')}")
print(f"Voice ID: {plan.get('voice_id')}")

# Try import
try:
    from backend.app.tts import synthesize, get_provider_info
    print("✓ TTS import successful")
    
    provider_info = get_provider_info()
    print(f"✓ Provider info: {provider_info}")
    
    # Try synthesis
    text = plan["scenes"][0]["narration"]
    lang = plan["language"]
    voice_id = plan["voice_id"]
    
    print(f"\nSynthesizing: '{text}' (lang={lang}, voice={voice_id})")
    wav_bytes, metadata = synthesize(text=text, lang=lang, voice_id=voice_id)
    print(f"✓ Synthesis successful: {len(wav_bytes)} bytes, duration={metadata['duration_sec']:.2f}s")
    print(f"  Metadata: {metadata}")
    
except Exception as e:
    import traceback
    print(f"✗ Error: {e}")
    print(traceback.format_exc())
