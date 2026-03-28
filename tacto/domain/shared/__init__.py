"""Shared kernel for TactoFlow domain."""

from tacto.domain.shared.exceptions import (
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
from tacto.domain.shared.result import Err, Failure, Ok, Result, ResultUtils, Success
from tacto.domain.shared.value_objects import (
    ConversationId,
    EntityId,
    MessageId,
    OrderId,
    PhoneNumber,
    RestaurantId,
    ValueObject,
)

__all__ = [
    "DomainException",
    "ValidationError",
    "EntityNotFoundError",
    "BusinessRuleViolationError",
    "InvalidOperationError",
    "ExternalServiceError",
    "AuthenticationError",
    "AuthorizationError",
    "RateLimitError",
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
