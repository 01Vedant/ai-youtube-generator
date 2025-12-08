import sys
import json
import uuid
import time
from typing import Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse


def jsonlog(obj: dict) -> None:
    try:
        sys.stdout.write(json.dumps(obj, separators=(",", ":")) + "\n")
    except Exception:
        # Avoid crashing on logging failure
        pass


def _client_ip(request: Request) -> str:
    xfwd = request.headers.get("x-forwarded-for")
    if xfwd:
        return xfwd.split(",")[0].strip()
    c = request.client
    return c.host if c else ""


async def _resolve_user_id(request: Request) -> Optional[str]:
    try:
        # Attempt to read decoded user from scope/state if present
        user = request.scope.get("user")
        if not user and hasattr(request, "state"):
            user = getattr(request.state, "user", None)
        # Fallback: parse bearer token if verify helper is importable
        if not user:
            try:
                from app.auth import verify_token  # type: ignore
                auth = request.headers.get("authorization")
                if auth and auth.lower().startswith("bearer "):
                    token = auth.split(" ", 1)[1]
                    uid = verify_token(token)
                    if uid:
                        return str(uid)
            except Exception:
                pass
        # Handle common user representations
        if user:
            uid = getattr(user, "id", None) or getattr(user, "user_id", None) or user.get("id") if isinstance(user, dict) else None
            if uid:
                return str(uid)
    except Exception:
        pass
    return None


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        start = time.monotonic()
        ip = _client_ip(request)
        user_id = await _resolve_user_id(request)
        try:
            response = await call_next(request)
            duration_ms = round((time.monotonic() - start) * 1000)
            jsonlog({
                "type": "access",
                "request_id": request_id,
                "ip": ip,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
                "user_id": user_id,
            })
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception as exc:
            duration_ms = round((time.monotonic() - start) * 1000)
            jsonlog({
                "type": "error",
                "request_id": request_id,
                "ip": ip,
                "method": request.method,
                "path": request.url.path,
                "duration_ms": duration_ms,
                "error_class": exc.__class__.__name__,
                "error_message": str(exc),
                "user_id": user_id,
            })
            # Re-raise to be handled by global exception handler without altering business logic
            raise


# Global uncaught exception handler returning structured 500 envelope
async def global_uncaught_exception_handler(request: Request, exc: Exception):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    jsonlog({
        "type": "uncaught",
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "error_class": exc.__class__.__name__,
        "error_message": str(exc),
    })
    body = {"error": {"code": "INTERNAL_ERROR", "message": "Unexpected error"}}
    return JSONResponse(status_code=500, content=body, headers={"X-Request-ID": request_id})
