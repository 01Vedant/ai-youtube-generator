import os

def _flag(name: str, default: bool = False) -> bool:
    v = os.environ.get(name)
    if v is None: return default
    return str(v).lower() in ("1","true","yes","on")
# ...existing code...
"""
DevotionalAI Platform - FastAPI Backend
Complete production-ready API for multi-user devotional video generation
"""

from pathlib import Path
import sys
import os
import mimetypes

# Configure MIME types for video streaming
mimetypes.add_type("video/mp4", ".mp4")
mimetypes.add_type("video/mp4", ".MP4")

# Add platform root to sys.path for resolving routes/, jobs/, etc.
# __file__ is .../platform/backend/app/main.py, so parents[2] is .../platform
PLATFORM_ROOT = Path(__file__).resolve().parents[2]  # .../platform
if str(PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(PLATFORM_ROOT))

# ============================================================================
# AUTO-CONFIGURE ENVIRONMENT (FFmpeg detection, encoder check, mode selection)
# ============================================================================
from .env_detector import auto_configure_environment
ENV_REPORT = auto_configure_environment()  # Run detection and print report

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, Depends, Request
from app.routes.legal import router as legal_router
from app.routes.onboarding import router as onboarding_router
from app.routes.feedback import router as feedback_router
from app.routes.public import router as public_router
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.maintenance import MaintenanceMiddleware
from app.middleware.logging import LoggingMiddleware, global_uncaught_exception_handler
from app.obs.sentry import init_sentry
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, List
import logging

# Async task queue
from .celery_config import celery_app, create_task, queue_health
from .models import User, Project, Scene, JobStatus
from .auth import verify_token, create_token, hash_password, verify_password
from app.auth.refresh import issue_access, issue_refresh, verify_refresh
from app.db import revoke_refresh
from .storage import S3Storage, LocalStorage
from .config import settings

# Import settings for OUTPUT_ROOT (ARTIFACTS_ROOT)
from .settings import OUTPUT_ROOT
APP_ENV = os.getenv("APP_ENV", "prod")

# Export for other modules
ARTIFACTS_ROOT = OUTPUT_ROOT

from app.routes.render import router as render_router
from routes.artifacts import router as artifacts_router
from routes.exports import router as exports_router
from routes.projects import router as projects_router
from routes.project_links import router as project_links_router
from routes.usage import router as usage_router
try:
    from routes.shares import router as shares_router
except ImportError:
    shares_router = None
try:
    from app.auth.routes import router as auth_router
except Exception as e:
    auth_router = None
from app.db import init_db

# Initialize app



import os

def _flag(name: str, default: bool = False) -> bool:
    v = os.environ.get(name, None)
    if v is None:
        return default
    return str(v).lower() in ("1", "true", "yes", "on")

# Register debug routes last and lazily to avoid import issues
def _maybe_register_debug(app):
    if not _flag("DEBUG_API_ENABLED", False):
        return
    from app.routes.debug import debug_router as _debug_router
    app.include_router(_debug_router, tags=["debug"])

# ...existing code...

# Import render router
from routes.render import router as render_router
from routes.artifacts import router as artifacts_router
from routes.exports import router as exports_router
from routes.projects import router as projects_router
from routes.project_links import router as project_links_router
from routes.usage import router as usage_router
try:
    from routes.shares import router as shares_router
except ImportError:
    shares_router = None
try:
    from app.auth.routes import router as auth_router
except Exception as e:
    auth_router = None
from app.db import init_db

# Initialize app

app = FastAPI(
    title="DevotionalAI Platform API",
    description="Production-ready multi-user devotional video generation platform",
    version="1.0.0"
)

app.add_middleware(LoggingMiddleware)
if not _flag("RATE_LIMIT_DISABLED", False):
    app.add_middleware(RateLimitMiddleware, rate_limit_per_min=settings.RATE_LIMIT_PER_MIN)

_maybe_register_debug(app)

# CORS for frontend - strict allowlist (no wildcards with credentials)
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
if os.getenv('APP_ENV', 'prod') == 'dev':
    # Allow public endpoints broadly in dev
    ALLOWED_ORIGINS = ALLOWED_ORIGINS + ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Range", "Accept-Ranges", "Content-Length"],
    max_age=86400,
)

app.include_router(legal_router)
app.include_router(onboarding_router, prefix="/onboarding")
app.include_router(feedback_router, prefix="/feedback", tags=["feedback"])
if _flag("PUBLIC_ENABLED", False):
    app.include_router(public_router, prefix="/public", tags=["public"])
app.include_router(render_router)

# Ensure OUTPUT_ROOT exists and mount static artifacts directory
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
app.mount("/artifacts", StaticFiles(directory=str(OUTPUT_ROOT)), name="artifacts")

# Add optional middlewares (some may not be present in this deployment)
try:
    from app.middleware.logging import LoggingMiddleware as _LM
    app.add_middleware(_LM)
except Exception:
    pass
