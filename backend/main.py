from fastapi import FastAPI
from .routes.shares import router as shares_router
from backend.routes.preflight import router as preflight_router

app = FastAPI(title="BhaktiGen Backend")

app.include_router(preflight_router)
app.include_router(shares_router)
