import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend" / "backend"))
sys.path.insert(0, str(REPO / "backend"))

from fastapi import FastAPI
from backend.backend.app.db import init_db
from backend.backend.routes.shares import router as shares_router
from backend.routes.preflight import router as preflight_router
from backend.routes.render import router as render_router
from backend.routes.storyboard import router as storyboard_router
from backend.routes.stubs import router as stubs_router

app = FastAPI(title="BhaktiGen Backend")

@app.on_event("startup")
def _startup():
    init_db()

app.include_router(preflight_router)
app.include_router(render_router)
app.include_router(storyboard_router)
app.include_router(shares_router)
app.include_router(stubs_router)
app.include_router(shares_router)
