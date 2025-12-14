"""
Render router: POST /render to enqueue, GET /render/{job_id}/status to poll.
Production-ready with simulator mode, robust error handling, and in-memory job tracking.
"""
import os
import sys
import logging
import time
import json
import uuid
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List, Annotated
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field, ValidationError, field_validator
from fastapi import Query
from backend.backend.app.settings import OUTPUT_ROOT
from backend.backend.app.artifacts_storage.factory import get_storage
from backend.backend.app.logs.activity import log_event
try:
    from backend.backend.app.auth.security import get_current_user
except Exception:
    # Fallback for test environments without auth deps
    def get_current_user():  # type: ignore
        return None
from backend.backend.app.usage.service import check_quota_or_raise, inc_renders
from backend.backend.app.db import get_conn, enqueue_job, get_job_row, mark_cancelled

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/render", tags=["render"])

# ==============================================================================
# Configuration
# ==============================================================================
SIMULATE_RENDER = int(os.getenv("SIMULATE_RENDER", "1"))

# In-memory job status cache
JOBS: Dict[str, Dict[str, Any]] = {}

# ==============================================================================
# URL Helpers
# ==============================================================================
def url_for_artifact(job_id: str, rel_path: str) -> str:
    """Build HTTP URL for artifact file.
    
    Args:
        job_id: Job UUID
        rel_path: Relative path like 'final/final.mp4' or 'images/scene_001.png'
    
    Returns:
        HTTP URL like '/artifacts/job-uuid/final/final.mp4'
    """
    # Normalize path separators for URL
    rel_path = rel_path.replace("\\", "/")
    return f"/artifacts/{job_id}/{rel_path}"

# ==============================================================================
# Pydantic Models (Simplified for robustness)
# ==============================================================================
class SceneInput(BaseModel):
    """Single scene with image prompt and narration"""
    image_prompt: str = Field(..., description="Image generation prompt", min_length=3)
    narration: str = Field(..., description="Narration text for TTS", min_length=3)
    duration_sec: Annotated[float, Field(ge=0.5, le=600)] = 3.0
    
    @field_validator("duration_sec", mode="before")
    @classmethod
    def _coerce_duration(cls, v):
        """Allow '3', '3.0', 3, 3.0 - coerce all to float"""
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            return float(v.strip())
        raise TypeError("duration_sec must be numeric")


class RenderPlan(BaseModel):
    """Video render plan with scenes and settings"""
    topic: str = Field(default="Bhakti demo", description="Video topic")
    language: str = Field(default="en", pattern="^(en|hi)$", description="Language code")
    voice: str = Field(default="F", pattern="^(F|M)$", description="Voice gender")
    voice_id: Optional[str] = Field(default=None, description="Specific TTS voice ID (e.g., hi-IN-SwaraNeural)")
    scenes: List[SceneInput] = Field(..., min_length=1, max_length=20)
    fast_path: bool = Field(default=True, description="Use fast rendering")
    proxy: bool = Field(default=True, description="Use proxy resolution")
    # Hybrid pipeline flags
    enable_parallax: bool = Field(default=True, description="Enable 2.5D parallax motion")
    enable_templates: bool = Field(default=True, description="Enable motion templates (titles, captions)")
    enable_audio_sync: bool = Field(default=True, description="Enable audio-led editing (beat sync)")
    quality: str = Field(default="final", pattern="^(preview|final)$", description="Output quality preset")

    class Config:
        json_schema_extra = {
            "example": {
                "topic": "Bhakti demo",
                "language": "en",
                "voice": "F",
                "scenes": [
                    {
                        "image_prompt": "sunrise over river",
                        "narration": "Welcome to the demo",
                        "duration_sec": 3
                    }
                ],
                "fast_path": True,
                "proxy": True
            }
        }


class SimpleRenderRequest(BaseModel):
    topic: str
    style: Optional[str] = None
    language: str = "hi"
    duration_sec: float = 60.0
    voice: str = Field(default="F", pattern="^(F|M)$")
    fast_path: bool = False
    proxy: Optional[bool] = None


class Event(BaseModel):
    """Activity log event"""
    ts_iso: str = Field(..., description="ISO 8601 timestamp")
    job_id: str = Field(..., description="Job UUID")
    event_type: str = Field(..., description="Event type (e.g., job_created, tts_started)")
    message: str = Field(..., description="Human-readable message")
    meta: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


