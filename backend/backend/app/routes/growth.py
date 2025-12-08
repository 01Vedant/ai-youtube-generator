from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.auth import verify_token
from app.auth.security import get_current_user
from app.growth.service import get_share_progress, unlock_for_share
from app.db import get_conn, _utcnow_iso
from app.shares.util import new_share_id

router = APIRouter(prefix="/growth", tags=["growth"])
security = HTTPBearer()

@router.get('/share-progress/{share_id}')
async def share_progress(share_id: str, credentials: HTTPAuthorizationCredentials = Depends(security)):
    user_id = verify_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail='Unauthorized')
    return get_share_progress(share_id)

@router.post('/share-unlock/{share_id}')
async def share_unlock(share_id: str, credentials: HTTPAuthorizationCredentials = Depends(security)):
    user_id = verify_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail='Unauthorized')
    return unlock_for_share(user_id, share_id)

@router.post('/referral/create')
async def referral_create(user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail='Unauthorized')
    code = new_share_id(10)
    conn = get_conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO referral_codes(code, owner_user_id, created_at) VALUES(?,?,?)",
            (code, user['id'], _utcnow_iso()),
        )
        conn.commit()
    finally:
        conn.close()
    base = __import__('os').getenv('APP_BASE_URL') or ''
    url = f"{base}/?ref={code}" if base else f"/?ref={code}"
    return {"code": code, "url": url}

@router.post('/referral/claim')
async def referral_claim(payload: dict, user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail='Unauthorized')
    code = payload.get('code')
    if not code:
        raise HTTPException(status_code=400, detail='Missing code')
    conn = get_conn()
    try:
        # Insert referral unique per new user
        conn.execute(
            "INSERT OR IGNORE INTO referrals(code, new_user_id, created_at) VALUES(?,?,?)",
            (code, user['id'], _utcnow_iso()),
        )
        conn.commit()
        # Grant +1 renders to claimant
        import datetime
        day = datetime.datetime.utcnow().date().isoformat()
        cur = conn.execute("SELECT renders FROM usage_daily WHERE user_id=? AND day=?", (user['id'], day)).fetchone()
        if cur:
            conn.execute("UPDATE usage_daily SET renders=renders+1 WHERE user_id=? AND day=?", (user['id'], day))
        else:
            conn.execute("INSERT INTO usage_daily(user_id,day,renders,tts_sec) VALUES(?,?,?,0)", (user['id'], day, 1))
        # Optionally grant to owner if code exists
        own = conn.execute("SELECT owner_user_id FROM referral_codes WHERE code=?", (code,)).fetchone()
        if own:
            owner_id = own[0]
            cur2 = conn.execute("SELECT renders FROM usage_daily WHERE user_id=? AND day=?", (owner_id, day)).fetchone()
            if cur2:
                conn.execute("UPDATE usage_daily SET renders=renders+1 WHERE user_id=? AND day=?", (owner_id, day))
            else:
                conn.execute("INSERT INTO usage_daily(user_id,day,renders,tts_sec) VALUES(?,?,?,0)", (owner_id, day, 1))
        conn.commit()
    finally:
        conn.close()
    return {"ok": True}
