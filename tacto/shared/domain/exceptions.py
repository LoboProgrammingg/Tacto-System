"""
Domain exceptions for TactoFlow.

All domain-specific exceptions inherit from DomainException.
"""

from typing import Any, Optional


class DomainException(Exception):
    """Base exception for all domain errors."""

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__
        self.details = details or {}

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }


class ValidationError(DomainException):
    """Raised when domain validation fails."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
    ) -> None:
        details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)
        super().__init__(message, code="VALIDATION_ERROR", details=details)
        self.field = field
        self.value = value


class EntityNotFoundError(DomainException):
    """Raised when an entity is not found."""

    def __init__(
        self,
        entity_type: str,
        entity_id: str,
    ) -> None:
        message = f"{entity_type} with id '{entity_id}' not found"
        super().__init__(
            message,
            code="ENTITY_NOT_FOUND",
            details={"entity_type": entity_type, "entity_id": entity_id},
        )
        self.entity_type = entity_type
        self.entity_id = entity_id


class BusinessRuleViolationError(DomainException):
    """Raised when a business rule is violated."""

    def __init__(
        self,
        rule: str,
        message: str,
    ) -> None:
        super().__init__(
            message,
            code="BUSINESS_RULE_VIOLATION",
            details={"rule": rule},
        )
        self.rule = rule


class InvalidOperationError(DomainException):
    """Raised when an operation is invalid in the current state."""

    def __init__(
        self,
        operation: str,
        reason: str,
    ) -> None:
        message = f"Cannot perform '{operation}': {reason}"
        super().__init__(
            message,
            code="INVALID_OPERATION",
            details={"operation": operation, "reason": reason},
        )


class ExternalServiceError(DomainException):
    """Raised when an external service fails."""

    def __init__(
        self,
        service: str,
        message: str,
        status_code: Optional[int] = None,
    ) -> None:
        details: dict[str, Any] = {"service": service}
        if status_code:
            details["status_code"] = status_code
        super().__init__(
            message,
            code="EXTERNAL_SERVICE_ERROR",
            details=details,
        )
        self.service = service
        self.status_code = status_code


class AuthenticationError(DomainException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message, code="AUTHENTICATION_ERROR")


class AuthorizationError(DomainException):
    """Raised when authorization fails."""

    def __init__(self, message: str = "Access denied") -> None:
        super().__init__(message, code="AUTHORIZATION_ERROR")


class RateLimitError(DomainException):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        limit: int,
        window_seconds: int,
        retry_after: Optional[int] = None,
    ) -> None:
        message = f"Rate limit of {limit} requests per {window_seconds}s exceeded"
        details: dict[str, Any] = {"limit": limit, "window_seconds": window_seconds}
        if retry_after:
            details["retry_after"] = retry_after
        super().__init__(message, code="RATE_LIMIT_EXCEEDED", details=details)
