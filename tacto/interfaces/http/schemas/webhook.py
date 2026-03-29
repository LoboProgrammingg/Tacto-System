"""Webhook HTTP Schemas."""

from pydantic import BaseModel


class WebhookResponse(BaseModel):
    """Standardized response returned to Join webhook (always HTTP 200)."""

    success: bool
    message: str = "OK"
