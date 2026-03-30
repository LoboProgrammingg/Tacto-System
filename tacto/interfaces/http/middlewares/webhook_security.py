"""
Webhook Security Middleware.

Provides HMAC signature validation for webhook endpoints.
"""

import hashlib
import hmac
from typing import Optional

import structlog
from fastapi import HTTPException, Request, status

from tacto.config.settings import get_settings


logger = structlog.get_logger()


async def validate_webhook_signature(request: Request) -> bool:
    """
    Validate HMAC-SHA256 signature of webhook request.

    The Join API sends webhook requests with a signature header:
    - X-Hub-Signature-256: sha256=<hex_digest>

    The signature is computed as: HMAC-SHA256(secret, raw_body)

    Args:
        request: FastAPI request object

    Returns:
        True if signature is valid or HMAC is disabled

    Raises:
        HTTPException: If signature is missing or invalid
    """
    settings = get_settings()

    # If HMAC is not configured, allow all requests (backward compatibility)
    if not settings.join.hmac_enabled:
        return True

    # Get the signature from header
    signature_header: Optional[str] = request.headers.get("X-Hub-Signature-256")

    if not signature_header:
        logger.warning("webhook_signature_missing", path=str(request.url.path))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Hub-Signature-256 header",
        )

    # Parse the signature (format: "sha256=<hex_digest>")
    if not signature_header.startswith("sha256="):
        logger.warning("webhook_signature_invalid_format", header=signature_header[:20])
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature format",
        )

    expected_signature = signature_header[7:]  # Remove "sha256=" prefix

    # Get raw body bytes
    body_bytes = await request.body()

    # Compute expected HMAC
    computed_signature = hmac.new(
        key=settings.join.webhook_secret.encode("utf-8"),
        msg=body_bytes,
        digestmod=hashlib.sha256,
    ).hexdigest()

    # Constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(computed_signature, expected_signature):
        logger.warning(
            "webhook_signature_mismatch",
            path=str(request.url.path),
            computed=computed_signature[:16] + "...",
            received=expected_signature[:16] + "...",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature",
        )

    logger.debug("webhook_signature_valid")
    return True


def generate_webhook_signature(body: bytes, secret: str) -> str:
    """
    Generate HMAC-SHA256 signature for webhook payload.

    Useful for testing or when sending webhooks to external services.

    Args:
        body: Raw request body bytes
        secret: HMAC secret key

    Returns:
        Signature in format "sha256=<hex_digest>"
    """
    signature = hmac.new(
        key=secret.encode("utf-8"),
        msg=body,
        digestmod=hashlib.sha256,
    ).hexdigest()
    return f"sha256={signature}"
