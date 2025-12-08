import os
import math
from datetime import datetime, timezone
from typing import Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse


ALLOWED_PREFIXES = ("/health", "/version", "/metrics", "/billing/webhook")


def _env_flag(name: str, default: str = "0") -> str:
    return os.getenv(name, default)


def _parse_until(until_str: Optional[str]) -> Optional[datetime]:
    if not until_str:
        return None
    try:
        # Expect ISO8601; allow 'Z' suffix
        if until_str.endswith("Z"):
            until_str = until_str[:-1] + "+00:00"
        return datetime.fromisoformat(until_str).astimezone(timezone.utc)
    except Exception:
        return None


def _retry_after_seconds(until: Optional[datetime]) -> int:
    if not until:
        return 300
    now = datetime.now(timezone.utc)
    diff = (until - now).total_seconds()
    sec = math.ceil(diff)
    return sec if sec > 0 else 300


def _client_ip(request: Request) -> str:
    xfwd = request.headers.get("x-forwarded-for")
    if xfwd:
        return xfwd.split(",")[0].strip()
    client = request.client
    return client.host if client else ""


class MaintenanceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        # Bypass for allowed prefixes
        path = request.url.path
        if path.startswith(ALLOWED_PREFIXES):
            return await call_next(request)

        mode = _env_flag("MAINTENANCE_MODE", "0")
        if mode != "1":
            return await call_next(request)

        # Allowlist IPs
        allow_ips = _env_flag("MAINTENANCE_ALLOWLIST_IPS", "").strip()
        if allow_ips:
            allow = {ip.strip() for ip in allow_ips.split(",") if ip.strip()}
            if _client_ip(request) in allow:
                return await call_next(request)

        # Admin bypass if enabled
        allow_admins = _env_flag("MAINTENANCE_ALLOW_ADMINS", "1")
        if allow_admins == "1":
            try:
                # Use existing auth dependency/helper if available via scope
                user = request.scope.get("user")
                # Fallback: decode token if your app supports; else treat missing as anon
                if not user:
                    # Attempt to get from state/session if provided elsewhere
                    user = request.state.__dict__.get("user") if hasattr(request, "state") else None
                role = getattr(user, "role", None) if user else None
                if role == "admin":
                    return await call_next(request)
            except Exception:
                # On any failure, treat as anonymous (no bypass)
                pass

        until_str = _env_flag("MAINTENANCE_UNTIL", "")
        until_dt = _parse_until(until_str)
        message = _env_flag("MAINTENANCE_MESSAGE", "We’re doing scheduled maintenance.")

        body = {
            "error": {
                "code": "MAINTENANCE",
                "message": message,
                "until": until_dt.isoformat() if until_dt else None,
            }
        }
        headers = {"Retry-After": str(_retry_after_seconds(until_dt)), "Content-Type": "application/json"}
        return JSONResponse(status_code=503, content=body, headers=headers)
import os
import math
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


def _parse_until(val: Optional[str]) -> Optional[datetime]:
    if not val:
        return None
    try:
        # Expect ISO8601; ensure timezone-aware
        dt = datetime.fromisoformat(val)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _client_ip(request: Request) -> str:
    xfwd = request.headers.get("x-forwarded-for")
    if xfwd:
        return xfwd.split(",")[0].strip()
    client = request.client
    return client.host if client else ""


def _path_is_bypass(path: str) -> bool:
    return (
        path.startswith("/health")
        or path.startswith("/version")
        or path.startswith("/metrics")
        or path.startswith("/billing/webhook")
    )


async def _user_role(request: Request) -> Optional[str]:
    # Best-effort: use existing auth dependency if available
    try:
        verifier = request.app.state.get("auth_verifier")  # type: ignore[attr-defined]
        if verifier:
            user = await verifier.get_user(request)
            return getattr(user, "role", None)
    except Exception:
        pass
    return None


class MaintenanceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        mode = _env("MAINTENANCE_MODE", "0")
        if mode != "1":
            return await call_next(request)

        path = request.url.path
        if _path_is_bypass(path):
            return await call_next(request)

        # Admin bypass
        allow_admins = _env("MAINTENANCE_ALLOW_ADMINS", "1")
        if allow_admins == "1":
            role = await _user_role(request)
            if role == "admin":
                return await call_next(request)

        # IP allowlist
        allowlist_raw = _env("MAINTENANCE_ALLOWLIST_IPS", "").strip()
        allowlist: List[str] = [s.strip() for s in allowlist_raw.split(",") if s.strip()]
        if allowlist:
            ip = _client_ip(request)
            if ip in allowlist:
                return await call_next(request)

        # Block with 503 envelope
        message = _env("MAINTENANCE_MESSAGE", "We’re doing scheduled maintenance.")
        until_str = _env("MAINTENANCE_UNTIL", "").strip()
        until_dt = _parse_until(until_str)

        retry_after = 300
        if until_dt:
            now = datetime.now(timezone.utc)
            delta = (until_dt - now).total_seconds()
            if delta > 0:
                retry_after = int(math.ceil(delta))

        body = {
            "error": {
                "code": "MAINTENANCE",
                "message": message,
                "until": until_dt.isoformat() if until_dt else None,
            }
        }

        return JSONResponse(status_code=503, content=body, headers={"Retry-After": str(retry_after)})
