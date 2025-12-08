import os
import uuid
from datetime import datetime, timedelta
from app.db import init_db, get_conn, enqueue_job, lease_next, renew_lease, requeue_stale, mark_completed, mark_failed, get_job_row
from app.worker import process_once, WORKER_ID
from app.settings import OUTPUT_ROOT


def _now_iso():
    return datetime.utcnow().isoformat() + "Z"


def setup_module(module):
    init_db()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)


def test_stale_requeue():
    job_id = uuid.uuid4().hex
    enqueue_job(job_id, "u1", "{}")
    conn = get_conn()
    now = _now_iso()
    past = (datetime.utcnow() - timedelta(seconds=1200)).isoformat() + "Z"
    try:
        conn.execute("UPDATE job_queue SET status='running', started_at=?, lock_token=?, heartbeat_at=? WHERE id=?", (now, "wX", past, job_id))
        conn.commit()
    finally:
        conn.close()
    count = requeue_stale(_now_iso(), stale_sec=600)
    assert count >= 1
    row = get_job_row(job_id)
    assert row["status"] == "queued"
    assert row["lock_token"] is None


def test_lease_exclusivity():
    job1 = uuid.uuid4().hex
    job2 = uuid.uuid4().hex
    enqueue_job(job1, "u1", "{}")
    enqueue_job(job2, "u1", "{}")
    j1 = lease_next(_now_iso(), WORKER_ID)
    assert j1 and j1["id"] == job1
    j2 = lease_next(_now_iso(), WORKER_ID)
    assert j2 and j2["id"] == job2


def test_heartbeat_renew():
    job_id = uuid.uuid4().hex
    enqueue_job(job_id, "u1", "{}")
    j = lease_next(_now_iso(), WORKER_ID)
    assert j
    before = get_job_row(job_id)["heartbeat_at"]
    renew_lease(job_id, WORKER_ID, _now_iso())
    after = get_job_row(job_id)["heartbeat_at"]
    assert after != before


def test_ownership_checks():
    job_id = uuid.uuid4().hex
    enqueue_job(job_id, "u1", "{}")
    j = lease_next(_now_iso(), WORKER_ID)
    assert j
    # Wrong worker should not flip state
    mark_completed(job_id, worker_id="wrong")
    row = get_job_row(job_id)
    assert row["status"] == "running"
    # Correct worker succeeds
    mark_completed(job_id, worker_id=WORKER_ID)
    row = get_job_row(job_id)
    assert row["status"] == "completed"


def test_idempotent_skip():
    job_id = uuid.uuid4().hex
    # Seed completed state and final.mp4
    job_dir = OUTPUT_ROOT / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "final.mp4").write_bytes(b"mp4")
    enqueue_job(job_id, "u1", "{}")
    # Manually mark completed so worker should skip
    conn = get_conn()
    now = _now_iso()
    try:
        conn.execute("UPDATE job_queue SET status='completed', finished_at=?, updated_at=? WHERE id=?", (now, now, job_id))
        conn.commit()
    finally:
        conn.close()
    # Lease then process; should short-circuit
    j = lease_next(_now_iso(), WORKER_ID)
    assert j
    processed = process_once(sleep_when_empty=0)
    assert processed


def test_crash_recovery_end_to_end():
    job_id = uuid.uuid4().hex
    enqueue_job(job_id, "u1", "{}")
    # Set running with stale heartbeat
    conn = get_conn()
    past = (datetime.utcnow() - timedelta(seconds=1200)).isoformat() + "Z"
    try:
        conn.execute("UPDATE job_queue SET status='running', started_at=?, lock_token=?, heartbeat_at=? WHERE id=?", (_now_iso(), "wX", past, job_id))
        conn.commit()
    finally:
        conn.close()
    # Requeue stale
    requeue_stale(_now_iso(), stale_sec=600)
    # Process once -> completes (simulated orchestrator)
    processed = process_once(sleep_when_empty=0)
    assert processed
    assert get_job_row(job_id)["status"] in ("completed", "failed")
