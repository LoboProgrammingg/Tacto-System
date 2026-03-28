"""
Join Instance Management Routes.

Endpoints for managing WhatsApp instances via Join Developer API.
All credentials come from environment variables (JOIN_TOKEN_CLIENTE, JOIN_API_BASE_URL).
"""

from typing import Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from tacto.domain.shared.result import Failure
from tacto.infrastructure.messaging.join_instance_manager import JoinInstanceManager


logger = structlog.get_logger()
router = APIRouter()


class CreateInstanceRequest(BaseModel):
    """Request to create a new instance."""

    instance_name: str = Field(..., min_length=3, max_length=100)


class ConnectInstanceRequest(BaseModel):
    """Request to connect instance to restaurant."""

    restaurant_id: UUID
    instance_key: str = Field(..., alias="instancia")

    class Config:
        populate_by_name = True


class ConfigureWebhookRequest(BaseModel):
    """Request to configure webhook URL."""

    instance_key: str
    webhook_url: str = Field(..., pattern=r"^https?://")
    events: Optional[list[str]] = None


class InstanceResponse(BaseModel):
    """Instance response model. instance_name is not returned — list shows all instances."""

    instance_key: str
    status: str
    phone_number: Optional[str] = None
    webhook_url: Optional[str] = None
    is_connected: bool = False


class QRCodeResponse(BaseModel):
    """QR Code response model."""

    qr_code: str
    instance_key: str
    expires_in: int = 60


class InstanceListResponse(BaseModel):
    """List of instances response."""

    instances: list[InstanceResponse]
    total: int


def _to_response(instance) -> InstanceResponse:
    return InstanceResponse(
        instance_key=instance.instance_key,
        status=instance.status,
        phone_number=instance.phone_number,
        webhook_url=instance.webhook_url,
        is_connected=instance.is_connected,
    )


@router.post(
    "/",
    response_model=InstanceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Instance",
    description="Create a new WhatsApp instance",
)
async def create_instance(request: CreateInstanceRequest) -> InstanceResponse:
    """Create a new WhatsApp instance."""
    manager = JoinInstanceManager()
    try:
        result = await manager.create_instance(request.instance_name)
        if isinstance(result, Failure):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(result.error))
        return _to_response(result.value)
    finally:
        await manager.disconnect()


@router.get(
    "/",
    response_model=InstanceListResponse,
    summary="List Instances",
    description="List all WhatsApp instances from the Join API",
)
async def list_instances() -> InstanceListResponse:
    """List all WhatsApp instances."""
    manager = JoinInstanceManager()
    try:
        result = await manager.list_instances()
        if isinstance(result, Failure):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(result.error),
            )
        instances = [_to_response(i) for i in result.value]
        return InstanceListResponse(instances=instances, total=len(instances))
    finally:
        await manager.disconnect()


@router.get(
    "/{instance_key}/status",
    response_model=InstanceResponse,
    summary="Get Instance Status",
    description="Get status of a specific instance",
)
async def get_instance_status(instance_key: str) -> InstanceResponse:
    """Get instance status."""
    manager = JoinInstanceManager()
    try:
        result = await manager.get_instance_status(instance_key)
        if isinstance(result, Failure):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(result.error))
        return _to_response(result.value)
    finally:
        await manager.disconnect()


@router.get(
    "/{instance_key}/qrcode",
    response_model=QRCodeResponse,
    summary="Get QR Code",
    description="Get QR code for instance connection",
)
async def get_qr_code(instance_key: str) -> QRCodeResponse:
    """Get QR code for WhatsApp connection."""
    manager = JoinInstanceManager()
    try:
        result = await manager.get_qr_code(instance_key)
        if isinstance(result, Failure):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(result.error))
        qr = result.value
        return QRCodeResponse(qr_code=qr.qr_code, instance_key=qr.instance_key, expires_in=qr.expires_in)
    finally:
        await manager.disconnect()


@router.post(
    "/webhook",
    status_code=status.HTTP_200_OK,
    summary="Configure Webhook",
    description="Configure webhook URL for an instance",
)
async def configure_webhook(request: ConfigureWebhookRequest) -> dict:
    """Configure webhook URL for instance."""
    manager = JoinInstanceManager()
    try:
        result = await manager.configure_webhook(
            instance_key=request.instance_key,
            webhook_url=request.webhook_url,
            events=request.events,
        )
        if isinstance(result, Failure):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(result.error))
        return {
            "success": True,
            "message": "Webhook configured successfully",
            "instance_key": request.instance_key,
            "webhook_url": request.webhook_url,
        }
    finally:
        await manager.disconnect()


@router.post(
    "/connect",
    status_code=status.HTTP_200_OK,
    summary="Connect Instance to Restaurant",
    description="Associate a WhatsApp instance with a restaurant (multi-tenant webhook routing)",
)
async def connect_to_restaurant(request: ConnectInstanceRequest) -> dict:
    """
    Connect WhatsApp instance to restaurant.

    Updates canal_master_id on the restaurant so incoming webhooks from
    this instance are routed to the correct restaurant's AI pipeline.
    """
    from tacto.domain.shared.value_objects import RestaurantId
    from tacto.infrastructure.database.connection import get_async_session
    from tacto.infrastructure.persistence.restaurant_repository import (
        PostgresRestaurantRepository,
    )

    async with get_async_session() as session:
        repo = PostgresRestaurantRepository(session)
        restaurant_id = RestaurantId(request.restaurant_id)
        restaurant_result = await repo.find_by_id(restaurant_id)

        if isinstance(restaurant_result, Failure) or restaurant_result.value is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Restaurant {request.restaurant_id} not found",
            )

        restaurant = restaurant_result.value

        # Persist the canal_master_id so the webhook can route messages correctly
        update_result = await repo.update_canal_master_id(
            restaurant_id=restaurant_id,
            canal_master_id=request.instance_key,
        )

        if isinstance(update_result, Failure):
            logger.error(
                "Failed to update canal_master_id",
                restaurant_id=str(request.restaurant_id),
                instance_key=request.instance_key,
                error=str(update_result.error),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to link instance to restaurant: {update_result.error}",
            )

        logger.info(
            "Instance successfully connected to restaurant",
            restaurant_id=str(request.restaurant_id),
            instance_key=request.instance_key,
            restaurant_name=restaurant.name,
        )

        return {
            "success": True,
            "message": f"Instance '{request.instance_key}' connected to restaurant '{restaurant.name}'",
            "restaurant_id": str(request.restaurant_id),
            "restaurant_name": restaurant.name,
            "instance_key": request.instance_key,
        }


@router.delete(
    "/{instance_key}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Instance",
    description="Delete a WhatsApp instance",
)
async def delete_instance(instance_key: str) -> None:
    """Delete WhatsApp instance."""
    manager = JoinInstanceManager()
    try:
        result = await manager.delete_instance(instance_key)
        if isinstance(result, Failure):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(result.error))
    finally:
        await manager.disconnect()


@router.post(
    "/{instance_key}/logout",
    status_code=status.HTTP_200_OK,
    summary="Logout Instance",
    description="Disconnect/logout a WhatsApp instance",
)
async def logout_instance(instance_key: str) -> dict:
    """Logout/disconnect WhatsApp instance."""
    manager = JoinInstanceManager()
    try:
        result = await manager.disconnect_instance(instance_key)
        if isinstance(result, Failure):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(result.error))
        return {"success": True, "message": "Instance logged out successfully", "instance_key": instance_key}
    finally:
        await manager.disconnect()
