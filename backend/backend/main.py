from fastapi import FastAPI
from backend.backend.routes.shares import router as shares_router
from backend.routes.preflight import router as preflight_router
from backend.routes.render import router as render_router

app = FastAPI(title="BhaktiGen Backend")

app.include_router(preflight_router)
app.include_router(render_router)
app.include_router(shares_router)
