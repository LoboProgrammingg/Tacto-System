"""
IntegrationType Value Object.

Represents the type of messaging integration used by a restaurant.
"""

from enum import IntEnum


class IntegrationType(IntEnum):
    """
    Type of messaging integration.

    Values match database schema and Tacto API specifications.
    """

    META = 1
    JOIN = 2

    @property
    def display_name(self) -> str:
        """Get human-readable name."""
        names = {
            IntegrationType.META: "WhatsApp Business (Meta)",
            IntegrationType.JOIN: "Join Developer",
        }
        return names.get(self, "Unknown")

    @classmethod
    def from_value(cls, value: int) -> "IntegrationType":
        """Create from integer value with validation."""
        try:
            return cls(value)
        except ValueError:
            raise ValueError(f"Invalid integration type: {value}. Must be 1 (META) or 2 (JOIN)")

    def __str__(self) -> str:
        return self.name
