from fastapi import HTTPException
from app.flags import is_enabled
import os

def require_admin(user: dict) -> None:
    roles = user.get('roles', []) or []
    email = user.get('email')
    admin_emails = [e.strip() for e in os.getenv('ADMIN_EMAILS', '').split(',') if e.strip()]
    if ('admin' in roles) or (email and email in admin_emails):
        return
    raise HTTPException(status_code=403, detail='Admin required')

def require_feature(key: str):
    if not is_enabled(key):
        raise HTTPException(status_code=403, detail={"error": {"code": "FEATURE_DISABLED", "feature": key}})
from fastapi import HTTPException, status


def forbid():
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