# ==============================================================================
# Job Status Helpers
# ==============================================================================
def set_status(job_id: str, **fields):
    """Update job status in memory"""
    if job_id not in JOBS:
        JOBS[job_id] = {
            "job_id": job_id,
            "state": "pending",
            "step": "pending",
            "progress_pct": 0,
            "assets": [],
            "logs": [],
            "error": None,
            "final_video_url": None,
            "created_at": datetime.utcnow().isoformat()
        }
    JOBS[job_id].update(fields)
    return JOBS[job_id]


def get_status(job_id: str) -> Optional[Dict[str, Any]]:
    """Get job status from memory or disk"""
    # Check in-memory first
    if job_id in JOBS:
        return JOBS[job_id]
    
    # Check disk (job_summary.json)
    summary_path = OUTPUT_ROOT / job_id / "job_summary.json"
    if summary_path.exists():
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            
            # Convert relative paths to HTTP URLs
            assets = summary.get("assets", [])
            assets_with_urls = []
            for asset in assets:
                asset_copy = asset.copy()
                if "path" in asset_copy:
                    asset_copy["url"] = url_for_artifact(job_id, asset_copy["path"])
                assets_with_urls.append(asset_copy)
            
            # Build final_video_url by checking candidates in order
            final_video_url = None
            job_dir = OUTPUT_ROOT / job_id
            
            # Check standard candidates first
            candidates = ["final_video.mp4", "final.mp4", "output.mp4"]
            for candidate in candidates:
                video_path = job_dir / candidate
                if video_path.exists():
                    final_video_url = f"/artifacts/{job_id}/{candidate}"
                    break
            
            # If no standard name found, check subdirectories for .mp4 files
            if not final_video_url and job_dir.exists():
                for mp4_file in job_dir.rglob("*.mp4"):
                    if mp4_file.is_file():
                        rel_path = mp4_file.relative_to(job_dir)
                        final_video_url = f"/artifacts/{job_id}/{str(rel_path).replace(chr(92), '/')}"
                        break
            
            # Map to standard format
            return {
                "job_id": job_id,
                "state": summary.get("state", "unknown"),
                "step": summary.get("step", "unknown"),
                "progress_pct": summary.get("progress", 0),
                "assets": assets_with_urls,
                "final_video_url": final_video_url,
                "logs": summary.get("logs", []),
                "error": summary.get("error"),
                "encoder": summary.get("encoder", "unknown"),
                "resolution": summary.get("resolution", "1080p"),
                "fast_path": summary.get("fast_path", True),
                "timings": summary.get("timings", {}),
                "audio": summary.get("audio"),
                "audio_error": summary.get("audio_error"),
                "plan": summary.get("plan")
            }
        except Exception as e:
            logger.warning(f"Failed to load job_summary.json for {job_id}: {e}")
    
    return None


def append_log(job_id: str, msg: str):
    """Append log message to job"""
    if job_id in JOBS:
        log_entry = {
            "ts": datetime.utcnow().isoformat(),
            "msg": msg
        }
        JOBS[job_id]["logs"].append(log_entry)


# ==============================================================================
# Response helpers
# ==============================================================================
def _build_artifact_map(raw: Dict[str, Any]) -> Dict[str, str]:
    artifacts: Dict[str, str] = {}
    assets = raw.get("assets", []) or []
    for asset in assets:
        url = asset.get("url")
        if not url:
            continue
        label = asset.get("label") or asset.get("path") or f"asset_{len(artifacts) + 1}"
        artifacts[str(label)] = url

    final_video_url = raw.get("final_video_url")
    if isinstance(final_video_url, str) and final_video_url:
        artifacts.setdefault("final_video", final_video_url)

    return artifacts


