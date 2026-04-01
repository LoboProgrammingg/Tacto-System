"""
Restaurant DTOs for Application Layer.

Data Transfer Objects for restaurant-related operations.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateRestaurantDTO:
    """DTO for creating a new restaurant."""

    name: str
    menu_url: str
    chave_grupo_empresarial: UUID
    canal_master_id: str
    empresa_base_id: str
    opening_hours: Optional[dict[str, Any]] = None
    prompt_default: str = ""
    integration_type: int = 2  # JOIN
    automation_type: int = 1  # BASIC
    timezone: str = "America/Cuiaba"
    agent_config: Optional[dict[str, Any]] = None


@dataclass(frozen=True, slots=True)
class UpdateRestaurantDTO:
    """DTO for updating an existing restaurant."""

    name: Optional[str] = None
    prompt_default: Optional[str] = None
    menu_url: Optional[str] = None
    opening_hours: Optional[dict[str, Any]] = None
    automation_type: Optional[int] = None
    timezone: Optional[str] = None
    is_active: Optional[bool] = None
    agent_config: Optional[dict[str, Any]] = None


@dataclass(frozen=True, slots=True)
class RestaurantResponseDTO:
    """DTO for restaurant response."""

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
    timezone: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    agent_config: dict[str, Any] = None

    @classmethod
    def from_entity(cls, entity: Any) -> "RestaurantResponseDTO":
        """Create DTO from Restaurant entity."""
        return cls(
            id=entity.id.value,
            name=entity.name,
            prompt_default=entity.prompt_default,
            menu_url=entity.menu_url,
            opening_hours=entity.opening_hours.to_dict(),
            integration_type=entity.integration_type.value,
            automation_type=entity.automation_type.value,
            chave_grupo_empresarial=entity.chave_grupo_empresarial,
            canal_master_id=entity.canal_master_id,
            empresa_base_id=entity.empresa_base_id,
            timezone=entity.timezone,
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            agent_config=entity.agent_config.to_dict(),
        )
