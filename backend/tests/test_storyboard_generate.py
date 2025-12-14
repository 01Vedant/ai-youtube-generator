from typing import Any, Dict


def test_storyboard_generate_endpoint(client):
    payload = {"topic": "Morning meditation", "voice": "F"}

    resp = client.post("/storyboard/generate", json=payload)
    assert resp.status_code == 200

    data: Dict[str, Any] = resp.json()
    assert data.get("topic") == payload["topic"]
    scenes = data.get("scenes") or []
    assert len(scenes) >= 4
    for scene in scenes:
        assert "image_prompt" in scene
        assert "narration" in scene
        assert "duration_sec" in scene
        assert isinstance(scene["duration_sec"], (int, float))
