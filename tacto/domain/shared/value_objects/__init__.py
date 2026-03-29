"""
Shared Value Objects for TactoFlow domain.

SHIM: Re-exports from tacto.shared.domain.value_objects for backward compatibility.
"""

from tacto.shared.domain.value_objects import (
    ConversationId,
    EntityId,
    MessageId,
    OrderId,
    PhoneNumber,
    RestaurantId,
    ValueObject,
)

__all__ = [
    "ValueObject",
    "EntityId",
    "RestaurantId",
    "ConversationId",
    "MessageId",
    "OrderId",
    "PhoneNumber",
]
