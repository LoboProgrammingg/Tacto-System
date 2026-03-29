"""
Domain exceptions for TactoFlow.

SHIM: Re-exports from tacto.shared.domain.exceptions for backward compatibility.
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
]
