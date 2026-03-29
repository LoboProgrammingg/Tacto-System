"""
HTTP Schemas — Pydantic models for API request/response validation.

Following Clean Architecture, these schemas are interface-specific models
that map between HTTP requests/responses and application DTOs.
"""

from tacto.interfaces.http.schemas.restaurant import (
    CreateRestaurantRequest,
    RestaurantListResponse,
    RestaurantResponse,
    TactoMenuItemResponse,
    TactoRestaurantDataResponse,
    TactoSyncResponse,
)
from tacto.interfaces.http.schemas.chat import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
)
from tacto.interfaces.http.schemas.instance import (
    ConfigureWebhookRequest,
    ConnectInstanceRequest,
    CreateInstanceRequest,
    InstanceListResponse,
    InstanceResponse,
    QRCodeResponse,
)
from tacto.interfaces.http.schemas.webhook import (
    WebhookResponse,
)

__all__ = [
    # Restaurant
    "CreateRestaurantRequest",
    "RestaurantResponse",
    "RestaurantListResponse",
    "TactoSyncResponse",
    "TactoMenuItemResponse",
    "TactoRestaurantDataResponse",
    # Chat
    "ChatRequest",
    "ChatMessage",
    "ChatResponse",
    # Instance
    "CreateInstanceRequest",
    "ConnectInstanceRequest",
    "ConfigureWebhookRequest",
    "InstanceResponse",
    "QRCodeResponse",
    "InstanceListResponse",
    # Webhook
    "WebhookResponse",
]