def _format_job_status(raw: Dict[str, Any]) -> Dict[str, Any]:
    state = (raw.get("state") or "unknown").lower()

    if state in {"cancelled", "canceled"}:
        return {
            "status": "canceled",
            "error": {
                "code": "CANCELLED",
                "phase": "finalize",
                "message": "Job cancelled",
                "meta": raw.get("error") if isinstance(raw.get("error"), dict) else {},
            },
        }

    if state in {"success", "completed"}:
        response: Dict[str, Any] = {
            "status": "completed",
            "artifacts": _build_artifact_map(raw),
        }
        audio_meta = raw.get("audio")
        if isinstance(audio_meta, dict):
            response["audioMeta"] = audio_meta
        return response

    if state == "error":
        error_payload = raw.get("error")
        if isinstance(error_payload, dict):
            code = error_payload.get("code", "UNKNOWN")
            phase = error_payload.get("phase", "finalize")
            message = error_payload.get("message", "Render failed")
            meta = error_payload.get("meta") or {}
        else:
            code = "UNKNOWN"
            phase = "finalize"
            message = str(error_payload) if error_payload else "Render failed"
            meta = {}

        return {
            "status": "failed",
            "error": {
                "code": code,
                "phase": phase,
                "message": message,
                "meta": meta,
            }
        }

    progress = raw.get("progress_pct")
    payload: Dict[str, Any] = {
        "status": "queued" if state in {"pending", "queued", "waiting"} else "running"
    }
    if isinstance(progress, (int, float)):
        payload["progress"] = progress
    return payload


# ==============================================================================
# Orchestrator Integration
# ==============================================================================
def get_orchestrator():
    """Get orchestrator instance (simulator or real)"""
    if SIMULATE_RENDER:
        try:
            from orchestrator import Orchestrator
            logger.info("Using SIMULATOR orchestrator (SIMULATE_RENDER=1)")
            return Orchestrator(base_dir=OUTPUT_ROOT)
        except ImportError as e:
            logger.error(f"Failed to import simulator orchestrator: {e}")
            raise HTTPException(
                status_code=500,
                detail="Simulator orchestrator not available. Check platform/orchestrator.py exists."
            )
    else:
        try:
            from pipeline.real_orchestrator import RealOrchestrator
            logger.info("Using REAL orchestrator (SIMULATE_RENDER=0)")
            return RealOrchestrator(base_dir=OUTPUT_ROOT)
        except ImportError as e:
            logger.error(f"Failed to import real orchestrator: {e}")
            raise HTTPException(
                status_code=503,
                detail=f"Real orchestrator not available: {e}. Set SIMULATE_RENDER=1 for simulator mode."
            )


def run_simulator_job(job_id: str, plan_dict: dict):
    """Run simulator job in background thread"""
    try:
        # Status callback to update in-memory cache
        def status_callback(step: str, progress_pct: int, meta: Optional[Dict] = None):
            state = "running" if progress_pct < 100 else "completed"
            set_status(
                job_id,
                state=state,
                step=step,
                progress_pct=progress_pct
            )
            append_log(job_id, f"{step} {progress_pct}%")
        
        # Get orchestrator and run
        orch = get_orchestrator()
        set_status(job_id, state="running", step="initializing")
        append_log(job_id, "Starting simulation...")
        
        summary = orch.run(plan_dict, status_callback=status_callback)
        
        if summary.get("state") == "error":
            error_payload = summary.get("error")
            set_status(
                job_id,
                state="error",
                step="error",
                progress_pct=summary.get("progress", 0),
                error=error_payload,
            )
            message = (
                error_payload.get("message")
                if isinstance(error_payload, dict)
                else str(error_payload)
            )
            append_log(job_id, f"ERROR: {message}")
            logger.error(f"Job {job_id} failed: {message}")
            return
        
        # Convert asset paths to URLs for in-memory status
        assets = summary.get("assets", [])
        assets_with_urls = []
        for asset in assets:
            asset_copy = asset.copy()
            if "path" in asset_copy:
                asset_copy["url"] = url_for_artifact(summary.get("job_id"), asset_copy["path"])
            assets_with_urls.append(asset_copy)
        
        # Update final status
        status_updates = {
            "state": "completed",
            "step": "completed",
            "progress_pct": 100,
            "assets": assets_with_urls,
            "final_video_url": summary.get("final_video_url"),
            "encoder": summary.get("encoder", "simulator"),
            "resolution": summary.get("resolution", "1080p"),
            "fast_path": summary.get("fast_path", True),
            "timings": summary.get("timings", {})
        }
        
        # Include audio metadata if available
        if "audio" in summary:
            status_updates["audio"] = summary["audio"]
        
        # Include audio_error if TTS failed
        if "audio_error" in summary:
            status_updates["audio_error"] = summary["audio_error"]
        
        set_status(job_id, **status_updates)

        # Upload artifacts to configured storage (best-effort)
        try:
            _upload_artifacts(job_id)
        except Exception as up_e:  # noqa: BLE001
            logger.warning(f"Artifact upload best-effort failed for {job_id}: {up_e}")

        append_log(job_id, "Job completed successfully")
        
        logger.info(f"Job {job_id} completed successfully")
        
    except Exception as e:
        error_msg = str(e)
        logger.exception(f"Job {job_id} failed: {e}")
        set_status(
            job_id,
            state="error",
            step="error",
            error=error_msg
        )
        append_log(job_id, f"ERROR: {error_msg}")


