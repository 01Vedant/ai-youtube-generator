from __future__ import annotations
import json
import os
import time
import logging
from typing import Optional, Dict, Any

from .db import lease_next, renew_lease, requeue_stale, mark_completed, mark_failed, mark_running, get_job_row
from .settings import OUTPUT_ROOT
from .artifacts_storage.factory import get_storage

logger = logging.getLogger(__name__)
import socket
import uuid

WORKER_ID = f"{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:8]}"


def _get_orchestrator():
    simulate = int(os.getenv("SIMULATE_RENDER", "1"))
    if simulate:
        from orchestrator import Orchestrator  # type: ignore
        return Orchestrator(base_dir=OUTPUT_ROOT)
    else:
        from pipeline.real_orchestrator import RealOrchestrator  # type: ignore
        return RealOrchestrator(base_dir=OUTPUT_ROOT)


def run_job(job_id: str, plan: Dict[str, Any]) -> Dict[str, Any]:
    orch = _get_orchestrator()
    # Minimal status callback to keep orchestrator happy; worker persists status via DB only
    def _cb(step: str, progress_pct: int, meta: Optional[Dict[str, Any]] = None) -> None:
        # Could emit to activity log here if desired
        return
    return orch.run(plan, status_callback=_cb)


def process_once(sleep_when_empty: float = 0.2, heartbeat_sec: int = 10) -> bool:
    now = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    job = lease_next(now, WORKER_ID)
    if not job:
        if sleep_when_empty:
            time.sleep(sleep_when_empty)
        return False

    job_id = job["id"]
    payload = json.loads(job["payload"]) if isinstance(job["payload"], str) else job["payload"]
    try:
        mark_running(job_id)
        # Skip already-cancelled jobs
        try:
            row = get_job_row(job_id)
            if row and row.get("status") == "cancelled":
                try:
                    from app.logs.activity import log_event
                    log_event(job_id, "job_cancelled", "Skipped cancelled job")
                except Exception:
                    pass
                return True
        except Exception:
            pass
        # Activity log
        try:
            from app.logs.activity import log_event
            log_event(job_id, "job_started", "Worker started job")
        except Exception:
            pass

        # Idempotency guard
        job_dir = OUTPUT_ROOT / job_id
        final_path = job_dir / "final.mp4"
        try:
            from app.db import get_job_row
            row = get_job_row(job_id)
            if row and row.get("status") == "completed" and final_path.exists():
                try:
                    from app.logs.activity import log_event
                    log_event(job_id, "job_skipped", "Idempotency skip: already completed")
                except Exception:
                    pass
                return True
        except Exception:
            pass

        summary = run_job(job_id, payload)
        # renew lease at end
        try:
            now2 = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
            renew_lease(job_id, WORKER_ID, now2)
        except Exception:
            pass
        try:
            row_after = get_job_row(job_id)
            if row_after and row_after.get("status") == "cancelled":
                try:
                    from app.logs.activity import log_event
                    log_event(job_id, "job_cancelled", "Job marked cancelled during processing")
                except Exception:
                    pass
                return True
        except Exception:
            pass
        if summary.get("state") == "error":
            err = summary.get("error") or {}
            code = (err.get("code") if isinstance(err, dict) else "UNKNOWN") or "UNKNOWN"
            msg = (err.get("message") if isinstance(err, dict) else str(err)) or "Render failed"
            mark_failed(job_id, code, msg, WORKER_ID)
            try:
                from app.logs.activity import log_event
                log_event(job_id, "job_failed", msg, {"code": code})
            except Exception:
                pass
            return True

        mark_completed(job_id, WORKER_ID)
        # Best-effort upload of artifacts
        try:
            _upload_artifacts(job_id)
        except Exception as up_e:  # noqa: BLE001
            logger.warning("Artifact upload best-effort failed for %s: %s", job_id, up_e)
        try:
            from app.logs.activity import log_event
            log_event(job_id, "job_completed", "Worker completed job")
        except Exception:
            pass
        return True
    except Exception as e:
        msg = str(e)
        mark_failed(job_id, "EXCEPTION", msg, WORKER_ID)
        try:
            from app.logs.activity import log_event
            log_event(job_id, "job_failed", msg, {"code": "EXCEPTION"})
        except Exception:
            pass
        return True


def main_loop():
    backoff = 0.2
    # Best-effort preflight check (non-fatal)
    try:
        import subprocess, sys as _sys, os as _os
        preflight_path = _os.path.join(_os.getcwd(), "scripts", "preflight.py")
        r = subprocess.run([_sys.executable, preflight_path], capture_output=True, text=True, timeout=15)
        if r.returncode != 0:
            msg = (r.stdout or r.stderr or "").strip()
            logger.warning("Preflight failed: %s", msg)
        else:
            first = (r.stdout or "").splitlines()[:1]
            logger.info("Preflight OK: %s", first)
    except Exception as e:
        logger.warning("Preflight check error: %s", e)
    # On-start recovery: requeue stale running jobs
    try:
        now = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        requeue_stale(now)
    except Exception:
        pass
    while True:
        processed = process_once(sleep_when_empty=backoff)
        if not processed:
            backoff = min(5.0, backoff * 1.5)
        else:
            backoff = 0.2


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    main_loop()


def _upload_artifacts(job_id: str) -> None:
    storage = get_storage()
    job_dir = OUTPUT_ROOT / job_id

    # Final video candidates -> upload as final.mp4
    final_candidates = [
        job_dir / "final.mp4",
        job_dir / "final_video.mp4",
        job_dir / "output.mp4",
    ]
    final_src = next((p for p in final_candidates if p.exists()), None)
    if final_src:
        try:
            storage.put_file(f"{job_id}/final.mp4", str(final_src))
            try:
                size = final_src.stat().st_size
            except Exception:
                size = None
            from app.logs.activity import log_event
            log_event(job_id, "artifact_uploaded", "Uploaded final video", {"key": f"{job_id}/final.mp4", "size_bytes": size})
        except Exception:
            pass

    # tts.wav
    tts = job_dir / "tts.wav"
    if tts.exists():
        try:
            storage.put_file(f"{job_id}/tts.wav", str(tts))
            try:
                size = tts.stat().st_size
            except Exception:
                size = None
            from app.logs.activity import log_event
            log_event(job_id, "artifact_uploaded", "Uploaded tts.wav", {"key": f"{job_id}/tts.wav", "size_bytes": size})
        except Exception:
            pass

    # thumb.png
    thumb = job_dir / "thumb.png"
    if thumb.exists():
        try:
            storage.put_file(f"{job_id}/thumb.png", str(thumb))
            try:
                size = thumb.stat().st_size
            except Exception:
                size = None
            from app.logs.activity import log_event
            log_event(job_id, "artifact_uploaded", "Uploaded thumb.png", {"key": f"{job_id}/thumb.png", "size_bytes": size})
        except Exception:
            pass