try:
    from app.middleware.maintenance import MaintenanceMiddleware as _MM
    if _flag("MAINTENANCE_MODE", False):
        app.add_middleware(_MM)
except Exception:
    pass
try:
    from app.middleware.rate_limit import RateLimitMiddleware as _RLM
    if not _flag("RATE_LIMIT_DISABLED", False):
        app.add_middleware(_RLM, rate_limit_per_min=settings.RATE_LIMIT_PER_MIN)
except Exception:
    pass
    try:
        from app.middleware.security_headers import SecurityHeadersMiddleware as _SHM
        app.add_middleware(_SHM)
    except Exception:
        pass


# Add tenancy middleware early (after API key, before routes)
if _flag("SAAS_ENABLED", False):
    app.add_middleware(TenancyMiddleware)

# Prometheus metrics endpoint
from prometheus_client import CollectorRegistry, generate_latest
from .metrics import get_registry

@app.get("/metrics/prometheus")
async def prometheus_metrics():
    """Export Prometheus metrics."""
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(generate_latest(get_registry()))

# Include artifacts router (REST endpoints for manifest and safe files)
app.include_router(artifacts_router, prefix="/artifacts", tags=["artifacts"])
app.include_router(exports_router, prefix="/exports", tags=["exports"])
if auth_router:
    app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(projects_router, prefix="/projects", tags=["projects"])
app.include_router(project_links_router, prefix="/projects", tags=["projects"]) 
app.include_router(usage_router, prefix="/usage", tags=["usage"])

@app.get("/queue/health")
async def queue_health_endpoint():
    """Queue health check endpoint - reports broker, backend, and eager flag."""
    return queue_health()

@app.on_event("startup")
async def startup_event():
    """Run on application startup - print configuration summary"""
    try:
        init_db()
    except Exception as e:
        logger.error("DB init failed: %s", e)
    # Best-effort S3 bucket bootstrap if S3 storage is configured
    try:
        from app.artifacts_storage.factory import get_storage
        from app.artifacts_storage.s3 import S3Storage
        storage = get_storage()
        if isinstance(storage, S3Storage) and getattr(storage, 'bucket', None):
            try:
                storage.client.head_bucket(Bucket=storage.bucket)
            except Exception:
                try:
                    storage.client.create_bucket(Bucket=storage.bucket)
                    logger.info("Created S3 bucket: %s", storage.bucket)
                except Exception as be:
                    logger.warning("S3 bucket bootstrap skipped: %s", be)
    except Exception:
        pass
    print("\n" + "="*70)
    print("🚀 BHAKTI VIDEO GENERATOR API STARTED")
    print("="*70)
    print(f"📡 Server: http://127.0.0.1:8000")
    print(f"📚 Docs: http://127.0.0.1:8000/docs")
    print(f"🧪 Self-test: http://127.0.0.1:8000/render/selftest")
    print(f"⚙️  Mode: {'SIMULATOR (dev)' if ENV_REPORT['mode']['simulate_render'] else 'REAL (production)'}")
    print(f"💡 Reason: {ENV_REPORT['mode']['reason']}")
    print("="*70 + "\n")


@app.get("/healthz")
async def healthz():
    """Basic health check - always returns 200 if app is running."""
    return {"ok": True, "status": "healthy"}

@app.get("/debug/tts")
async def debug_tts():
    """
    Task 3: Expose real provider status end-to-end
    Returns: {"provider": "edge"|"mock", "voices": [...], "ok": true}
    """
    try:
        from app.tts.engine import get_provider_info, health_check, HINDI_VOICE_MAP
        from app.config import settings
        
        provider_info = get_provider_info()
        health_result = health_check()
        
        # Extract provider name from provider_info
        provider_name = provider_info.get("name", "unknown")
        
        # Get Hindi voices from map
        hindi_voices = list(HINDI_VOICE_MAP.keys()) if provider_name == "edge" else ["mock"]
        
        return {
            "ok": health_result["ok"],
            "provider": provider_name,  # "edge" or "mock"
            "voices": hindi_voices,
            "default_voice": settings.TTS_VOICE,
            "rate": settings.TTS_RATE,
            "strict_mode": settings.TTS_STRICT,
            "health": health_result
        }
    except Exception as e:
        logger.exception("TTS debug check failed")
        return {
            "ok": False,
            "provider": "unknown",
            "voices": [],
            "error": str(e)
        }

