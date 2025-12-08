from __future__ import annotations
import os
import json
from pathlib import Path
import importlib.util
from types import ModuleType
from typing import Any

from app.db import init_db, get_conn
from fastapi import HTTPException
import sys

# Install lightweight stubs for heavy optional modules before importing routes
# Stub app.main to provide OUTPUT_ROOT without pulling full app bootstrap
if 'app.main' not in sys.modules:
    main_stub = ModuleType('app.main')
    setattr(main_stub, 'OUTPUT_ROOT', Path(__file__).resolve().parents[1] / 'data' / 'artifacts')
    sys.modules['app.main'] = main_stub

# Stub S3 module to avoid boto3 import during artifacts imports
if 'app.artifacts_storage.s3' not in sys.modules:
    s3_stub = ModuleType('app.artifacts_storage.s3')
    class _S3StubClass:  # minimal placeholder referenced by artifacts
        pass
    setattr(s3_stub, 'S3Storage', _S3StubClass)
    sys.modules['app.artifacts_storage.s3'] = s3_stub

# Import routes directly by file path style (consistent with other tests)
_EXPORTS_PATH = Path(__file__).resolve().parents[1] / 'routes' / 'exports.py'
spec = importlib.util.spec_from_file_location("exports_router", str(_EXPORTS_PATH))
assert spec and spec.loader
exports_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exports_mod)  # type: ignore

ExportYouTubeReq = exports_mod.ExportYouTubeReq
export_youtube = exports_mod.export_youtube
# Ensure pydantic resolves typing in dynamically loaded module
try:
    ExportYouTubeReq.model_rebuild()
except Exception:
    pass

_ARTIFACTS_PATH = Path(__file__).resolve().parents[1] / 'routes' / 'artifacts.py'
aspec = importlib.util.spec_from_file_location("artifacts_router", str(_ARTIFACTS_PATH))
assert aspec and aspec.loader
artifacts_mod = importlib.util.module_from_spec(aspec)
aspec.loader.exec_module(artifacts_mod)  # type: ignore

get_manifest = artifacts_mod.get_manifest


def _fake_user(id: str, plan_id: str) -> dict:
    return {"id": id, "email": f"{id}@example.com", "created_at": "", "plan_id": plan_id}


def setup_users_and_job(tmpdir: Path):
    init_db()
    conn = get_conn()
    try:
        # Ensure users
        conn.execute("INSERT OR REPLACE INTO users (id, email, password_hash, created_at, plan_id) VALUES (?,?,?,?,?)",
                     ("u_free", "free@example.com", "x", "", "free"))
        conn.execute("INSERT OR REPLACE INTO users (id, email, password_hash, created_at, plan_id) VALUES (?,?,?,?,?)",
                     ("u_pro", "pro@example.com", "x", "", "pro"))
        # Create job and final.mp4
        job_id = "job1"
        (tmpdir / job_id).mkdir(parents=True, exist_ok=True)
        (tmpdir / job_id / "final.mp4").write_bytes(b"00")
        # Link job to free user
        conn.execute("INSERT OR REPLACE INTO jobs_index (id, user_id, project_id, title, created_at) VALUES (?,?,?,?,?)",
                     (job_id, "u_free", None, "Test", ""))
        conn.commit()
    finally:
        conn.close()
    return "job1"


def test_quotas_and_export_gate(tmp_path: Path, monkeypatch):
    job_id = setup_users_and_job(tmp_path)
    # Point OUTPUT_ROOT to tmp path for video existence check
    monkeypatch.setattr(exports_mod, 'OUTPUT_ROOT', tmp_path)

    # Monkeypatch create_export to avoid side effects
    def _fake_create_export(job_id: str, payload: Any) -> dict:
        return {"export_id": "e1", "status": "queued", "youtube_url": None}
    monkeypatch.setattr(exports_mod, 'create_export', _fake_create_export)

    # Free user blocked
    class _Req:
        def __init__(self, job_id: str, title: str):
            self.job_id = job_id
            self.title = title
            self.description = ""
            self.tags = []
            self.visibility = "unlisted"

        def dict(self) -> dict:
            return {
                "job_id": self.job_id,
                "title": self.title,
                "description": self.description,
                "tags": self.tags,
                "visibility": self.visibility,
            }

    req = _Req(job_id=job_id, title="t")
    from fastapi import HTTPException
    try:
        export_youtube(req, user=_fake_user("u_free", "free"))
        assert False, "free should be blocked"
    except HTTPException as e:
        assert e.status_code == 402

    # Pro user allowed (transfer ownership to pro)
    conn = get_conn()
    try:
        conn.execute("UPDATE jobs_index SET user_id = ? WHERE id = ?", ("u_pro", job_id))
        conn.commit()
    finally:
        conn.close()
    resp = export_youtube(req, user=_fake_user("u_pro", "pro"))
    assert resp["status"] in ("queued", "completed")


def test_artifacts_manifest_gate_for_s3(monkeypatch):
    init_db()
    # Fake S3 storage class and instance
    class S3Stub:
        def get_url(self, key: str) -> str:
            return f"https://example.com/{key}"
    # Patch artifacts to treat S3Stub as S3Storage and provide storage instance
    monkeypatch.setattr(artifacts_mod, 'S3Storage', S3Stub)
    monkeypatch.setattr(artifacts_mod, 'get_storage', lambda: S3Stub())

    # Ensure users and a job exist so owner check passes
    conn = get_conn()
    try:
        conn.execute("INSERT OR REPLACE INTO users (id, email, password_hash, created_at, plan_id) VALUES (?,?,?,?,?)",
                     ("u_free", "free@example.com", "x", "", "free"))
        conn.execute("INSERT OR REPLACE INTO users (id, email, password_hash, created_at, plan_id) VALUES (?,?,?,?,?)",
                     ("u_pro", "pro@example.com", "x", "", "pro"))
        conn.execute("INSERT OR REPLACE INTO jobs_index (id, user_id, project_id, title, created_at) VALUES (?,?,?,?,?)",
                     ("jobX", "u_free", None, "Test", ""))
        conn.commit()
    finally:
        conn.close()

    # Free user should be blocked for S3 URLs
    try:
        get_manifest("jobX", user=_fake_user("u_free", "free"))
        assert False, "free should be blocked for s3_urls"
    except HTTPException as e:
        assert e.status_code == 402

    # Pro user allowed (transfer ownership to pro)
    conn = get_conn()
    try:
        conn.execute("UPDATE jobs_index SET user_id = ? WHERE id = ?", ("u_pro", "jobX"))
        conn.commit()
    finally:
        conn.close()
    m = get_manifest("jobX", user=_fake_user("u_pro", "pro"))
    assert "video" in m and m["video"].startswith("https://")
