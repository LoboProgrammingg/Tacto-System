"""
Entity identifiers as Value Objects.

All entity IDs are UUIDs wrapped in typed Value Objects for type safety.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from tacto.domain.shared.exceptions import ValidationError
from tacto.domain.shared.value_objects.base import ValueObject


class EntityId(ValueObject):
    """
    Base class for entity identifiers.

    Wraps a UUID to provide type safety and validation.
    """

    __slots__ = ("_value",)

    def __init__(self, value: Optional[str | uuid.UUID] = None) -> None:
        """
        Initialize entity ID.

        Args:
            value: UUID string or UUID object. If None, generates a new UUID.
        """
        if value is None:
            self._value = uuid.uuid4()
        elif isinstance(value, uuid.UUID):
            self._value = value
        else:
            try:
                self._value = uuid.UUID(str(value))
            except ValueError as e:
                raise ValidationError(
                    message=f"Invalid UUID format: {value}",
                    field="id",
                    value=value,
                ) from e
        super().__init__()

    def _validate(self) -> None:
        """Validate UUID is not nil."""
        if self._value == uuid.UUID(int=0):
            raise ValidationError(
                message="Entity ID cannot be nil UUID",
                field="id",
            )

    def _get_equality_components(self) -> tuple[Any, ...]:
        """Return UUID for equality comparison."""
        return (self._value,)

    @property
    def value(self) -> uuid.UUID:
        """Get the underlying UUID value."""
        return self._value

    def __str__(self) -> str:
        """Return string representation of UUID."""
        return str(self._value)

    def __repr__(self) -> str:
        """Return detailed representation."""
        return f"{self.__class__.__name__}('{self._value}')"

    @classmethod
    def generate(cls) -> "EntityId":
        """Generate a new random entity ID."""
        return cls(uuid.uuid4())

    @classmethod
    def from_string(cls, value: str) -> "EntityId":
        """Create entity ID from string."""
        return cls(value)


class RestaurantId(EntityId):
    """Typed identifier for Restaurant entities."""

    pass


class ConversationId(EntityId):
    """Typed identifier for Conversation entities."""

    pass


class MessageId(EntityId):
    """Typed identifier for Message entities."""

    pass


class OrderId(EntityId):
    """Typed identifier for Order entities."""

    pass