def _upload_artifacts(job_id: str) -> None:
    """Best-effort upload of known artifacts to storage.

    Normalizes final video to key '{job_id}/final.mp4'.
    Skips missing files; logs warnings but does not raise.
    """
    storage = get_storage()
    job_dir = OUTPUT_ROOT / job_id

    # Final video: support multiple on-disk names, upload under canonical key
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
            log_event(job_id, "artifact_uploaded", "Uploaded final video", {"key": f"{job_id}/final.mp4", "size_bytes": size})
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Upload final.mp4 failed for {job_id}: {e}")

    # TTS audio
    tts_src = job_dir / "tts.wav"
    if tts_src.exists():
        try:
            storage.put_file(f"{job_id}/tts.wav", str(tts_src))
            try:
                size = tts_src.stat().st_size
            except Exception:
                size = None
            log_event(job_id, "artifact_uploaded", "Uploaded tts.wav", {"key": f"{job_id}/tts.wav", "size_bytes": size})
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Upload tts.wav failed for {job_id}: {e}")

    # Thumbnail image
    thumb_src = job_dir / "thumb.png"
    if thumb_src.exists():
        try:
            storage.put_file(f"{job_id}/thumb.png", str(thumb_src))
            try:
                size = thumb_src.stat().st_size
            except Exception:
                size = None
            log_event(job_id, "artifact_uploaded", "Uploaded thumb.png", {"key": f"{job_id}/thumb.png", "size_bytes": size})
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Upload thumb.png failed for {job_id}: {e}")


# ============================================================================== 
# Regenerate / Duplicate helpers
# ============================================================================== 
class RegenerateOverrides(BaseModel):
    topic: Optional[str] = None
    language: Optional[str] = None
    voice: Optional[str] = None
    voice_id: Optional[str] = None
    fast_path: Optional[bool] = None
    proxy: Optional[bool] = None
    quality: Optional[str] = None
    scenes: Optional[List[SceneInput]] = None


def _load_base_plan(job_id: str) -> Optional[dict]:
    """Load base plan JSON for a job from DB or fallback to job_summary.json."""
    # Try DB first
    try:
        conn = get_conn()
        try:
            row = conn.execute(
                "SELECT input_json FROM jobs_index WHERE id = ?",
                (job_id,),
            ).fetchone()
        finally:
            conn.close()
        if row and row["input_json"]:
            try:
                return json.loads(row["input_json"])  # type: ignore[arg-type]
            except Exception:
                pass
    except Exception:
        pass

    # Fallback to job_summary.json 'plan' field if available
    summary_path = OUTPUT_ROOT / job_id / "job_summary.json"
    if summary_path.exists():
        try:
            data = json.loads(summary_path.read_text(encoding="utf-8"))
            plan = data.get("plan")
            if isinstance(plan, dict):
                return plan
        except Exception:
            return None
    return None


def _get_job_owner(job_id: str) -> str:
    """Return job owner user_id, or empty string if anonymous/unknown."""
    try:
        conn = get_conn()
        try:
            owner_row = conn.execute("SELECT user_id FROM jobs_index WHERE id = ?", (job_id,)).fetchone()
        finally:
            conn.close()
        if owner_row:
            return owner_row["user_id"] or ""
    except Exception:
        pass

    try:
        qrow = get_job_row(job_id)
        if qrow:
            user_id = qrow.get("user_id")
            if user_id is not None:
                return user_id or ""
    except Exception:
        pass

    return ""


