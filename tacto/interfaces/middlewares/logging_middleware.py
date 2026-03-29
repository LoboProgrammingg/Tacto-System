"""
Logging Middleware — Interface layer.

Logs every HTTP request with method, path, status code, duration and client IP.
Health check endpoints are logged at DEBUG level to avoid noise.
"""

import time

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger()

_HEALTH_PATHS = frozenset({"/health", "/ready"})


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = int((time.perf_counter() - start) * 1000)

        log = logger.bind(
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
            client=request.client.host if request.client else None,
        )

        if request.url.path in _HEALTH_PATHS:
            log.debug("http_request")
        else:
            log.info("http_request")

        return response
