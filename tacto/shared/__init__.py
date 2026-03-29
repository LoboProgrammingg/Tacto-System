"""
Shared Kernel — Cross-cutting concerns shared across bounded contexts.

This module contains:
- shared/domain/: Value Objects, Events, Exceptions (domain concepts)
- shared/application/: Result type, Command/Query base classes
- shared/infrastructure/: Logging, DateTime helpers

Following DDD (Eric Evans) and Clean Architecture (Uncle Bob).
"""

from tacto.shared.domain import (
    BusinessRuleViolationError,
    ConversationId,
    DomainEvent,
    DomainException,
    EntityId,
    EntityNotFoundError,
    ExternalServiceError,
    InvalidOperationError,
    MessageId,
    OrderId,
    PhoneNumber,
    RestaurantId,
    ValidationError,
    ValueObject,
)
from tacto.shared.application import (
    Err,
    Failure,
    Ok,
    Result,
    ResultUtils,
    Success,
)

__all__ = [
    # Domain
    "DomainException",
    "ValidationError",
    "EntityNotFoundError",
    "BusinessRuleViolationError",
    "InvalidOperationError",
    "ExternalServiceError",
    "DomainEvent",
    "ValueObject",
    "EntityId",
    "RestaurantId",
    "ConversationId",
    "MessageId",
    "OrderId",
    "PhoneNumber",
    # Application
    "Result",
    "Success",
    "Failure",
    "ResultUtils",
    "Ok",
    "Err",
]