# ==============================================================================
# API Endpoints
# ==============================================================================
def _enqueue_plan(plan_dict: dict, user) -> Dict[str, Any]:
    job_id = plan_dict.get("job_id") or str(uuid.uuid4())
    plan_dict["job_id"] = job_id

    if user:
        check_quota_or_raise(user["id"], add_renders=1)

    try:
        conn = get_conn()
        try:
            now = datetime.utcnow().isoformat()
            plan_json = json.dumps(plan_dict)
            conn.execute(
                (
                    "INSERT OR IGNORE INTO jobs_index (id, user_id, project_id, title, created_at, input_json, parent_job_id) "
                    "VALUES (?,?,?,?,?,?,?)"
                ),
                (job_id, user["id"] if user else "", None, plan_dict.get("topic") or "", now, plan_json, None),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception:
        pass

    enqueue_job(job_id, user["id"] if user else "", json.dumps(plan_dict))

    if user:
        try:
            inc_renders(user["id"], 1)
        except Exception:
            pass

    return {
        "job_id": job_id,
        "status": "queued",
        "estimated_wait_seconds": 120 if not SIMULATE_RENDER else 0,
        "fast_path": plan_dict.get("fast_path"),
        "proxy": plan_dict.get("proxy"),
        "message": "Job queued successfully",
    }


def _build_simple_scenes(req: SimpleRenderRequest) -> List[SceneInput]:
    duration = req.duration_sec or 60.0
    count = int(round(duration / 15.0)) or 5
    count = max(3, min(8, count))
    base = max(duration / count, 0.5)
    durations: List[float] = [round(base, 2) for _ in range(count)]
    durations[-1] = max(0.5, round(duration - sum(durations[:-1]), 2))
    variations = ["intro", "insight", "reflection", "practice", "blessing", "closing", "lesson", "takeaway"]
    scenes: List[SceneInput] = []
    for idx in range(count):
        tag = variations[idx % len(variations)]
        prompt_bits = [req.topic, req.style or "", req.language]
        prompt = " | ".join([p for p in prompt_bits if p]).strip()
        prompt = f"{prompt} - {tag}".strip(" -")
        narration = f"{req.topic} scene {idx + 1} {tag}"
        scenes.append(SceneInput(image_prompt=prompt, narration=narration, duration_sec=durations[idx]))
    return scenes


@router.post("")
def post_render(plan: RenderPlan, request: Request, user=Depends(get_current_user)):
    """
    POST /render: Create a new render job
    
    Accepts RenderPlan JSON body, validates, creates job, starts background processing.
    Returns job_id immediately for status polling.
    
    Returns:
        - 200: Job created successfully with job_id
        - 422: Invalid input (Pydantic validation)
        - 400: Business logic error (bad plan)
        - 500: Unexpected server error
    """
    try:
        # Create job ID
        job_id = str(uuid.uuid4())
        logger.info(f"Creating render job {job_id} for topic: {plan.topic}")
        
        # Defensive logging: verify duration types after Pydantic validation
        logger.info("API durations(types)=%s values=%s",
            [type(s.duration_sec).__name__ for s in plan.scenes],
            [s.duration_sec for s in plan.scenes]
        )
        # Convert plan to dict (mode="python" preserves numeric types)
        plan_dict = plan.model_dump(mode="python")
        plan_dict["job_id"] = job_id
        
        # Return immediately
        return _enqueue_plan(plan_dict, user)
        
    except ValidationError as e:
        # Pydantic validation errors (should be caught by FastAPI automatically)
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    
    except Exception as e:
        # Unexpected errors
        logger.exception(f"Unexpected error creating render job: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"render_failed: {str(e)}"
        )


@router.post("/simple")
def post_simple_render(req: SimpleRenderRequest, request: Request, user=Depends(get_current_user)):
    try:
        lang = req.language or "hi"
        if lang not in ("en", "hi"):
            lang = "hi"
        scenes = _build_simple_scenes(req)
        plan = RenderPlan(
            topic=req.topic,
            language=lang,
            voice=req.voice,
            scenes=scenes,
            fast_path=req.fast_path,
            proxy=req.proxy if req.proxy is not None else True,
        )
        plan_dict = plan.model_dump(mode="python")
        plan_dict["style"] = req.style
        plan_dict["duration_sec"] = req.duration_sec
        return _enqueue_plan(plan_dict, user)
    except Exception as e:
        logger.exception(f"Error creating simple render: {e}")
        raise


@router.get("/{job_id}/status")
def get_render_status(job_id: str, user=Depends(get_current_user)):
    """
    GET /render/{job_id}/status: Poll job status
    
    Returns current job state, progress, logs, and output URLs.
    
    Returns:
        - 200: Job status found
        - 404: Job not found
    """
    try:
        qrow = get_job_row(job_id)
        if not user:
            if not (qrow and (qrow.get("user_id") == "")):
                raise HTTPException(status_code=401, detail="Unauthorized")
        else:
            owner_id = _get_job_owner(job_id)
            if owner_id and owner_id != user["id"]:
                raise HTTPException(status_code=403, detail="Forbidden")

        # First, check durable queue status
        if qrow:
            qstatus = qrow["status"]
            if qstatus in ("queued", "running"):
                raw = {"state": qstatus, "progress_pct": None}
                return _format_job_status(raw)
            if qstatus == "failed":
                err = {"code": qrow.get("err_code") or "UNKNOWN", "message": qrow.get("err_message") or "Render failed", "phase": "finalize"}
                return _format_job_status({"state": "error", "error": err})
            if qstatus in ("cancelled", "canceled"):
                return _format_job_status({"state": "cancelled"})

        # If completed or if no queue row, fall back to job summary/artifacts
        status = get_status(job_id)

        if not status:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found"
            )

        return _format_job_status(status)

    except HTTPException:
        raise

    except Exception as exc:  # noqa: BLE001 - return structured error envelope
        logger.exception(f"Error getting status for {job_id}: {exc}")
        return {
            "status": "failed",
            "error": {
                "code": "UNKNOWN",
                "phase": "finalize",
                "message": "Unable to fetch job status",
                "meta": {"job_id": job_id},
            },
        }


