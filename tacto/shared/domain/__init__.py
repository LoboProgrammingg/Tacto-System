"""
Shared Domain — Value Objects, Events, and Exceptions shared across bounded contexts.

This is the Shared Kernel in DDD terminology.
"""

from tacto.shared.domain.exceptions import (
    AuthenticationError,
    AuthorizationError,
    BusinessRuleViolationError,
    DomainException,
    EntityNotFoundError,
    ExternalServiceError,
    InvalidOperationError,
    RateLimitError,
    ValidationError,
)
from tacto.shared.domain.events import DomainEvent
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
    # Exceptions
    "DomainException",
    "ValidationError",
    "EntityNotFoundError",
    "BusinessRuleViolationError",
    "InvalidOperationError",
    "ExternalServiceError",
    "AuthenticationError",
    "AuthorizationError",
    "RateLimitError",
    # Events
    "DomainEvent",
    # Value Objects
    "ValueObject",
    "EntityId",
    "RestaurantId",
    "ConversationId",
    "MessageId",
    "OrderId",
    "PhoneNumber",
]
