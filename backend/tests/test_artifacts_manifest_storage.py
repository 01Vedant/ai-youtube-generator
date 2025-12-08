import uuid

from app.db import get_conn
import routes.artifacts as artifacts_module


def seed_job_for_user(user_id: str) -> str:
    job_id = uuid.uuid4().hex[:12]
    conn = get_conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO jobs_index (id, user_id, project_id, title, created_at) VALUES (?,?,?,?, datetime('now'))",
            (job_id, user_id, None, job_id),
        )
        conn.commit()
    finally:
        conn.close()
    return job_id


def test_manifest_uses_storage_urls(monkeypatch):
    # fake storage returning presigned-like URLs
    class FakeStorage:
        def get_url(self, key: str, expires_sec: int = 3600) -> str:  # noqa: ARG002
            return f"https://cdn.example/{key}"

        def exists(self, key: str) -> bool:  # noqa: ARG002
            return True

        def put_file(self, key: str, src_path: str) -> None:  # noqa: ARG002
            pass

    # Patch the symbol imported in routes.artifacts
    monkeypatch.setattr(artifacts_module, "get_storage", lambda: FakeStorage())

    user = {"id": "user-123"}
    job_id = seed_job_for_user(user["id"])

    data = artifacts_module.get_manifest(job_id, user=user)
    assert data["video"].startswith("https://cdn.example/")
    assert data["thumbnail"].endswith("thumb.png")
    assert data["audio"].endswith("tts.wav")
