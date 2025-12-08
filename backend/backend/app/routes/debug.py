import fastapi

debug_router = fastapi.APIRouter()

@debug_router.get("/debug/echo")
def debug_echo_get(q: str | None = None):
    return {"echo": q}

@debug_router.post("/debug/echo")
def debug_echo_post(payload: dict):
    return {"echo": payload}
