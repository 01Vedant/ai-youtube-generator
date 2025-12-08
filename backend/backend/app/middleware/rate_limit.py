import os
import time
from typing import Dict, Tuple, Optional

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

# In-memory fixed-window counters: { key: (window_start_sec, count) }
_RL_STORE: Dict[str, Tuple[int, int]] = {}

def _now_sec() -> int:
    return int(time.time())

def client_ip(request: Request) -> Optional[str]:
    xfwd = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
    if xfwd:
        # take first IP
        return xfwd.split(",")[0].strip() or None
    return request.client.host if request.client else None

def extract_user_id(request: Request) -> Optional[str]:
    # Lightweight extraction: read bearer token and defer to security util if available
    auth = request.headers.get("Authorization") or request.headers.get("authorization")
    if not auth or not auth.lower().startswith("bearer "):
        return None
    # Import lazily to avoid circular deps
    try:
        from app.auth.security import decode_access_token  # type: ignore
        token = auth.split(" ", 1)[1]
        payload = decode_access_token(token)
        uid = payload.get("user_id") or payload.get("sub")
        return str(uid) if uid else None
    except Exception:
        return None

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.window_sec = int(os.getenv("RL_WINDOW_SEC", "600"))
        # Limits
        self.limits = {
            ("POST", "/auth/login"): ("login", "ip", int(os.getenv("RL_LOGIN_PER_IP", "20"))),
            ("POST", "/auth/register"): ("register", "ip", int(os.getenv("RL_REGISTER_PER_IP", "10"))),
            ("POST", "/render"): ("render", "user", int(os.getenv("RL_RENDER_PER_USER", "30"))),
            ("POST", "/shares"): ("share", "user", int(os.getenv("RL_SHARE_PER_USER", "50"))),
            ("GET", "/tts/preview"): ("tts", "user", int(os.getenv("RL_TTS_CALLS_PER_USER", "60"))),
        }

    def match(self, request: Request) -> Optional[Tuple[str, str, int]]:
        method = request.method.upper()
        path = request.url.path
        for (m, prefix), cfg in self.limits.items():
            if method == m and path.startswith(prefix):
                return cfg  # (metric, scope, limit)
        return None

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        cfg = self.match(request)
        if not cfg:
            return await call_next(request)

        metric, scope, limit = cfg
        now = _now_sec()
        window = (now // self.window_sec) * self.window_sec

        # Determine key
        key_id: Optional[str] = None
        if scope == "ip":
            key_id = client_ip(request)
        else:
            key_id = extract_user_id(request)

        # Skip RL when user-id required but missing (anonymous)
        if key_id is None:
            return await call_next(request)

        store_key = f"{scope}:{key_id}:{metric}"
        prev = _RL_STORE.get(store_key)
        if not prev or prev[0] != window:
            # Reset window
            _RL_STORE[store_key] = (window, 0)
            prev = _RL_STORE[store_key]

        used = prev[1] + 1
        _RL_STORE[store_key] = (window, used)

        if used > limit:
            reset_at = window + self.window_sec
            body = {
                "error": {
                    "code": "QUOTA_EXCEEDED",
                    "metric": metric,
                    "scope": scope,
                    "limit": limit,
                    "used": used,
                    "reset_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(reset_at)),
                }
            }
            return JSONResponse(status_code=429, content=body)

        return await call_next(request)
