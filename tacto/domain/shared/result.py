"""
Result Monad for Domain-Driven Design.

Implements the Result pattern (Railway Oriented Programming) for explicit
error handling without exceptions in business logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar, Union

T = TypeVar("T")
E = TypeVar("E", bound=Exception)
U = TypeVar("U")


@dataclass(frozen=True, slots=True)
class Success(Generic[T]):
    """Represents a successful result containing a value."""

    value: T

    def is_success(self) -> bool:
        return True

    def is_failure(self) -> bool:
        return False


@dataclass(frozen=True, slots=True)
class Failure(Generic[E]):
    """Represents a failed result containing an error."""

    error: E

    def is_success(self) -> bool:
        return False

    def is_failure(self) -> bool:
        return True


Result = Union[Success[T], Failure[E]]


class ResultUtils:
    """
    Utility class for creating and manipulating Result types.

    Usage:
        result = ResultUtils.success(user)
        result = ResultUtils.failure(ValidationError("Invalid email"))

        if result.is_success():
            user = result.value
        else:
            error = result.error
    """

    @staticmethod
    def success(value: T) -> Success[T]:
        """Create a successful result."""
        return Success(value)

    @staticmethod
    def failure(error: E) -> Failure[E]:
        """Create a failed result."""
        return Failure(error)

    @staticmethod
    def map(
        result: Result[T, E],
        func: Callable[[T], U],
    ) -> Result[U, E]:
        """Apply a function to the success value if present."""
        if isinstance(result, Success):
            return Success(func(result.value))
        return result

    @staticmethod
    def flat_map(
        result: Result[T, E],
        func: Callable[[T], Result[U, E]],
    ) -> Result[U, E]:
        """Apply a function that returns a Result to the success value."""
        if isinstance(result, Success):
            return func(result.value)
        return result

    @staticmethod
    def map_error(
        result: Result[T, E],
        func: Callable[[E], Exception],
    ) -> Result[T, Exception]:
        """Apply a function to the error if present."""
        if isinstance(result, Failure):
            return Failure(func(result.error))
        return result

    @staticmethod
    def unwrap_or(result: Result[T, E], default: T) -> T:
        """Get the success value or return a default."""
        if isinstance(result, Success):
            return result.value
        return default

    @staticmethod
    def unwrap_or_raise(result: Result[T, E]) -> T:
        """Get the success value or raise the error."""
        if isinstance(result, Success):
            return result.value
        raise result.error


def Ok(value: T) -> Success[T]:
    """Shorthand for creating a successful result."""
    return Success(value)


def Err(error: E) -> Failure[E]:
    """Shorthand for creating a failed result."""
    return Failure(error)
