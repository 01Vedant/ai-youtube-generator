from __future__ import annotations
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from starlette.responses import Response
import os

CSP_DEFAULT = (
    "default-src 'self'; "
    "img-src 'self' data: blob:; "
    "media-src 'self' data: blob:; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "connect-src 'self' https://api.stripe.com https://js.stripe.com; "
    "frame-src https://js.stripe.com;"
)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.is_prod = os.getenv('APP_ENV', 'prod') == 'prod'

    async def dispatch(self, request, call_next):
        response: Response = await call_next(request)
        if self.is_prod:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
            # Skip CSP for metrics endpoints to avoid issues
            path = request.url.path
            if not path.startswith('/metrics'):
                response.headers['Content-Security-Policy'] = os.getenv('CSP', CSP_DEFAULT)
        return response
