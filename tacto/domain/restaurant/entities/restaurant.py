"""
Restaurant Entity - Aggregate Root.

The Restaurant is the main aggregate root for the Restaurant bounded context.
It encapsulates all business rules related to restaurant management.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from tacto.domain.restaurant.events.restaurant_created import RestaurantCreated
from tacto.domain.restaurant.value_objects.agent_persona import AgentPersonaConfig
from tacto.domain.restaurant.value_objects.automation_type import AutomationType
from tacto.domain.restaurant.value_objects.integration_type import IntegrationType
from tacto.domain.restaurant.value_objects.opening_hours import OpeningHours
from tacto.shared.domain.events.domain_event import DomainEvent
from tacto.shared.domain.exceptions import BusinessRuleViolationError, ValidationError
from tacto.shared.domain.value_objects import RestaurantId


@dataclass
class Restaurant:
    """
    Restaurant Aggregate Root.

    Represents a restaurant tenant in the system with all its configuration
    for AI automation and external integrations.

    Invariants:
    - Name must be at least 3 characters
    - Must have valid opening hours
    - Must have valid integration configuration
    - prompt_default can be empty (means: use base SYSTEM_PROMPT only, no custom instructions)
    - menu_url must be a valid URL
    """

    id: RestaurantId
    name: str
    prompt_default: str
    menu_url: str
    opening_hours: OpeningHours
    integration_type: IntegrationType
    automation_type: AutomationType
    chave_grupo_empresarial: UUID
    canal_master_id: str
    empresa_base_id: str
    timezone: str = "America/Cuiaba"
    agent_config: AgentPersonaConfig = field(default_factory=AgentPersonaConfig.empty)
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: Optional[datetime] = None
    # Pending domain events — lidos e despachados pelo repositório/use case após save
    pending_events: list[DomainEvent] = field(default_factory=list, repr=False, compare=False)

    def __post_init__(self) -> None:
        """Validate invariants after initialization."""
        self._validate_invariants()

    def _validate_invariants(self) -> None:
        """Validate all business invariants."""
        if len(self.name.strip()) < 3:
            raise ValidationError(
                message="Restaurant name must be at least 3 characters",
                field="name",
                value=self.name,
            )

        if not self.menu_url.strip():
            raise ValidationError(
                message="Menu URL cannot be empty",
                field="menu_url",
            )

        if not self.menu_url.startswith(("http://", "https://")):
            raise ValidationError(
                message="Menu URL must be a valid HTTP/HTTPS URL",
                field="menu_url",
                value=self.menu_url,
            )

        if not self.canal_master_id.strip():
            raise ValidationError(
                message="Canal Master ID cannot be empty",
                field="canal_master_id",
            )

    def is_open_now(self) -> bool:
        """Check if restaurant is currently open in its timezone."""
        return self.opening_hours.is_open_now(self.timezone)

    def get_today_hours(self) -> str:
        """Get formatted opening hours for today."""
        return self.opening_hours.get_today_hours()

    def can_process_ai_response(self) -> bool:
        """Check if AI can process responses for this restaurant."""
        return self.is_active and not self.is_deleted

    @property
    def is_deleted(self) -> bool:
        """Check if restaurant is soft-deleted."""
        return self.deleted_at is not None

    def activate(self) -> None:
        """Activate the restaurant."""
        if self.is_deleted:
            raise BusinessRuleViolationError(
                rule="BR-REST-001",
                message="Cannot activate a deleted restaurant",
            )
        self.is_active = True
        self._touch()

    def deactivate(self) -> None:
        """Deactivate the restaurant."""
        self.is_active = False
        self._touch()

    def soft_delete(self) -> None:
        """Soft delete the restaurant."""
        self.deleted_at = datetime.now(timezone.utc)
        self.is_active = False
        self._touch()

    def update_prompt(self, new_prompt: str) -> None:
        """Update the default AI prompt. Empty string is valid — uses base SYSTEM_PROMPT."""
        self.prompt_default = new_prompt
        self._touch()

    def update_agent_config(self, new_config: AgentPersonaConfig) -> None:
        """Update the AI persona configuration for this restaurant."""
        self.agent_config = new_config
        self._touch()

    def update_opening_hours(self, new_hours: OpeningHours) -> None:
        """Update opening hours."""
        self.opening_hours = new_hours
        self._touch()

    def upgrade_automation(self, new_type: AutomationType) -> None:
        """Upgrade automation level."""
        if new_type.value < self.automation_type.value:
            raise BusinessRuleViolationError(
                rule="BR-REST-002",
                message="Cannot downgrade automation level directly. Contact support.",
            )
        self.automation_type = new_type
        self._touch()

    def _add_event(self, event: DomainEvent) -> None:
        """Acumula evento para despacho após persistência."""
        self.pending_events.append(event)

    def _touch(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now(timezone.utc)

    @classmethod
    def create(
        cls,
        name: str,
        prompt_default: str,
        menu_url: str,
        opening_hours: OpeningHours,
        integration_type: IntegrationType,
        automation_type: AutomationType,
        chave_grupo_empresarial: UUID,
        canal_master_id: str,
        empresa_base_id: str,
        timezone: str = "America/Cuiaba",
        agent_config: Optional[AgentPersonaConfig] = None,
        restaurant_id: Optional[RestaurantId] = None,
    ) -> "Restaurant":
        """
        Factory method to create a new Restaurant.

        This is the preferred way to create new Restaurant instances.
        """
        instance = cls(
            id=restaurant_id or RestaurantId.generate(),
            name=name,
            prompt_default=prompt_default,
            menu_url=menu_url,
            opening_hours=opening_hours,
            integration_type=integration_type,
            automation_type=automation_type,
            chave_grupo_empresarial=chave_grupo_empresarial,
            canal_master_id=canal_master_id,
            empresa_base_id=empresa_base_id,
            timezone=timezone,
            agent_config=agent_config or AgentPersonaConfig.empty(),
        )
        instance._add_event(RestaurantCreated(
            restaurant_id=instance.id.value,
            name=instance.name,
            canal_master_id=instance.canal_master_id,
        ))
        return instance
