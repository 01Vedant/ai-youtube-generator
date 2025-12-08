from __future__ import annotations
from datetime import datetime, timedelta
from passlib.context import CryptContext
import jwt

# Minimal re-exports for legacy imports in app.main
try:
	from app.config import settings
except Exception:  # pragma: no cover
	class _S:  # fallback for tests
		SECRET_KEY = "dev-secret"
	settings = _S()

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
	return _pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
	try:
		return _pwd_context.verify(plain_password, hashed_password)
	except Exception:
		return False

def create_token(user_id: str, expires_hours: int = 24) -> str:
	expire = datetime.utcnow() + timedelta(hours=expires_hours)
	to_encode = {"sub": user_id, "exp": expire, "iat": datetime.utcnow()}
	return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")

def verify_token(token: str) -> str | None:
	try:
		payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
		user_id: str | None = payload.get("sub")
		return user_id
	except Exception:
		return None
