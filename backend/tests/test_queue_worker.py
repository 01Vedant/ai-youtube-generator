from __future__ import annotations
import os
import json
from pathlib import Path
from typing import Any

from app.db import init_db, get_job_row, enqueue_job
from app.worker import process_once
import importlib.util
from pathlib import Path as _Path

_RENDER_PATH = _Path(__file__).resolve().parents[2] / 'routes' / 'render.py'
spec = importlib.util.spec_from_file_location("render_router", str(_RENDER_PATH))
assert spec and spec.loader
render_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render_mod)  # type: ignore

post_render = render_mod.post_render
get_render_status = render_mod.get_render_status
RenderPlan = render_mod.RenderPlan
SceneInput = render_mod.SceneInput


def _fake_user(uid: str) -> dict:
    return {"id": uid, "email": f"{uid}@example.com", "created_at": ""}


def test_enqueue_and_complete_simulator(tmp_path: Path):
    os.environ['SIMULATE_RENDER'] = '1'
    init_db()

    # Prepare plan
    plan = RenderPlan(
        topic="Queue Test",
        language="en",
        voice="F",
        scenes=[SceneInput(image_prompt="alpha", narration="bravo", duration_sec=1.0)]
    )

    # Enqueue via API (callable) with fake user
    user = _fake_user('u1')
    resp = post_render(plan, request=None, user=user)  # type: ignore
    job_id = resp["job_id"]

    # Verify queued
    row = get_job_row(job_id)
    assert row is not None
    assert row["status"] == 'queued'

    # Run worker once; should pick and complete
    processed = process_once(sleep_when_empty=0)
    assert processed is True

    row2 = get_job_row(job_id)
    assert row2 is not None
    assert row2["status"] == 'completed'

    # Status endpoint reflects completion
    status = get_render_status(job_id, user=user)  # type: ignore
    assert status["status"] == 'completed'


def test_worker_marks_failed(monkeypatch):
    os.environ['SIMULATE_RENDER'] = '1'
    init_db()

    # Create a queued job directly
    import uuid
    job_id = 'job-fail-' + uuid.uuid4().hex
    payload = {"job_id": job_id, "topic": "X", "language": "en", "scenes": []}
    enqueue_job(job_id, 'u2', json.dumps(payload))

    # Monkeypatch worker.run_job to raise
    import app.worker as worker

    def boom(job_id: str, plan: Any) -> dict:
        raise RuntimeError("boom")

    monkeypatch.setattr(worker, 'run_job', boom)

    processed = worker.process_once(sleep_when_empty=0)
    assert processed is True
    row = get_job_row(job_id)
    assert row is not None
    assert row["status"] == 'failed'
    assert row["err_code"] == 'EXCEPTION'