@app.get("/readyz")
async def readyz():
    """Readiness check - verifies platform imports, ffmpeg, and output directory."""
    try:
        import shutil
        
        # Verify platform root is accessible
        if not PLATFORM_ROOT.exists():
            raise HTTPException(status_code=503, detail="Platform root not found")
        
        # Try importing routes to verify sys.path is correct
        try:
            import routes.render
        except ImportError as e:
            raise HTTPException(status_code=503, detail=f"Routes import failed: {e}")
        
        # Check ffmpeg availability
        simulate_mode = int(os.getenv("SIMULATE_RENDER", "1"))
        ffmpeg_ok = bool(shutil.which("ffmpeg")) if not simulate_mode else None
        
        # Verify OUTPUT_ROOT is writable
        write_ok = False
        test_file = OUTPUT_ROOT / ".readyz_test"
        try:
            test_file.write_text("ok")
            test_file.unlink()
            write_ok = True
        except Exception as e:
            logger.warning(f"Output directory not writable: {e}")
            if not simulate_mode:
                raise HTTPException(status_code=503, detail=f"Output directory not writable: {e}")
        
        # Check schedule storage is writable
        schedule_dir = Path("platform/schedules")
        schedule_store_ok = False
        try:
            schedule_dir.mkdir(parents=True, exist_ok=True)
            schedule_test = schedule_dir / ".readyz_test"
            schedule_test.write_text("ok")
            schedule_test.unlink()
            schedule_store_ok = True
        except Exception as e:
            logger.warning(f"Schedule storage not writable: {e}")
        
        return {
            "ok": True,
            "status": "ready",
            "platform_root": str(PLATFORM_ROOT),
            "artifacts_root": str(OUTPUT_ROOT),
            "simulate_mode": bool(simulate_mode),
            "ffmpeg_ok": ffmpeg_ok,
            "write_ok": write_ok and OUTPUT_ROOT.is_dir(),
            "schedule_store_ok": schedule_store_ok,
            "environment": ENV_REPORT
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Readiness check failed")
        raise HTTPException(status_code=503, detail=str(e))

@app.get("/debug/cors")
async def debug_cors(request: Request):
    """Debug endpoint to verify CORS configuration."""
    return {
        "origins": ALLOWED_ORIGINS,
        "allow_credentials": True,
        "note": "CORS middleware is registered before routers & static mounts."
    }

# TTS Preview endpoint
from pydantic import BaseModel as PydanticBaseModel
from app.auth.security import get_current_user
from app.usage.service import check_quota_or_raise, inc_tts_sec
from app.metrics import add_tts_seconds

class TTSPreviewRequest(PydanticBaseModel):
    text: str
    lang: str = "hi"
    voice_id: str | None = None
    pace: float | None = None

@app.post("/tts/preview", tags=["tts"])
async def tts_preview(request: TTSPreviewRequest, user=Depends(get_current_user)):
    """
    Preview TTS synthesis for a given text
    Returns URL to generated WAV file
    """
    import hashlib
    from backend.app.tts import synthesize
    
    # Create preview directory
    preview_dir = OUTPUT_ROOT / "_previews"
    preview_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate hash for caching
    content = f"{request.voice_id}|{request.text}|{request.pace}|{request.lang}"
    file_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
    preview_path = preview_dir / f"{file_hash}.wav"
    
    # Synthesize if not cached
    if not preview_path.exists():
        try:
            wav_bytes, metadata = synthesize(
                text=request.text,
                lang=request.lang,
                voice_id=request.voice_id,
                pace=request.pace
            )
            preview_path.write_bytes(wav_bytes)
        except Exception as e:
            logger.error(f"TTS preview failed: {e}")
            raise HTTPException(status_code=500, detail=f"TTS synthesis failed: {str(e)}")
    
    # Get duration
    import wave
    import io
    with wave.open(str(preview_path), 'rb') as wav:
        frames = wav.getnframes()
        rate = wav.getframerate()
        duration_sec = frames / rate
    
    # Enforce quota only for authenticated users (anonymous unaffected)
    try:
        if user:
            # check then increment after successful synthesis
            check_quota_or_raise(user["id"], add_tts_sec=int(duration_sec))
            inc_tts_sec(user["id"], int(duration_sec))
            try:
                add_tts_seconds(duration_sec)
            except Exception:
                pass
    except Exception as e:
        # If quota exceeded, bubble up the HTTPException
        raise

    return {
        "url": f"/artifacts/_previews/{file_hash}.wav",
        "duration_sec": duration_sec,
        "cached": preview_path.exists()
    }

# Include render router
app.include_router(render_router)

# Include Creator Mode routers
from routes.templates import router as templates_router
from app.routes.templates_marketplace import router as marketplace_router
from routes.library import router as library_router
from routes.publish import router as publish_router
from routes.schedule import router as schedule_router
from routes.dashboard import router as dashboard_router
try:
    from routes.admin_purge import router as admin_purge_router
except ImportError:
    admin_purge_router = None
try:
    from routes.admin import router as admin_router
except ImportError:
    admin_router = None
try:
    from routes.onboarding import router as onboarding_router
except ImportError:
    onboarding_router = None
try:
    from routes.analytics import router as analytics_router
except ImportError:
    analytics_router = None
try:
    from routes.growth import router as growth_router
except ImportError:
    growth_router = None
try:
    from routes.logs import router as logs_router
except ImportError:
    logs_router = None
from app.flags import get_flags, set_flag
from fastapi import APIRouter, Depends
try:
    from app.auth.guards import require_admin
    from app.auth import get_current_user
    _auth_available = True
except ImportError:
    _auth_available = False

app.include_router(templates_router)
app.include_router(marketplace_router)
app.include_router(library_router)
app.include_router(publish_router)
app.include_router(schedule_router)
app.include_router(dashboard_router)
if shares_router:
    app.include_router(shares_router, tags=["shares"])
try:
    from routes.health import router as health_router
    app.include_router(health_router, tags=["health"])
except ImportError:
    pass
if admin_purge_router:
    app.include_router(admin_purge_router)
if admin_router:
    app.include_router(admin_router)
if onboarding_router:
    app.include_router(onboarding_router)
if analytics_router:
    app.include_router(analytics_router, prefix="/analytics", tags=["analytics"])
if growth_router:
    app.include_router(growth_router, prefix="/growth", tags=["growth"])
if logs_router:
    app.include_router(logs_router, prefix="/logs", tags=["logs"])

# E2E test helpers (dev-only)
if APP_ENV == "dev":
    try:
        from app.routes.e2e import router as e2e_router
        app.include_router(e2e_router, prefix="/__e2e", tags=["e2e"])
    except Exception:
        pass

# Legal and privacy/status routers
try:
    from app.routes.legal import router as legal_router
    app.include_router(legal_router, prefix="/legal", tags=["legal"])
except Exception:
    pass
try:
    from app.routes.privacy import router as privacy_router
    app.include_router(privacy_router, prefix="/privacy", tags=["privacy"])
except Exception:
    pass
try:
    from app.routes.status import router as status_router
    app.include_router(status_router, tags=["status"])
except Exception:
    pass

# Admin flags router
if _auth_available:
    flags_router = APIRouter(prefix="/admin", tags=["admin"])

    @flags_router.get('/flags')
    def admin_get_flags(user=Depends(get_current_user)):
        require_admin(user)
        return get_flags()

    @flags_router.put('/flags')
    def admin_put_flag(payload: dict, user=Depends(get_current_user)):
        require_admin(user)
        key = str(payload.get('key'))
        val = bool(payload.get('value'))
        set_flag(key, val)
        return get_flags()

    app.include_router(flags_router)

# Debug endpoint for video inspection (focused)
@app.get("/debug/video/{job_id}", tags=["debug"])
async def debug_video(job_id: str):
    """Inspect video file status for a job"""
    job_dir = OUTPUT_ROOT / job_id
    
    if not job_dir.exists():
        raise HTTPException(status_code=404, detail=f"Job directory not found: {job_id}")
    
    # Check candidates in order
    candidates = ["final_video.mp4", "final.mp4", "output.mp4"]
    chosen = None
    exists = False
    size_bytes = 0
    url = None
    
    for candidate in candidates:
        video_path = job_dir / candidate
        if video_path.exists():
            chosen = candidate
            exists = True
            size_bytes = video_path.stat().st_size
            url = f"/artifacts/{job_id}/{candidate}"
            break
    
    # Fallback: find any .mp4 in subdirs
    all_mp4s = []
    if job_dir.exists():
        for mp4_file in job_dir.rglob("*.mp4"):
            if mp4_file.is_file():
                rel_path = str(mp4_file.relative_to(job_dir)).replace("\\", "/")
                all_mp4s.append({
                    "path": rel_path,
                    "size_bytes": mp4_file.stat().st_size,
                    "url": f"/artifacts/{job_id}/{rel_path}"
                })
                if not chosen:
                    chosen = rel_path
                    exists = True
                    size_bytes = mp4_file.stat().st_size
                    url = f"/artifacts/{job_id}/{rel_path}"
    
    return {
        "job_id": job_id,
        "chosen": chosen,
        "exists": exists,
        "size_bytes": size_bytes,
        "size_mb": round(size_bytes / (1024 * 1024), 2) if size_bytes > 0 else 0,
        "url": url,
        "files": all_mp4s
    }

# Debug endpoint for artifact inspection
@app.get("/debug/artifacts/{job_id}", tags=["debug"])
async def debug_artifacts(job_id: str):
    """List all artifacts for a job with file sizes and video status"""
    job_dir = OUTPUT_ROOT / job_id
    
    if not job_dir.exists():
        raise HTTPException(status_code=404, detail=f"Job directory not found: {job_id}")
    
    files = []
    has_final_video = False
    final_video_location = None
    
    for file_path in job_dir.rglob("*"):
        if file_path.is_file():
            rel_path = file_path.relative_to(job_dir)
            size_bytes = file_path.stat().st_size
            
            # Check for video in either location
            if file_path.name == "final.mp4" and "final" in str(rel_path):
                has_final_video = True
                final_video_location = str(rel_path).replace("\\", "/")
            elif file_path.name == "final_video.mp4":
                has_final_video = True
                final_video_location = str(rel_path).replace("\\", "/")
            
            files.append({
                "path": str(rel_path).replace("\\", "/"),
                "size_bytes": size_bytes,
                "size_mb": round(size_bytes / (1024 * 1024), 2),
                "url": f"/artifacts/{job_id}/{str(rel_path).replace(chr(92), '/')}"
            })
    
    return {
        "job_id": job_id,
        "job_dir": str(job_dir),
        "has_final_video": has_final_video,
        "final_video_location": final_video_location,
        "final_video_url": f"/artifacts/{job_id}/{final_video_location}" if final_video_location else None,
        "file_count": len(files),
        "files": sorted(files, key=lambda x: x["path"])
    }

# Include diagnostics and retention routers
try:
    from backend.app.routes.diagnostics import router as diagnostics_router
    app.include_router(diagnostics_router)
except ImportError:
    pass

try:
    from app.retention import router as retention_router
    app.include_router(retention_router)
except ImportError:
    pass

# Include SaaS routers (auth, billing, account)
if _flag("SAAS_ENABLED", False):
    app.include_router(auth_router)
    app.include_router(billing_router)
    app.include_router(account_router)

# Security
security = HTTPBearer()

# Storage backend (S3 or Local)
storage = S3Storage() if settings.USE_S3 else LocalStorage()

# =============================================================================
# AUTH ENDPOINTS
# =============================================================================

@app.post("/api/v1/auth/register")
async def register(email: str, password: str, name: str):
    """Register new user"""
    try:
        user = User.create(email=email, password=hash_password(password), name=name)
        # Best-effort onboarding seed: project + completed demo job + tiny artifacts
        try:
            import uuid as _uuid
            seed_project_id = str(_uuid.uuid4())
            project = Project.create(
                user_id=user.id,
                project_id=seed_project_id,
                name="Getting Started",
                description="Sample project",
                story_data={"scenes": []}
            )
            demo_id_short = str(_uuid.uuid4())[:8]
            seed_job_id = f"demo-{demo_id_short}"
            job = JobStatus.create(job_id=seed_job_id, user_id=user.id, project_id=project.id, task_type="video_stitch")
            job.update_status(status="completed", progress=100, message="Welcome to BhaktiGen", result={"title": "Welcome to BhaktiGen"})
            # Artifacts under OUTPUT_ROOT/demo-<id>
            job_dir = OUTPUT_ROOT / seed_job_id
            job_dir.mkdir(parents=True, exist_ok=True)
            # 1x1 PNG
            try:
                png_bytes = bytes([137,80,78,71,13,10,26,10,0,0,0,13,73,72,68,82,0,0,0,1,0,0,0,1,8,6,0,0,0,31,21,196,137,0,0,0,10,73,68,65,84,120,156,99,96,0,0,0,2,0,1,226,33,185,86,0,0,0,0,73,69,78,68,174,66,96,130])
                (job_dir / "thumb.png").write_bytes(png_bytes)
            except Exception:
                pass
            # Very short silent WAV (44-byte header for 1 sample, 16-bit mono 8kHz)
            try:
                import wave, io
                buf = io.BytesIO()
                with wave.open(buf, 'wb') as w:
                    w.setnchannels(1)
                    w.setsampwidth(2)
                    w.setframerate(8000)
                    w.writeframes(b"\x00\x00")
                (job_dir / "tts.wav").write_bytes(buf.getvalue())
            except Exception:
                pass
            # Placeholder MP4 (empty file ok)
            try:
                (job_dir / "final.mp4").write_bytes(b"")
            except Exception:
                pass
            try:
                logger.info(json.dumps({"type":"onboarding_seed","user_id":user.id,"project_id":project.id,"job_id":seed_job_id,"ok":True}))
            except Exception:
                pass
        except Exception as se:
            try:
                logger.warning(json.dumps({"type":"onboarding_seed","user_id":user.id,"error":str(se),"ok":False}))
            except Exception:
                pass
        return {
            "success": True,
            "user_id": user.id,
            "email": user.email,
            "token": create_token(user.id, expires_hours=24)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/auth/login")
async def login(email: str, password: str):
    """Login user"""
    user = User.get_by_email(email)
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access, exp = issue_access(user.id)
    refresh, jti, r_exp = issue_refresh(user.id)
    # Set HttpOnly refresh cookie
    secure = os.getenv("APP_ENV", "dev") == "prod"
    max_age = int(os.getenv("REFRESH_EXPIRES_DAYS", "14")) * 86400
    from fastapi import Response
    resp = Response(media_type="application/json")
    resp.set_cookie(
        key="refresh_token",
        value=refresh,
        httponly=True,
        samesite="lax",
        secure=secure,
        max_age=max_age,
        path="/auth/",
    )
    resp.body = json.dumps({
        "success": True,
        "user_id": user.id,
        "email": user.email,
        "name": user.name,
        "access_token": access,
        "token_type": "bearer",
        "expires_at": exp,
    }).encode()
    return resp
@app.post("/auth/refresh")
async def refresh_token(request: Request):
    # CSRF is enforced by middleware
    ref = request.cookies.get("refresh_token")
    if not ref:
        return JSONResponse(status_code=401, content={"error": {"code": "INVALID_REFRESH"}})
    try:
        user_id, old_jti = verify_refresh(ref)
    except Exception:
        # Expire cookie on invalid
        resp = JSONResponse(status_code=401, content={"error": {"code": "INVALID_REFRESH"}})
        resp.set_cookie("refresh_token", "", max_age=0, path="/auth/", httponly=True)
        return resp
    # Rotate: revoke old, issue new
    revoke_refresh(old_jti, datetime.now().isoformat())
    access, exp = issue_access(user_id)
    new_ref, new_jti, r_exp = issue_refresh(user_id)
    secure = os.getenv("APP_ENV", "dev") == "prod"
    max_age = int(os.getenv("REFRESH_EXPIRES_DAYS", "14")) * 86400
    resp = JSONResponse(content={"access_token": access, "token_type": "bearer", "expires_at": exp})
    resp.set_cookie("refresh_token", new_ref, httponly=True, samesite="lax", secure=secure, max_age=max_age, path="/auth/")
    return resp


@app.post("/auth/logout")
async def logout(request: Request):
    ref = request.cookies.get("refresh_token")
    if ref:
        try:
            user_id, jti = verify_refresh(ref)
            revoke_refresh(jti, datetime.now().isoformat())
        except Exception:
            pass
    resp = JSONResponse(content={"ok": True})
    resp.set_cookie("refresh_token", "", max_age=0, path="/auth/", httponly=True)
    return resp

@app.get("/api/v1/auth/me")
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user"""
    user_id = verify_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = User.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Return tenant info if SaaS enabled
    tenant_id = getattr(user, 'tenant_id', user_id)
    roles = getattr(user, 'roles', ['creator'])
    
    return {
        "user_id": user.id,
        "tenant_id": tenant_id,
        "email": user.email,
        "name": user.name,
        "roles": roles,
        "created_at": user.created_at
    }

# Add /me endpoint alias for SaaS compatibility
if _flag("SAAS_ENABLED", False):
    @app.get("/api/auth/me")
    async def get_current_user_saas(request: Request):
        """Get current user - SaaS compatible endpoint"""
        # Tenant info attached by TenancyMiddleware
        if not hasattr(request.state, 'user_id'):
            raise HTTPException(status_code=401, detail="Unauthorized")
        
        return {
            "user_id": request.state.user_id,
            "tenant_id": request.state.tenant_id,
            "roles": getattr(request.state, 'roles', ['creator']),
        }

# =============================================================================
# PROJECT ENDPOINTS
# =============================================================================

@app.post("/api/v1/projects/create")
async def create_project(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    name: str = None,
    description: str = None,
    template: Optional[str] = None
):
    """Create new project from template or blank"""
    user_id = verify_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    project_id = str(uuid.uuid4())
    
    # Load template if provided
    story_data = None
    if template:
        template_path = Path(__file__).parent.parent.parent / "templates" / f"{template}.json"
        if template_path.exists():
            story_data = json.loads(template_path.read_text())
    
    project = Project.create(
        user_id=user_id,
        project_id=project_id,
        name=name or f"Project {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        description=description,
        story_data=story_data or {"scenes": []}
    )
    
    # Create cloud storage structure
    storage.create_project_structure(user_id, project_id)
    
    logger.info(f"Created project {project_id} for user {user_id}")
    
    return {
        "success": True,
        "project_id": project_id,
        "project": project.to_dict()
    }


@app.post("/api/v1/projects/create_from_title")
async def create_project_from_title(
    title: Optional[str] = None,
    description: Optional[str] = None,
    full_text: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Create a project from a simple title/description and run story generation pipeline."""
    user_id = verify_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    project_id = str(uuid.uuid4())

    project = Project.create(
        user_id=user_id,
        project_id=project_id,
        name=title,
        description=description,
        story_data={"scenes": []}
    )

    storage.create_project_structure(user_id, project_id)

    # Queue story generation
    job_id = create_task(
        task_type="story_generation",
        user_id=user_id,
        project_id=project_id,
        params={"title": title, "description": description or "", "full_text": full_text or "", "max_scenes": 6}
    )

    return {"success": True, "project_id": project_id, "job_id": job_id, "message": "Story generation queued"}

@app.get("/api/v1/projects/{project_id}")
async def get_project(
    project_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get project details"""
    user_id = verify_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    project = Project.get(user_id, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return project.to_dict()

@app.get("/api/v1/projects")
async def list_projects(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    limit: int = 10,
    offset: int = 0
):
    """List all projects for user"""
    user_id = verify_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    projects = Project.list_by_user(user_id, limit=limit, offset=offset)
    return {
        "projects": [p.to_dict() for p in projects],
        "total": Project.count_by_user(user_id)
    }

@app.put("/api/v1/projects/{project_id}")
async def update_project(
    project_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    name: Optional[str] = None,
    description: Optional[str] = None,
    story_data: Optional[dict] = None,
    settings: Optional[dict] = None
):
    """Update project (name, story, settings)"""
    user_id = verify_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    project = Project.get(user_id, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project.update(
        name=name or project.name,
        description=description or project.description,
        story_data=story_data or project.story_data,
        settings=settings or project.settings
    )
    
    logger.info(f"Updated project {project_id}")
    
    return project.to_dict()

@app.delete("/api/v1/projects/{project_id}")
async def delete_project(
    project_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Delete project and all associated assets"""
    user_id = verify_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    project = Project.get(user_id, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Delete from cloud storage
    storage.delete_project(user_id, project_id)
    project.delete()
    
    logger.info(f"Deleted project {project_id}")
    
    return {"success": True, "message": "Project deleted"}

# =============================================================================
# ASSET GENERATION ENDPOINTS (Async Jobs)
# =============================================================================

@app.post("/api/v1/projects/{project_id}/generate/tts")
async def generate_tts(
    project_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    voice: Optional[str] = "aria",
    background_tasks: BackgroundTasks = None
):
    """Generate TTS audio for all scenes"""
    user_id = verify_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    project = Project.get(user_id, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Create async job
    job_id = create_task(
        task_type="tts",
        user_id=user_id,
        project_id=project_id,
        params={"voice": voice}
    )
    
    logger.info(f"Started TTS job {job_id} for project {project_id}")
    
    return {
        "success": True,
        "job_id": job_id,
        "status": "queued",
        "message": "TTS generation queued. Check status with job_id."
    }

@app.post("/api/v1/projects/{project_id}/generate/images")
async def generate_images(
    project_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    engine: str = "openai",
    quality: str = "preview"  # preview (720p) or final (4k)
):
    """Generate AI images for all scenes"""
    user_id = verify_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    project = Project.get(user_id, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    job_id = create_task(
        task_type="image_generation",
        user_id=user_id,
        project_id=project_id,
        params={"engine": engine, "quality": quality}
    )
    
    logger.info(f"Started image generation job {job_id} with engine={engine}, quality={quality}")
    
    return {
        "success": True,
        "job_id": job_id,
        "status": "queued",
        "message": f"Image generation queued ({quality} quality with {engine})"
    }

@app.post("/api/v1/projects/{project_id}/generate/subtitles")
async def generate_subtitles(
    project_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    language: str = "hindi"
):
    """Generate SRT subtitles for all scenes"""
    user_id = verify_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    project = Project.get(user_id, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    job_id = create_task(
        task_type="subtitles",
        user_id=user_id,
        project_id=project_id,
        params={"language": language}
    )
    
    logger.info(f"Started subtitle generation job {job_id}")
    
    return {
        "success": True,
        "job_id": job_id,
        "status": "queued"
    }

@app.post("/api/v1/projects/{project_id}/render/stitch")
async def stitch_video(
    project_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    resolution: str = "4k",  # 720p, 1080p, 4k
    fps: int = 24
):
    """Stitch final video from assets"""
    user_id = verify_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    project = Project.get(user_id, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    job_id = create_task(
        task_type="video_stitch",
        user_id=user_id,
        project_id=project_id,
        params={"resolution": resolution, "fps": fps}
    )
    
    logger.info(f"Started video stitching job {job_id} - {resolution} @ {fps}fps")
    
    return {
        "success": True,
        "job_id": job_id,
        "status": "queued",
        "message": f"Video stitching queued ({resolution} resolution)"
    }

# =============================================================================
# JOB TRACKING
# =============================================================================

@app.get("/api/v1/jobs/{job_id}")
async def get_job_status(
    job_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get status of async job"""
    user_id = verify_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    job = JobStatus.get(job_id)
    if not job or job.user_id != user_id:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "job_id": job_id,
        "status": job.status,
        "progress": job.progress,
        "message": job.message,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "result": job.result
    }

@app.get("/api/v1/projects/{project_id}/jobs")
async def list_project_jobs(
    project_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """List all jobs for a project"""
    user_id = verify_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    project = Project.get(user_id, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    jobs = JobStatus.list_by_project(project_id)
    return {
        "jobs": [
            {
                "job_id": j.id,
                "task_type": j.task_type,
                "status": j.status,
                "progress": j.progress,
                "created_at": j.created_at
            }
            for j in jobs
        ]
    }

# =============================================================================
# DOWNLOAD ENDPOINTS
# =============================================================================

@app.get("/api/v1/projects/{project_id}/download/video")
async def download_video(
    project_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    format: str = "mp4"
):
    """Download final video"""
    user_id = verify_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    project = Project.get(user_id, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    video_path = storage.get_final_video_path(user_id, project_id)
    if not video_path or not Path(video_path).exists():
        raise HTTPException(status_code=404, detail="Video not ready. Please complete stitching first.")
    
    return FileResponse(
        path=video_path,
        media_type="video/mp4",
        filename=f"{project.name}_final.mp4"
    )

@app.get("/api/v1/projects/{project_id}/download/assets")
async def download_assets_zip(
    project_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Download all assets as zip"""
    user_id = verify_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    project = Project.get(user_id, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    zip_path = storage.create_assets_zip(user_id, project_id)
    
    return FileResponse(
        path=zip_path,
        media_type="application/zip",
        filename=f"{project.name}_assets.zip"
    )

@app.get("/api/v1/projects/{project_id}/preview/image/{scene_number}")
async def preview_scene_image(
    project_id: str,
    scene_number: int,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Preview image for specific scene"""
    user_id = verify_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    project = Project.get(user_id, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    image_path = storage.get_scene_image_path(user_id, project_id, scene_number)
    if not image_path or not Path(image_path).exists():
        raise HTTPException(status_code=404, detail="Image not found")
    
    return FileResponse(path=image_path, media_type="image/png")

@app.get("/api/v1/projects/{project_id}/preview/audio/{scene_number}")
async def preview_scene_audio(
    project_id: str,
    scene_number: int,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Preview audio for specific scene"""
    user_id = verify_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    project = Project.get(user_id, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    audio_path = storage.get_scene_audio_path(user_id, project_id, scene_number)
    if not audio_path or not Path(audio_path).exists():
        raise HTTPException(status_code=404, detail="Audio not found")
    
    return FileResponse(path=audio_path, media_type="audio/mpeg")

# =============================================================================
# TEMPLATE ENDPOINTS
# =============================================================================

@app.get("/api/v1/templates")
async def list_templates():
    """List all available story templates"""
    templates_dir = Path(__file__).parent.parent.parent / "templates"
    templates = []
    
    for template_file in templates_dir.glob("*.json"):
        data = json.loads(template_file.read_text())
        templates.append({
            "id": template_file.stem,
            "name": data.get("name", template_file.stem),
            "description": data.get("description", ""),
            "scenes": len(data.get("scenes", [])),
            "category": data.get("category", "general")
        })
    
    return {"templates": sorted(templates, key=lambda x: x["name"])}

@app.get("/api/v1/templates/{template_id}")
async def get_template(template_id: str):
    """Get full template content"""
    template_path = Path(__file__).parent.parent.parent / "templates" / f"{template_id}.json"
    
    if not template_path.exists():
        raise HTTPException(status_code=404, detail="Template not found")
    
    return json.loads(template_path.read_text())

# =============================================================================
# SETTINGS & CONFIG
# =============================================================================

@app.get("/api/v1/settings/voices")
async def get_available_voices():
    """Get list of available TTS voices"""
    return {
        "voices": [
            {"id": "aria", "name": "Aria (Warm Female, Hindi)", "language": "hindi"},
            {"id": "sagara", "name": "Sagara (Deep Male, Hindi)", "language": "hindi"},
            {"id": "daya", "name": "Daya (Gentle Female, Hindi)", "language": "hindi"},
        ]
    }

@app.get("/api/v1/settings/image-engines")
async def get_image_engines():
    """Get list of available image generation engines"""
    return {
        "engines": [
            {"id": "openai", "name": "DALL·E 3 (Cinematic)", "pricing": "high"},
            {"id": "sdxl", "name": "Stable Diffusion XL", "pricing": "medium"},
            {"id": "runway", "name": "Runway Gen-3 (Video)", "pricing": "high"},
            {"id": "local", "name": "Local Placeholder", "pricing": "free"},
        ]
    }

# =============================================================================
# HEALTH & STATUS
# =============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

@app.get("/healthz")
async def liveness_probe():
    """Kubernetes liveness probe - fast, no dependencies"""
    return {"status": "alive"}

@app.get("/readyz")
async def readiness_probe():
    """Kubernetes readiness probe - checks critical dependencies"""
    import shutil
    import subprocess
    from routes.diagnostics import check_ffmpeg, check_disk_space, check_tmp_writable
    
    checks = {}
    
    # Fast subset of preflight checks
    ffmpeg_result = check_ffmpeg()
    checks["ffmpeg"] = ffmpeg_result["ok"]
    
    tmp_result = check_tmp_writable()
    checks["tmp_writable"] = tmp_result["ok"]
    
    disk_result = check_disk_space()
    checks["disk_space"] = disk_result["ok"] and disk_result["free_gb"] > 2.0
    
    # Check Redis if configured
    redis_url = os.environ.get("REDIS_URL")
    if redis_url:
        try:
            import redis
            r = redis.from_url(redis_url, socket_connect_timeout=1)
            r.ping()
            checks["redis"] = True
        except Exception as e:
            logger.warning(f"Redis check failed: {e}")
            checks["redis"] = False
    
    # Ready only if all checks pass
    ready = all(checks.values())
    status_code = 200 if ready else 503
    
    return {
        "status": "ready" if ready else "not_ready",
        "checks": checks,
        "details": {
            "disk_free_gb": disk_result.get("free_gb", 0),
            "tmp_path": tmp_result.get("path", "unknown")
        }
    }

@app.get("/api/v1/stats")
async def platform_stats(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get platform statistics"""
    user_id = verify_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = User.get(user_id)
    projects = Project.list_by_user(user_id, limit=1000)
    
    return {
        "user": user.email,
        "total_projects": len(projects),
        "storage_used_gb": sum(p.estimated_size_gb for p in projects),
        "videos_generated": len([p for p in projects if p.status == "completed"]),
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
