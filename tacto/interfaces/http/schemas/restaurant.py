"""Restaurant HTTP Schemas."""

from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AgentPersonaConfigSchema(BaseModel):
    """
    Schema for per-restaurant AI persona overrides.

    All fields are optional — omit a field to use the platform default (env var).
    Only include fields that should differ from the platform default.

    Examples:
      {}                                             → use all platform defaults
      {"attendant_name": "Chef Pedro"}               → override name only
      {"attendant_name": "Ana", "attendant_gender": "feminino", "max_emojis_per_message": 2}
    """

    attendant_name: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=50,
        description="Nome do atendente virtual. Null = usa ATTENDANT_NAME do .env.",
        examples=["Maria", "Chef Pedro", "Juliana"],
    )
    attendant_gender: Optional[str] = Field(
        default=None,
        description="Gênero gramatical do atendente: feminino | masculino | neutro.",
        pattern=r"^(feminino|masculino|neutro)$",
    )
    persona_style: Optional[str] = Field(
        default=None,
        description="Estilo de comunicação: formal | informal.",
        pattern=r"^(formal|informal)$",
    )
    max_emojis_per_message: Optional[int] = Field(
        default=None,
        ge=0,
        le=5,
        description="Máximo de emojis por mensagem (0 = sem emojis). Null = usa ATTENDANT_MAX_EMOJIS do .env.",
    )


class CreateRestaurantRequest(BaseModel):
    """Request body for creating a restaurant."""

    name: str = Field(..., min_length=3, max_length=255)
    menu_url: str = Field(..., pattern=r"^https?://", description="URL do Webgula para pedidos (ex: https://webgula.com.br/restaurante/delivery)")
    opening_hours: Optional[dict[str, Any]] = Field(
        default=None,
        description="Horários de funcionamento. Se não informado, será preenchido automaticamente pelo tacto-sync.",
    )
    chave_grupo_empresarial: UUID
    canal_master_id: str = Field(..., min_length=1)
    empresa_base_id: str = Field(..., min_length=1)
    integration_type: int = Field(default=2, ge=1, le=2)
    automation_type: int = Field(default=1, ge=1, le=3)
    agent_config: Optional[AgentPersonaConfigSchema] = Field(
        default=None,
        description="Configurações de persona do atendente virtual. Null = usa todos os padrões do .env.",
    )


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
    agent_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Configurações de persona vigentes para este restaurante.",
    )


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
