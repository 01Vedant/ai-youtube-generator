"""
Tenancy middleware: resolve tenant_id from JWT, scope storage paths
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import logging
import jwt
import os

logger = logging.getLogger(__name__)

JWT_SECRET = os.getenv("JWT_SECRET", "change-in-production")
JWT_ALGORITHM = "HS256"


class TenancyMiddleware(BaseHTTPMiddleware):
    """
    Extract tenant_id from JWT and add to request scope.
    Scopes all storage operations to tenants/{tenant_id}/
    """

    async def dispatch(self, request: Request, call_next):
        tenant_id = None
        user_id = None

        # Try to extract from Authorization header
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                claims = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
                tenant_id = claims.get("tenant_id")
                user_id = claims.get("sub")
            except Exception as e:
                logger.debug(f"Failed to decode token: {e}")

        # Fallback: check refresh_token cookie
        if not tenant_id:
            refresh_token = request.cookies.get("refresh_token")
            if refresh_token:
                try:
                    claims = jwt.decode(refresh_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
                    # Note: refresh tokens don't have tenant_id, only user_id
                    user_id = claims.get("sub")
                    logger.debug(f"Refresh token used, user_id: {user_id}")
                except Exception as e:
                    logger.debug(f"Failed to decode refresh token: {e}")

        # Add to request state for downstream use
        request.state.tenant_id = tenant_id
        request.state.user_id = user_id

        response = await call_next(request)
        return response
