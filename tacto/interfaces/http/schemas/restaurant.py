"""Restaurant HTTP Schemas."""

from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CreateRestaurantRequest(BaseModel):
    """Request body for creating a restaurant."""

    name: str = Field(..., min_length=3, max_length=255)
    prompt_default: str = Field(..., min_length=10)
    menu_url: str = Field(..., pattern=r"^https?://")
    opening_hours: dict[str, Any]
    chave_grupo_empresarial: UUID
    canal_master_id: str = Field(..., min_length=1)
    empresa_base_id: str = Field(..., min_length=1)
    integration_type: int = Field(default=2, ge=1, le=2)
    automation_type: int = Field(default=1, ge=1, le=3)


class RestaurantResponse(BaseModel):
    """Response model for restaurant."""

    id: UUID
    name: str
    prompt_default: str
    menu_url: str
    opening_hours: dict[str, Any]
    integration_type: int
    automation_type: int
    chave_grupo_empresarial: UUID
    canal_master_id: str
    empresa_base_id: str
    is_active: bool


class RestaurantListResponse(BaseModel):
    """Response model for restaurant list."""

    items: list[RestaurantResponse]
    total: int


class TactoSyncResponse(BaseModel):
    """Response for Tacto menu sync operation."""

    restaurant_id: UUID
    restaurant_name: str
    items_synced: int
    categories: list[str]
    address: Optional[str] = None
    hours_text: str


class TactoMenuItemResponse(BaseModel):
    """Response model for a single Tacto menu item."""

    name: str
    category: str
    price: float
    description: Optional[str] = None
    is_available: bool


class TactoRestaurantDataResponse(BaseModel):
    """Response for full Tacto restaurant data fetch."""

    restaurant_id: UUID
    restaurant_name: str
    tacto_name: str
    total_items: int
    categories: list[str]
    menu_items: list[TactoMenuItemResponse]
    raw_menu_text: str
    payment_methods: list[str]
    address: Optional[str] = None
    phone: Optional[str] = None
    delivery_info: Optional[str] = None
    cached: bool
    last_updated: str
