"""
Base Value Object implementation.

Value Objects are immutable objects that are defined by their attributes
rather than their identity. Two Value Objects with the same attributes
are considered equal.
"""

from abc import ABC, abstractmethod
from typing import Any


class ValueObject(ABC):
    """
    Abstract base class for all Value Objects.

    Value Objects are:
    - Immutable
    - Compared by value (not identity)
    - Self-validating

    Subclasses must implement:
    - _validate(): Validate the value object's state
    - _get_equality_components(): Return tuple of components for equality
    """

    def __init__(self) -> None:
        """Initialize and validate the value object."""
        self._validate()

    @abstractmethod
    def _validate(self) -> None:
        """
        Validate the value object's invariants.

        Raises:
            ValidationError: If validation fails
        """
        pass

    @abstractmethod
    def _get_equality_components(self) -> tuple[Any, ...]:
        """
        Return the components used for equality comparison.

        Returns:
            Tuple of values that define this value object's identity
        """
        pass

    def __eq__(self, other: object) -> bool:
        """Compare value objects by their equality components."""
        if not isinstance(other, self.__class__):
            return False
        return self._get_equality_components() == other._get_equality_components()

    def __ne__(self, other: object) -> bool:
        """Check inequality."""
        return not self.__eq__(other)

    def __hash__(self) -> int:
        """Hash based on equality components."""
        return hash(self._get_equality_components())

    def __repr__(self) -> str:
        """Return string representation."""
        class_name = self.__class__.__name__
        components = self._get_equality_components()
        return f"{class_name}({components})"
