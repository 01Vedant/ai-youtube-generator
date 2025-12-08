"""
Middleware for rate limiting, idempotency, and request tracking.
"""
import logging
import time
import uuid
from typing import Dict, Tuple
from collections import defaultdict
from datetime import datetime, timedelta
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limit by IP address or user_id.
    Tracks requests in last N minutes; returns 429 if exceeded.
    """

    def __init__(self, app, rate_limit_per_min: int = 10):
        super().__init__(app)
        self.rate_limit_per_min = rate_limit_per_min
        self.request_log: Dict[str, list] = defaultdict(list)  # key -> [timestamp, ...]

    async def dispatch(self, request: Request, call_next):
        # Rate limit only POST /render
        if request.method == "POST" and "/render" in request.url.path:
            key = self._get_rate_limit_key(request)
            now = time.time()
            cutoff = now - 60  # Last minute

            # Prune old entries
            self.request_log[key] = [ts for ts in self.request_log[key] if ts > cutoff]

            # Check limit
            if len(self.request_log[key]) >= self.rate_limit_per_min:
                logger.warning("Rate limit exceeded for %s", key)
                return JSONResponse(
                    {
                        "detail": f"Rate limit: max {self.rate_limit_per_min} requests per minute",
                        "retry_after_seconds": 60,
                    },
                    status_code=429,
                )

            # Record request
            self.request_log[key].append(now)

        response = await call_next(request)
        return response

    def _get_rate_limit_key(self, request: Request) -> str:
        """Extract rate limit key from request (user_id > IP)."""
        # TODO: Extract user_id from JWT token if available
        return request.client.host if request.client else "unknown"


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """
    Idempotency by Idempotency-Key header.
    Caches response for POST requests; returns same on retry.
    """

    def __init__(self, app):
        super().__init__(app)
        self.cache: Dict[str, Tuple[dict, int]] = {}  # key -> (response_data, status_code)

    async def dispatch(self, request: Request, call_next):
        # Only cache POST /render
        if request.method == "POST" and request.url.path == "/render":
            idempotency_key = request.headers.get("Idempotency-Key")
            
            if idempotency_key:
                # Check cache
                if idempotency_key in self.cache:
                    cached_response, status_code = self.cache[idempotency_key]
                    logger.info("Idempotency cache hit: %s", idempotency_key)
                    return JSONResponse(cached_response, status_code=status_code)

        response = await call_next(request)

        # Cache successful responses
        if request.method == "POST" and request.url.path == "/render":
            idempotency_key = request.headers.get("Idempotency-Key")
            if idempotency_key and response.status_code in [200, 201]:
                try:
                    # Parse response body (this is tricky with streaming; simplified)
                    import json
                    body = b""
                    async for chunk in response.body_iterator:
                        body += chunk
                    
                    data = json.loads(body)
                    self.cache[idempotency_key] = (data, response.status_code)
                    logger.info("Idempotency cache stored: %s", idempotency_key)
                    
                    # Return cached response with same body
                    return JSONResponse(data, status_code=response.status_code)
                except Exception as e:
                    logger.error("Idempotency cache store failed: %s", e)

        return response


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """
    Add request_id and job_id to all requests for correlation logging.
    """

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.scope["request_id"] = request_id
        
        # Extract job_id from URL if present
        if "/render/" in request.url.path:
            parts = request.url.path.split("/render/")
            if len(parts) > 1:
                job_id = parts[1].split("/")[0]
                request.scope["job_id"] = job_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Simple API key auth via x-api-key header.
    Routes requiring auth: POST /render, DELETE /render/{job_id}/cancel
    Skips unauthenticated endpoints: /health, /healthz, /readyz, /metrics
    """

    def __init__(self, app, api_key_admin: str = "", api_key_creator: str = ""):
        super().__init__(app)
        self.api_key_admin = api_key_admin
        self.api_key_creator = api_key_creator

    async def dispatch(self, request: Request, call_next):
        # Skip auth for public endpoints
        public_paths = ["/health", "/healthz", "/readyz", "/metrics", "/docs", "/openapi.json"]
        if any(request.url.path.startswith(p) for p in public_paths):
            return await call_next(request)

        # Skip OPTIONS (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        # Require API key for protected endpoints
        if request.method in ["POST", "DELETE"] or "/render/" in request.url.path:
            api_key = request.headers.get("X-API-Key", "").strip()
            
            if not api_key:
                logger.warning("Missing API key for %s %s", request.method, request.url.path)
                return JSONResponse(
                    {"detail": "Missing X-API-Key header"},
                    status_code=401,
                )

            # Validate key
            valid_keys = [self.api_key_admin, self.api_key_creator]
            if api_key not in valid_keys or not api_key:
                logger.warning("Invalid API key for %s %s", request.method, request.url.path)
                return JSONResponse(
                    {"detail": "Invalid X-API-Key"},
                    status_code=403,
                )

            # Attach role to request
            request.scope["api_key_role"] = "admin" if api_key == self.api_key_admin else "creator"

        return await call_next(request)
