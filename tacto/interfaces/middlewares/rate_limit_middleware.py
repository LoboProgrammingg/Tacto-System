"""
Rate Limit Middleware — Interface layer.

Fixed-window rate limiting per client IP using Redis.
Falls back to allow-all when Redis is unavailable (fail-open for availability).
Rate limit: configurable via settings.app.rate_limit_rpm (0 = disabled).
"""

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from tacto.infrastructure.config.config import get_settings

logger = structlog.get_logger()

_EXEMPT_PATHS = frozenset({
    "/health",
    "/ready",
    "/docs",
    "/redoc",
    "/openapi.json",
})


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        settings = get_settings()
        rpm = settings.app.rate_limit_rpm

        if rpm == 0 or request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        redis = getattr(request.app.state, "redis", None)
        if redis is None or not redis.is_connected:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        key = f"tacto:ratelimit:{client_ip}"

        count_result = await redis.incr(key)
        if not count_result.is_success():
            return await call_next(request)

        count = count_result.value
        if count == 1:
            await redis.expire(key, 60)

        if count > rpm:
            logger.warning("rate_limit_exceeded", client=client_ip, path=request.url.path, count=count)
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Try again in a minute."},
                headers={"Retry-After": "60"},
            )

        return await call_next(request)
