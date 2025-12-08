import os
from fastapi import APIRouter

router = APIRouter()

@router.get("/debug/echo")
def debug_echo():
    return {"ok": True, "env": os.getenv("APP_ENV", "dev")}
