"""TactoFlow Domain Layer."""

from tacto.shared.application import (
    Err,
    Failure,
    Ok,
    Result,
    ResultUtils,
    Success,
)
from tacto.shared.domain import (
    BusinessRuleViolationError,
    ConversationId,
    DomainException,
    EntityId,
    EntityNotFoundError,
    InvalidOperationError,
    MessageId,
    OrderId,
    PhoneNumber,
    RestaurantId,
    ValidationError,
    ValueObject,
)

__all__ = [
    "DomainException",
    "ValidationError",
    "EntityNotFoundError",
    "BusinessRuleViolationError",
    "InvalidOperationError",
    "Result",
    "Success",
    "Failure",
    "ResultUtils",
    "Ok",
    "Err",
    "ValueObject",
    "EntityId",
    "RestaurantId",
    "ConversationId",
    "MessageId",
    "OrderId",
    "PhoneNumber",
]
