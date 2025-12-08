from fastapi import FastAPI
from .routes.shares import router as shares_router

app = FastAPI(title="BhaktiGen Backend")
app.include_router(shares_router)
