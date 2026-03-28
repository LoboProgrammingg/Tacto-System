"""
Integration Entity.

Represents the integration configuration for a restaurant's messaging channel.
This is a child entity of the Restaurant aggregate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from tacto.domain.restaurant.value_objects.integration_type import IntegrationType
from tacto.domain.shared.exceptions import ValidationError
from tacto.domain.shared.value_objects import RestaurantId


@dataclass
class IntegrationCredentials:
    """
    Value Object for integration credentials.

    Stores encrypted credentials for external service authentication.
    """

    instance_key: Optional[str] = None
    token_cliente: Optional[str] = None
    api_key: Optional[str] = None
    webhook_secret: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary (for JSON storage)."""
        return {
            "instance_key": self.instance_key,
            "token_cliente": self.token_cliente,
            "api_key": self.api_key,
            "webhook_secret": self.webhook_secret,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IntegrationCredentials":
        """Create from dictionary."""
        return cls(
            instance_key=data.get("instance_key"),
            token_cliente=data.get("token_cliente"),
            api_key=data.get("api_key"),
            webhook_secret=data.get("webhook_secret"),
        )


@dataclass
class Integration:
    """
    Integration Entity.

    Represents the configuration for connecting a restaurant to a messaging
    platform (Join, WhatsApp Business, etc.).

    This is a child entity within the Restaurant aggregate boundary.
    """

    id: UUID
    restaurant_id: RestaurantId
    integration_type: IntegrationType
    credentials: IntegrationCredentials
    webhook_url: Optional[str] = None
    is_active: bool = True
    last_sync_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        """Validate invariants."""
        self._validate_invariants()

    def _validate_invariants(self) -> None:
        """Validate integration invariants."""
        if self.webhook_url and not self.webhook_url.startswith(("http://", "https://")):
            raise ValidationError(
                message="Webhook URL must be a valid HTTP/HTTPS URL",
                field="webhook_url",
                value=self.webhook_url,
            )

    def activate(self) -> None:
        """Activate the integration."""
        self.is_active = True
        self._touch()

    def deactivate(self) -> None:
        """Deactivate the integration."""
        self.is_active = False
        self._touch()

    def update_credentials(self, credentials: IntegrationCredentials) -> None:
        """Update integration credentials."""
        self.credentials = credentials
        self._touch()

    def mark_synced(self) -> None:
        """Mark integration as synced."""
        self.last_sync_at = datetime.utcnow()
        self._touch()

    def _touch(self) -> None:
        """Update timestamp."""
        self.updated_at = datetime.utcnow()

    @classmethod
    def create(
        cls,
        restaurant_id: RestaurantId,
        integration_type: IntegrationType,
        credentials: IntegrationCredentials,
        webhook_url: Optional[str] = None,
    ) -> "Integration":
        """Factory method to create a new Integration."""
        return cls(
            id=uuid4(),
            restaurant_id=restaurant_id,
            integration_type=integration_type,
            credentials=credentials,
            webhook_url=webhook_url,
        )
