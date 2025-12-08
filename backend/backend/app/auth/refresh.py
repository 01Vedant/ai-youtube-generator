import os
import base64
import hmac
import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Tuple

from app.db import store_refresh, is_refresh_active


def _secret() -> bytes:
    return (os.getenv("JWT_SECRET", "dev-secret")).encode()


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _sign(data: bytes) -> str:
    return _b64url(hmac.new(_secret(), data, hashlib.sha256).digest())


def _encode(claims: dict) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    h = _b64url(json.dumps(header, separators=(",", ":")).encode())
    p = _b64url(json.dumps(claims, separators=(",", ":")).encode())
    s = _sign(f"{h}.{p}".encode())
    return f"{h}.{p}.{s}"


def _decode(token: str) -> dict:
    try:
        h, p, s = token.split(".")
        expected = _sign(f"{h}.{p}".encode())
        if not hmac.compare_digest(s, expected):
            raise ValueError("bad signature")
        # Pad base64 as needed
        def _pad(x: str) -> bytes:
            return base64.urlsafe_b64decode(x + "=" * (-len(x) % 4))
        payload = json.loads(_pad(p))
        return payload
    except Exception as e:
        raise ValueError("invalid token") from e


def new_jti() -> str:
    return _b64url(os.urandom(16))


def issue_access(user_id: str) -> Tuple[str, str]:
    exp_min = int(os.getenv("ACCESS_EXPIRES_MIN", "15"))
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=exp_min)
    claims = {"sub": user_id, "typ": "access", "exp": int(exp.timestamp()), "jti": new_jti()}
    tok = _encode(claims)
    return tok, exp.isoformat()


def issue_refresh(user_id: str) -> Tuple[str, str, str]:
    days = int(os.getenv("REFRESH_EXPIRES_DAYS", "14"))
    now = datetime.now(timezone.utc)
    exp = now + timedelta(days=days)
    jti = new_jti()
    claims = {"sub": user_id, "typ": "refresh", "exp": int(exp.timestamp()), "jti": jti}
    tok = _encode(claims)
    store_refresh(user_id, jti, now.isoformat())
    return tok, jti, exp.isoformat()


def verify_refresh(token: str) -> Tuple[str, str]:
    payload = _decode(token)
    if payload.get("typ") != "refresh":
        raise ValueError("wrong type")
    if int(payload.get("exp", 0)) < int(datetime.now(timezone.utc).timestamp()):
        raise ValueError("expired")
    sub = payload.get("sub")
    jti = payload.get("jti")
    if not sub or not jti:
        raise ValueError("invalid claims")
    if not is_refresh_active(jti):
        raise ValueError("revoked")
    return str(sub), str(jti)
