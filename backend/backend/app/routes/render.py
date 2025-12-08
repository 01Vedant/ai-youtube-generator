from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from uuid import uuid4
import os
from pathlib import Path

router = APIRouter()

# In-memory job store for demo (replace with DB in prod)
RENDER_JOBS = {}
ARTIFACTS_ROOT = Path(os.environ.get("ARTIFACTS_ROOT", "artifacts"))
ARTIFACTS_ROOT.mkdir(exist_ok=True, parents=True)

class RenderRequest(BaseModel):
    script: str
    template_id: str
    duration_sec: int

class RenderJob(BaseModel):
    job_id: str
    status: str
    artifacts: dict

# Minimal stub renderer
SIMULATE_RENDER = os.environ.get("SIMULATE_RENDER", "0") in ("1", "true", "yes", "on")

PLACEHOLDER_FILES = {
    "artifact": ARTIFACTS_ROOT / "placeholder_4k.png",
    "audio": ARTIFACTS_ROOT / "placeholder_silence.mp3",
    "video": ARTIFACTS_ROOT / "placeholder.mp4",
}

# Create placeholder files if simulating
if SIMULATE_RENDER:
    for k, f in PLACEHOLDER_FILES.items():
        if not f.exists():
            with open(f, "wb") as fp:
                fp.write(b"\x00" * 1024)  # 1KB stub

@router.post("/render")
def start_render(req: RenderRequest):
    job_id = str(uuid4())
    job = RenderJob(job_id=job_id, status="queued", artifacts={})
    RENDER_JOBS[job_id] = job.dict()
    # Simulate background worker
    if SIMULATE_RENDER:
        # Immediately mark as success
        job.status = "success"
        job.artifacts = {k: f.name for k, f in PLACEHOLDER_FILES.items()}
        RENDER_JOBS[job_id] = job.dict()
    else:
        # In real: enqueue task, update status async
        job.status = "running"
        RENDER_JOBS[job_id] = job.dict()
    return {"job_id": job_id}

@router.get("/render/{job_id}")
def poll_render(job_id: str):
    job = RENDER_JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job
