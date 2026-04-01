"""
Order Item Value Object.

Represents a single item in the customer's order cart.
Immutable by design - modifications create new instances.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class OrderItem:
    """
    A single item in the order cart.

    Attributes:
        name: Product name from menu (e.g., "Pizza Calabresa")
        quantity: Number of units
        unit_price: Price per unit in BRL
        variation: Size or variation (e.g., "Grande", "Média")
        observations: Special requests (e.g., "Sem cebola")
    """

    name: str
    quantity: int
    unit_price: float
    variation: Optional[str] = None
    observations: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate item data."""
        if self.quantity < 1:
            raise ValueError("Quantity must be at least 1")
        if self.unit_price < 0:
            raise ValueError("Unit price cannot be negative")
        if not self.name.strip():
            raise ValueError("Item name cannot be empty")

    @property
    def total_price(self) -> float:
        """Calculate total price for this item."""
        return round(self.quantity * self.unit_price, 2)

    @property
    def display_name(self) -> str:
        """Get formatted display name with variation."""
        if self.variation:
            return f"{self.name} ({self.variation})"
        return self.name

    def with_quantity(self, new_quantity: int) -> "OrderItem":
        """Create new item with updated quantity."""
        return OrderItem(
            name=self.name,
            quantity=new_quantity,
            unit_price=self.unit_price,
            variation=self.variation,
            observations=self.observations,
        )

    def with_observations(self, new_observations: str) -> "OrderItem":
        """Create new item with updated observations."""
        return OrderItem(
            name=self.name,
            quantity=self.quantity,
            unit_price=self.unit_price,
            variation=self.variation,
            observations=new_observations,
        )

    def matches(self, name: str, variation: Optional[str] = None) -> bool:
        """
        Check if this item matches the given name and variation.

        Uses case-insensitive comparison for flexibility.
        """
        name_matches = self.name.lower().strip() == name.lower().strip()
        if variation is None:
            return name_matches
        if self.variation is None:
            return False
        return name_matches and self.variation.lower().strip() == variation.lower().strip()

    def to_dict(self) -> dict:
        """Serialize to dictionary for storage."""
        return {
            "name": self.name,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "variation": self.variation,
            "observations": self.observations,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OrderItem":
        """Deserialize from dictionary."""
        return cls(
            name=data["name"],
            quantity=data["quantity"],
            unit_price=data["unit_price"],
            variation=data.get("variation"),
            observations=data.get("observations"),
        )

    def to_line(self, index: int) -> str:
        """Format as a single line for display in order summary."""
        line = f"{index}. {self.quantity}x {self.display_name} - R$ {self.total_price:.2f}"
        if self.observations:
            line += f" _{self.observations}_"
        return line
