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
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.app.debug else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
