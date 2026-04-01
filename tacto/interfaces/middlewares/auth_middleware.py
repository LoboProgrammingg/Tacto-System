"""
Auth Middleware — Interface layer.

API Key authentication via X-API-Key header.
Disabled when settings.app.api_key is empty (default for local dev).
Webhook paths are exempt — they use their own HMAC validation.
"""

import secrets

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from tacto.infrastructure.config.config import get_settings

logger = structlog.get_logger()

_PUBLIC_PATHS = frozenset({
    "/health",
    "/ready",
    "/docs",
    "/redoc",
    "/openapi.json",
})

_WEBHOOK_PREFIX = "/api/v1/webhook"


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        settings = get_settings()
        expected_key = settings.app.api_key

        if not expected_key:
            return await call_next(request)

        path = request.url.path
        if path in _PUBLIC_PATHS or path.startswith(_WEBHOOK_PREFIX):
            return await call_next(request)

        provided_key = request.headers.get("X-API-Key", "")
        if not secrets.compare_digest(provided_key, expected_key):
            logger.warning("auth_failed", path=path, client=request.client.host if request.client else None)
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing API key."},
                headers={"WWW-Authenticate": "ApiKey"},
            )

        return await call_next(request)
