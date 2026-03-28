"""
AutomationType Value Object.

Represents the automation level for a restaurant's AI assistant.
"""

from enum import IntEnum


class AutomationType(IntEnum):
    """
    Level of AI automation for restaurant.

    BASIC: Institutional info only (no menu details, no orders)
    INTERMEDIATE: Full menu RAG, product recommendations
    ADVANCED: Complete order creation and management
    """

    BASIC = 1
    INTERMEDIATE = 2
    ADVANCED = 3

    @property
    def display_name(self) -> str:
        """Get human-readable name."""
        names = {
            AutomationType.BASIC: "Básico",
            AutomationType.INTERMEDIATE: "Intermediário",
            AutomationType.ADVANCED: "Avançado",
        }
        return names.get(self, "Unknown")

    @property
    def can_access_menu(self) -> bool:
        """Check if this level can access detailed menu information."""
        return self in (AutomationType.INTERMEDIATE, AutomationType.ADVANCED)

    @property
    def can_create_orders(self) -> bool:
        """Check if this level can create orders."""
        return self == AutomationType.ADVANCED

    @property
    def can_recommend_products(self) -> bool:
        """Check if this level can recommend products."""
        return self in (AutomationType.INTERMEDIATE, AutomationType.ADVANCED)

    @classmethod
    def from_value(cls, value: int) -> "AutomationType":
        """Create from integer value with validation."""
        try:
            return cls(value)
        except ValueError:
            raise ValueError(
                f"Invalid automation type: {value}. Must be 1 (BASIC), 2 (INTERMEDIATE), or 3 (ADVANCED)"
            )

    def __str__(self) -> str:
        return self.name
