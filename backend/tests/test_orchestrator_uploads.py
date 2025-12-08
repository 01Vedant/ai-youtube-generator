from pathlib import Path
import uuid
import importlib.util
from types import ModuleType
from pathlib import Path as _P

from app.settings import OUTPUT_ROOT


def test_uploads_after_completion(monkeypatch):
    # Arrange: fake storage that records puts
    calls = []

    class FakeStorage:
        def put_file(self, key: str, src_path: str) -> None:
            calls.append((key, src_path))

        def get_url(self, key: str, expires_sec: int = 3600) -> str:  # pragma: no cover
            return f"https://cdn.example/{key}"

        def exists(self, key: str) -> bool:  # pragma: no cover
            return True

    # Dynamically load platform/routes/render.py to avoid import path conflicts
    backend_root = _P(__file__).resolve().parents[1]
    render_file = backend_root.parent / "routes" / "render.py"
    spec = importlib.util.spec_from_file_location("render_module", str(render_file))
    assert spec and spec.loader
    render_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(render_module)  # type: ignore[attr-defined]

    monkeypatch.setattr(render_module, "get_storage", lambda: FakeStorage())

    # Create job dir with artifacts
    job_id = uuid.uuid4().hex[:12]
    job_dir = OUTPUT_ROOT / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    # Create artifacts
    final = job_dir / "final.mp4"
    final.write_bytes(b"MP4")
    tts = job_dir / "tts.wav"
    tts.write_bytes(b"WAV")
    thumb = job_dir / "thumb.png"
    thumb.write_bytes(b"PNG")

    # Act: invoke internal uploader helper
    render_module._upload_artifacts(job_id)

    # Assert: one call per file with normalized keys
    keys = [k for (k, _) in calls]
    assert f"{job_id}/final.mp4" in keys
    assert f"{job_id}/tts.wav" in keys
    assert f"{job_id}/thumb.png" in keys
