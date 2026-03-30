"""
HTTP Middleware configuration — Interface layer.

Registers all middlewares on the FastAPI application.
Order (outermost → innermost → app):
  CORS → Logging → RateLimit → Auth → App

To add a new middleware: create its module in this package,
then add app.add_middleware() here BEFORE the existing ones.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from tacto.infrastructure.config.config import get_settings
from tacto.interfaces.middlewares.auth_middleware import AuthMiddleware
from tacto.interfaces.middlewares.logging_middleware import LoggingMiddleware
from tacto.interfaces.middlewares.rate_limit_middleware import RateLimitMiddleware


def setup_middlewares(app: FastAPI) -> None:
    """Register all HTTP middlewares on the FastAPI application.

    Starlette wraps middlewares in registration order (last = outermost).
    Registration sequence below produces: CORS → Logging → RateLimit → Auth → App.
    """
    settings = get_settings()

    # 1. Auth — innermost, only authenticated requests reach the app
    app.add_middleware(AuthMiddleware)

    # 2. Rate limit — per-IP throttling using Redis
    app.add_middleware(RateLimitMiddleware)

    # 3. Logging — structured request/response logs
    app.add_middleware(LoggingMiddleware)

    # 4. CORS — outermost, handles preflight before any other check
    # Priority: CORS_ORIGINS > DEBUG mode default
    cors_origins = _get_cors_origins(settings)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def _get_cors_origins(settings) -> list[str]:
    """
    Determine CORS allowed origins.

    Priority:
    1. CORS_ORIGINS env var (comma-separated list)
    2. DEBUG=true → ["*"] (allow all)
    3. DEBUG=false + no CORS_ORIGINS → [] (deny all)
    """
    if settings.app.cors_origins:
        # Parse comma-separated origins, strip whitespace
        origins = [o.strip() for o in settings.app.cors_origins.split(",") if o.strip()]
        return origins

    # Fallback to debug-based default
    return ["*"] if settings.app.debug else []
