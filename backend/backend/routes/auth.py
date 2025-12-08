"""
Auth routes: passwordless email magic-link JWT, sessions, tenants
"""

from fastapi import APIRouter, HTTPException, Depends, Response, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional
import os
import json
from datetime import datetime, timedelta
import uuid
import secrets
import logging
import redis

import jwt
from email_validator import validate_email, EmailNotValidError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])

# JWT Config
JWT_SECRET = os.getenv("JWT_SECRET", "change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))

# Email Config
MAGIC_LINK_FROM = os.getenv("MAGIC_LINK_FROM", "noreply@devotionalai.example.com")
MAGIC_LINK_TTL_MINUTES = int(os.getenv("MAGIC_LINK_TTL_MINUTES", "15"))

# Redis for magic link tokens
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    redis_client.ping()
except Exception as e:
    logger.warning(f"Redis unavailable: {e}. Magic links will use in-memory store.")
    redis_client = None

# In-memory fallback for development
_magic_link_store = {}


class MagicLinkRequest(BaseModel):
    email: str


class MagicLinkVerify(BaseModel):
    token: str


class RefreshRequest(BaseModel):
    refresh_token: str


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str]
    token_type: str = "bearer"
    expires_in: int


def create_access_token(user_id: str, tenant_id: str, email: str, role: str = "creator") -> str:
    """Create JWT access token."""
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "email": email,
        "role": role,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    """Create long-lived refresh token (30 days)."""
    payload = {
        "sub": user_id,
        "type": "refresh",
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(days=30),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> dict:
    """Verify JWT and return claims. Raises if invalid."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())) -> dict:
    """Dependency to extract current user from request."""
    claims = verify_token(credentials.credentials)
    return claims


@router.post("/magic-link/request")
async def request_magic_link(req: MagicLinkRequest):
    """
    Request magic link for passwordless login.
    In production, send email via SendGrid/AWS SES.
    """
    try:
        validated = validate_email(req.email)
        email = validated.email
    except EmailNotValidError as e:
        raise HTTPException(status_code=400, detail=f"Invalid email: {str(e)}")

    # Check if user exists or create new
    # TODO: implement user creation/lookup
    user_id = f"user_{uuid.uuid4().hex[:16]}"  # Placeholder
    tenant_id = f"tenant_{uuid.uuid4().hex[:16]}"  # Placeholder

    # Create magic link token (one-time use)
    magic_token = secrets.token_urlsafe(32)
    token_data = {
        "user_id": user_id,
        "tenant_id": tenant_id,
        "email": email,
        "role": "creator",
        "created_at": datetime.utcnow().isoformat(),
    }

    if redis_client:
        redis_client.setex(
            f"magic_link:{magic_token}",
            MAGIC_LINK_TTL_MINUTES * 60,
            json.dumps(token_data),
        )
    else:
        _magic_link_store[magic_token] = {
            **token_data,
            "expires_at": datetime.utcnow() + timedelta(minutes=MAGIC_LINK_TTL_MINUTES),
        }

    # TODO: Send email with link: https://app.example.com/login?token={magic_token}
    magic_link = f"https://app.example.com/login?token={magic_token}"
    logger.info(f"Magic link for {email}: {magic_link}")

    return {
        "success": True,
        "message": f"Magic link sent to {email}",
        # In dev, return link directly
        "magic_link": magic_link if os.getenv("DEBUG", "false").lower() == "true" else None,
    }


@router.post("/magic-link/verify")
async def verify_magic_link(req: MagicLinkVerify, response: Response) -> AuthResponse:
    """
    Verify magic link token and return JWT + refresh token.
    """
    token_data = None

    if redis_client:
        raw = redis_client.get(f"magic_link:{req.token}")
        if raw:
            token_data = json.loads(raw)
            redis_client.delete(f"magic_link:{req.token}")  # One-time use
    else:
        if req.token in _magic_link_store:
            stored = _magic_link_store.pop(req.token)
            if stored["expires_at"] > datetime.utcnow():
                token_data = {k: v for k, v in stored.items() if k != "expires_at"}

    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid or expired magic link")

    user_id = token_data["user_id"]
    tenant_id = token_data["tenant_id"]
    email = token_data["email"]
    role = token_data.get("role", "creator")

    # Create tokens
    access_token = create_access_token(user_id, tenant_id, email, role)
    refresh_token = create_refresh_token(user_id)

    # Set httpOnly cookie for refresh token
    response.set_cookie(
        "refresh_token",
        refresh_token,
        httponly=True,
        secure=os.getenv("SECURE_COOKIES", "true").lower() == "true",
        samesite="lax",
        max_age=30 * 24 * 3600,  # 30 days
    )

    logger.info(f"User {user_id} authenticated via magic link")

    return AuthResponse(
        access_token=access_token,
        refresh_token=None,  # Returned as httpOnly cookie
        expires_in=JWT_EXPIRE_HOURS * 3600,
    )


@router.post("/refresh")
async def refresh_access_token(req: RefreshRequest, response: Response) -> AuthResponse:
    """
    Exchange refresh token for new access token.
    """
    claims = verify_token(req.refresh_token)
    if claims.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user_id = claims["sub"]

    # TODO: Fetch user to get tenant_id, email, role from DB
    # For now, mock:
    tenant_id = f"tenant_{uuid.uuid4().hex[:16]}"
    email = "user@example.com"
    role = "creator"

    access_token = create_access_token(user_id, tenant_id, email, role)
    new_refresh_token = create_refresh_token(user_id)

    response.set_cookie(
        "refresh_token",
        new_refresh_token,
        httponly=True,
        secure=os.getenv("SECURE_COOKIES", "true").lower() == "true",
        samesite="lax",
        max_age=30 * 24 * 3600,
    )

    return AuthResponse(
        access_token=access_token,
        refresh_token=None,
        expires_in=JWT_EXPIRE_HOURS * 3600,
    )


@router.get("/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """
    Get current user info from JWT claims.
    """
    return {
        "user_id": current_user.get("sub"),
        "tenant_id": current_user.get("tenant_id"),
        "email": current_user.get("email"),
        "role": current_user.get("role", "creator"),
    }


@router.post("/logout")
async def logout(response: Response):
    """
    Logout: clear refresh token cookie.
    """
    response.delete_cookie("refresh_token", secure=True, httponly=True)
    return {"success": True, "message": "Logged out"}