@router.get("/{job_id}/activity")
def get_job_activity(job_id: str, limit: int = Query(default=100, ge=1, le=1000)):
    """
    GET /render/{job_id}/activity: Get activity log events
    
    Returns activity log events for a specific job, newest first.
    
    Args:
        job_id: Job UUID
        limit: Maximum number of events to return (default 100, max 1000)
    
    Returns:
        - 200: {"events": [...]}
        - 500: Error reading events
    """
    try:
        from backend.backend.app.logs.activity import read_events
        events = read_events(job_id, limit)
        return {"events": events}
    
    except Exception as e:
        logger.exception(f"Error reading activity for {job_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"activity_fetch_failed: {str(e)}"
        )


@router.get("/test")
def test_endpoint():
    """Health check for render router"""
    return {
        "status": "ok",
        "message": "Render router is operational",
        "simulate_mode": bool(SIMULATE_RENDER),
        "active_jobs": len(JOBS)
    }


@router.get("/selftest")
def selftest_endpoint():
    """
    Comprehensive self-test endpoint
    Tests orchestrator, rendering pipeline, status tracking, and file generation
    Returns detailed test results
    """
    logger.info("Starting self-test...")
    
    try:
        if SIMULATE_RENDER:
            # Run simulator self-test
            from orchestrator import run_selftest_simulated
            results = run_selftest_simulated()
        else:
            # Run real orchestrator self-test
            try:
                from pipeline.real_orchestrator import run_selftest_real
                results = run_selftest_real()
            except ImportError as e:
                results = {
                    "passed": False,
                    "error": f"Real orchestrator not available: {e}",
                    "tests": []
                }
        
        return {
            "status": "passed" if results.get("passed") else "failed",
            "mode": "simulator" if SIMULATE_RENDER else "real",
            "results": results,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.exception("Self-test failed with exception")
        return {
            "status": "error",
            "mode": "simulator" if SIMULATE_RENDER else "real",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.post("/{job_id}/duplicate")
def duplicate_job(job_id: str, overrides: Optional[RegenerateOverrides] = None, user=Depends(get_current_user)):
    """Duplicate an existing job by cloning its input plan with optional overrides.

    Returns a new job_id and enqueues it via the durable queue.
    """
    # Ownership enforcement
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        conn = get_conn()
        try:
            owner = conn.execute("SELECT user_id FROM jobs_index WHERE id = ?", (job_id,)).fetchone()
        finally:
            conn.close()
        if not owner:
            raise HTTPException(status_code=404, detail="Job not found")
        if owner["user_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="Forbidden")
    except HTTPException:
        raise
    except Exception:
        # Continue; base plan load will fail gracefully
        pass

    base_plan = _load_base_plan(job_id)
    if not isinstance(base_plan, dict):
        raise HTTPException(status_code=400, detail="Base plan unavailable for duplication")

    # Apply overrides if provided
    if overrides:
        ov = overrides.model_dump(exclude_none=True)
        for key in ["topic", "language", "voice", "voice_id", "fast_path", "proxy", "quality"]:
            if key in ov:
                base_plan[key] = ov[key]
        if "scenes" in ov and isinstance(ov["scenes"], list):
            # Pydantic SceneInput already validated
            base_plan["scenes"] = [s.model_dump(mode="python") if hasattr(s, 'model_dump') else s for s in ov["scenes"]]

    # Create new job id and persist
    new_job_id = str(uuid.uuid4())
    base_plan["job_id"] = new_job_id

    title = str(base_plan.get("topic") or f"Copy of {job_id}")

    # Insert into jobs_index with lineage and stored input_json
    try:
        conn = get_conn()
        try:
            now = datetime.utcnow().isoformat()
            conn.execute(
                (
                    "INSERT OR IGNORE INTO jobs_index (id, user_id, project_id, title, created_at, input_json, parent_job_id) "
                    "VALUES (?,?,?,?,?,?,?)"
                ),
                (new_job_id, user["id"], None, title, now, json.dumps(base_plan), job_id),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception:
        # Non-fatal; proceed to enqueue regardless
        pass

    # Enqueue cloned plan
    enqueue_job(new_job_id, user["id"], json.dumps(base_plan))

    # Best-effort activity log
    try:
        log_event(job_id, "regenerate", "Duplicated job", {"new_job_id": new_job_id})
        log_event(new_job_id, "job_created", "Enqueued duplicated job", {"parent_job_id": job_id})
    except Exception:
        pass

    return {"job_id": new_job_id, "status": "queued", "parent_job_id": job_id}


@router.post("/{job_id}/regenerate")
def regenerate_job(job_id: str, overrides: Optional[RegenerateOverrides] = None, user=Depends(get_current_user)):
    """Alias for duplicate; maintained for API clarity."""
    return duplicate_job(job_id, overrides, user)  # type: ignore[arg-type]


@router.post("/{job_id}/cancel")
def cancel_render(job_id: str, user=Depends(get_current_user)):
    """Cancel a queued/running render job."""
    # Auth + ownership
    qrow = get_job_row(job_id)
    if not user:
        if not (qrow and (qrow.get("user_id") == "")):
            raise HTTPException(status_code=401, detail="Unauthorized")
    else:
        owner_id = _get_job_owner(job_id)
        if owner_id and owner_id != user["id"]:
            raise HTTPException(status_code=403, detail="Forbidden")

    if not qrow:
        fallback_status = get_status(job_id)
        if fallback_status:
            state = str(fallback_status.get("state") or "").lower()
            if state in {"cancelled", "canceled"}:
                return {"status": "canceled", "job_id": job_id, "already": True}
            if state in {"success", "completed", "error", "failed"}:
                raise HTTPException(status_code=409, detail=f"Job is already {state}")
        raise HTTPException(status_code=404, detail="Job not found")

    status = qrow.get("status")
    if status in ("cancelled", "canceled"):
        return {"status": "canceled", "job_id": job_id, "already": True}
    if status not in ("queued", "running"):
        raise HTTPException(status_code=409, detail=f"Job is already {status or 'completed'}")

    mark_cancelled(job_id, reason="user_cancel")
    set_status(job_id, state="canceled", step="cancelled", progress_pct=qrow.get("progress_pct"))
    try:
        log_event(job_id, "job_cancelled", "User cancelled render", {"user_id": user["id"] if user else ""})
    except Exception:
        pass
    return {"ok": True, "job_id": job_id, "status": "canceled"}
