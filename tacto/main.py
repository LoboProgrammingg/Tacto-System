"""
TactoFlow - Main Application Entry Point.

FastAPI application with proper lifecycle management and dependency injection.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import os

import structlog
from fastapi import FastAPI

from tacto.config import Settings, get_settings
from tacto.interfaces.middlewares.middleware import setup_middlewares
from tacto.infrastructure.database.connection import close_database, get_engine
from tacto.infrastructure.redis.redis_client import RedisClient
from tacto.interfaces.http.routes import router as api_router


logger = structlog.get_logger()


def _validate_security_settings(settings: Settings) -> None:
    """
    Validate critical security settings at startup.

    Raises RuntimeError if insecure defaults are used in production.
    """
    if settings.app.debug:
        # In debug mode, allow insecure defaults with warning
        if settings.app.secret_key == "change-me-in-production":
            logger.warning(
                "Using default SECRET_KEY in debug mode. "
                "Set SECRET_KEY env var before deploying to production."
            )
        return

    # Production mode (DEBUG=false) — enforce secure configuration
    if settings.app.secret_key == "change-me-in-production":
        raise RuntimeError(
            "SECURITY ERROR: Cannot start in production mode with default SECRET_KEY. "
            "Set SECRET_KEY environment variable to a secure random value. "
            "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
        )

    logger.info("Security settings validated")


def _configure_langsmith(settings: Settings) -> None:
    """
    Configure LangSmith tracing at startup.

    Sets both LANGSMITH_* and LANGCHAIN_* env vars so that langchain-core
    picks them up regardless of which naming convention it checks first.
    """
    ls = settings.langsmith
    if not ls.tracing or not ls.api_key:
        logger.info("LangSmith tracing disabled")
        return

    # langchain-core 1.x reads LANGCHAIN_* vars; langsmith SDK reads LANGSMITH_*
    # Set both to guarantee compatibility across versions
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = ls.api_key
    os.environ["LANGCHAIN_PROJECT"] = ls.project
    os.environ["LANGCHAIN_ENDPOINT"] = ls.endpoint
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_API_KEY"] = ls.api_key
    os.environ["LANGSMITH_PROJECT"] = ls.project
    os.environ["LANGSMITH_ENDPOINT"] = ls.endpoint

    logger.info("LangSmith tracing enabled", project=ls.project, endpoint=ls.endpoint)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Handles startup and shutdown events for:
    - Security validation
    - Database connections
    - Redis connections
    - External API clients
    """
    settings = get_settings()
    logger.info("Starting TactoFlow", version=settings.app.version)

    # Validate security settings FIRST — fail fast if misconfigured
    _validate_security_settings(settings)

    _configure_langsmith(settings)

    redis_client = RedisClient()
    redis_result = await redis_client.connect()

    if redis_result.is_success():
        logger.info("Redis connected")
        app.state.redis = redis_client
    else:
        logger.warning("Redis connection failed, continuing without cache")
        app.state.redis = None

    get_engine()
    logger.info("Database engine initialized")

    app.state.settings = settings

    yield

    logger.info("Shutting down TactoFlow")

    if app.state.redis:
        await app.state.redis.disconnect()
        logger.info("Redis disconnected")

    await close_database()
    logger.info("Database connections closed")


def create_app() -> FastAPI:
    """
    Application factory.

    Creates and configures the FastAPI application.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.app.name,
        version=settings.app.version,
        description="Restaurant Automation System with AI-powered WhatsApp integration",
        docs_url="/docs" if settings.app.debug else None,
        redoc_url="/redoc" if settings.app.debug else None,
        lifespan=lifespan,
    )

    setup_middlewares(app)

    @app.get("/health", tags=["Health"])
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy", "version": settings.app.version}

    @app.get("/ready", tags=["Health"])
    async def readiness_check() -> dict[str, str]:
        """Readiness check endpoint."""
        checks = {"database": "ok", "redis": "ok"}

        redis = getattr(app.state, "redis", None)
        if redis is None or not redis.is_connected:
            checks["redis"] = "disconnected"

        return {"status": "ready", "checks": checks}

    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()

    uvicorn.run(
        "tacto.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.app.debug,
        log_level="debug" if settings.app.debug else "info",
    )
