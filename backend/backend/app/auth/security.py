from __future__ import annotations
import os
import hmac
import json
import time
import base64
import hashlib
import secrets
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from ..db import get_conn

ALGO = 'HS256'
JWT_SECRET = os.getenv('JWT_SECRET', 'dev-secret-change-me')
ACCESS_EXPIRES_MIN = int(os.getenv('ACCESS_EXPIRES_MIN', '30'))
REFRESH_EXPIRES_DAYS = int(os.getenv('REFRESH_EXPIRES_DAYS', '30'))


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')


def b64urldecode(data: str) -> bytes:
    padding = '=' * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def sign(header: Dict[str, Any], payload: Dict[str, Any], secret: str) -> str:
    header_b64 = b64url(json.dumps(header, separators=(',', ':')).encode('utf-8'))
    payload_b64 = b64url(json.dumps(payload, separators=(',', ':')).encode('utf-8'))
    msg = f"{header_b64}.{payload_b64}".encode('utf-8')
    sig = hmac.new(secret.encode('utf-8'), msg, hashlib.sha256).digest()
    sig_b64 = b64url(sig)
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode(token: str, secret: str) -> Dict[str, Any]:
    try:
        header_b64, payload_b64, sig_b64 = token.split('.')
    except ValueError:
        raise HTTPException(status_code=401, detail='Invalid token')
    msg = f"{header_b64}.{payload_b64}".encode('utf-8')
    expected = hmac.new(secret.encode('utf-8'), msg, hashlib.sha256).digest()
    if not hmac.compare_digest(expected, b64urldecode(sig_b64)):
        raise HTTPException(status_code=401, detail='Invalid signature')
    payload = json.loads(b64urldecode(payload_b64))
    if 'exp' in payload and int(time.time()) >= int(payload['exp']):
        raise HTTPException(status_code=401, detail='Token expired')
    return payload


def hash_password(pw: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac('sha256', pw.encode('utf-8'), salt, 200_000)
    return b64url(salt) + '.' + b64url(dk)


def verify_password(pw: str, hashed: str) -> bool:
    try:
        salt_b64, dk_b64 = hashed.split('.')
        salt = b64urldecode(salt_b64)
        expected = b64urldecode(dk_b64)
    except Exception:
        return False
    dk = hashlib.pbkdf2_hmac('sha256', pw.encode('utf-8'), salt, 200_000)
    return hmac.compare_digest(dk, expected)


def create_access_token(sub: str, expires_minutes: int = ACCESS_EXPIRES_MIN) -> str:
    now = int(time.time())
    header = {"alg": ALGO, "typ": "JWT"}
    payload = {"sub": sub, "type": "access", "iat": now, "exp": now + expires_minutes * 60}
    return sign(header, payload, JWT_SECRET)


def create_refresh_token(sub: str, expires_days: int = REFRESH_EXPIRES_DAYS) -> str:
    now = int(time.time())
    header = {"alg": ALGO, "typ": "JWT"}
    payload = {"sub": sub, "type": "refresh", "iat": now, "exp": now + expires_days * 86400}
    return sign(header, payload, JWT_SECRET)


http_bearer = HTTPBearer(auto_error=False)


def get_current_user(creds: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer)) -> Optional[dict]:
    if not creds:
        return None
    token = creds.credentials
    payload = decode(token, JWT_SECRET)
    if payload.get('type') != 'access':
        raise HTTPException(status_code=401, detail='Invalid token type')
    user_id = payload.get('sub')
    if not user_id:
        raise HTTPException(status_code=401, detail='Invalid token')
    # Fetch user
    conn = get_conn()
    try:
        row = conn.execute('SELECT id, email, created_at, plan_id FROM users WHERE id = ?', (user_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=401, detail='User not found')
        return dict(row)
    finally:
        conn.close()
