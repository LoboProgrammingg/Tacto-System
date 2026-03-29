"""Instance HTTP Schemas."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CreateInstanceRequest(BaseModel):
    """Request to create a new WhatsApp instance."""

    instance_name: str = Field(..., min_length=3, max_length=100)


class ConnectInstanceRequest(BaseModel):
    """Request to connect instance to restaurant."""

    restaurant_id: UUID
    instance_key: str = Field(..., alias="instancia")

    class Config:
        populate_by_name = True


class ConfigureWebhookRequest(BaseModel):
    """Request to configure webhook URL for an instance."""

    instance_key: str
    webhook_url: str = Field(..., pattern=r"^https?://")
    events: Optional[list[str]] = None


class InstanceResponse(BaseModel):
    """Response model for a WhatsApp instance."""

    instance_key: str
    status: str
    phone_number: Optional[str] = None
    webhook_url: Optional[str] = None
    is_connected: bool = False


class QRCodeResponse(BaseModel):
    """Response model for QR code generation."""

    qr_code: str
    instance_key: str
    expires_in: int = 60


class InstanceListResponse(BaseModel):
    """Response model for list of instances."""

    instances: list[InstanceResponse]
    total: int
