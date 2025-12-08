from __future__ import annotations
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from datetime import datetime
import uuid

from ..db import get_conn
from .security import hash_password, verify_password, create_access_token, create_refresh_token, decode, JWT_SECRET, get_current_user

router = APIRouter()


class RegisterReq(BaseModel):
    email: EmailStr
    password: str


class LoginReq(BaseModel):
    email: EmailStr
    password: str


class Tokens(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = 'bearer'


class RefreshReq(BaseModel):
    refresh_token: str


class MeRes(BaseModel):
    id: str
    email: EmailStr
    created_at: str
    plan_id: str
    entitlements: dict


@router.post('/register')
def register(req: RegisterReq):
    conn = get_conn()
    try:
        row = conn.execute('SELECT id FROM users WHERE email = ?', (req.email,)).fetchone()
        if row:
            raise HTTPException(status_code=409, detail='User already exists')
        user_id = uuid.uuid4().hex
        created_at = datetime.utcnow().isoformat() + 'Z'
        pw_hash = hash_password(req.password)
        conn.execute(
            'INSERT INTO users (id, email, password_hash, created_at, plan_id) VALUES (?, ?, ?, ?, ?)',
            (user_id, req.email, pw_hash, created_at, 'free')
        )
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@router.post('/login', response_model=Tokens)
def login(req: LoginReq):
    conn = get_conn()
    try:
        row = conn.execute('SELECT id, password_hash FROM users WHERE email = ?', (req.email,)).fetchone()
        if not row or not verify_password(req.password, row['password_hash']):
            raise HTTPException(status_code=401, detail='Invalid credentials')
        user_id = row['id']
        return Tokens(
            access_token=create_access_token(user_id),
            refresh_token=create_refresh_token(user_id),
        )
    finally:
        conn.close()


@router.post('/refresh', response_model=dict)
def refresh(req: RefreshReq):
    payload = decode(req.refresh_token, JWT_SECRET)
    if payload.get('type') != 'refresh':
        raise HTTPException(status_code=401, detail='Invalid token type')
    sub = payload.get('sub')
    if not sub:
        raise HTTPException(status_code=401, detail='Invalid token')
    return {"access_token": create_access_token(sub)}


from ..plans.entitlements import get_plan_spec


@router.get('/me', response_model=MeRes)
def me(current_user=Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail='Unauthorized')
    plan_id = current_user.get('plan_id', 'free')
    spec = get_plan_spec(plan_id)
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "created_at": current_user["created_at"],
        "plan_id": plan_id,
        "entitlements": {
            "features": sorted(list(spec["features"])),
            "quotas": spec["quotas"],
        },
    }
