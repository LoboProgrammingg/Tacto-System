"""
Order State Value Object.

Represents the complete state of an in-progress order.
This is the core aggregate for the Level 2 ordering flow.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from tacto.domain.order.value_objects.order_item import OrderItem
from tacto.domain.order.value_objects.order_status import OrderStatus


@dataclass
class OrderState:
    """
    Complete state of an in-progress order.

    This is a mutable aggregate that tracks the order through its lifecycle.
    It maintains the cart, delivery info, and status transitions.

    Attributes:
        restaurant_id: Restaurant this order belongs to
        customer_phone: Customer phone number (unique identifier)
        customer_name: Optional customer name for personalization
        status: Current order status
        items: List of items in the cart
        delivery_address: Delivery address when collected
        payment_method: Payment method when collected
        observations: General order observations
        created_at: When the order session started
        updated_at: Last modification timestamp
    """

    restaurant_id: UUID
    customer_phone: str
    customer_name: Optional[str] = None
    status: OrderStatus = OrderStatus.BROWSING
    items: list[OrderItem] = field(default_factory=list)
    delivery_address: Optional[str] = None
    payment_method: Optional[str] = None
    observations: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def subtotal(self) -> float:
        """Calculate subtotal of all items."""
        return round(sum(item.total_price for item in self.items), 2)

    @property
    def total(self) -> float:
        """Calculate total (subtotal + delivery fee if applicable)."""
        return self.subtotal

    @property
    def item_count(self) -> int:
        """Total number of individual items (considering quantities)."""
        return sum(item.quantity for item in self.items)

    @property
    def is_empty(self) -> bool:
        """Check if cart is empty."""
        return len(self.items) == 0

    @property
    def is_active(self) -> bool:
        """Check if order is still in progress."""
        return self.status.is_active

    @property
    def can_add_items(self) -> bool:
        """Check if items can still be added."""
        return self.status.can_add_items

    def add_item(self, item: OrderItem) -> None:
        """
        Add item to cart.

        If an identical item exists (same name, variation, observations),
        increases the quantity. Otherwise, adds as new item.
        """
        if not self.can_add_items:
            raise ValueError(f"Cannot add items in status: {self.status}")

        for i, existing in enumerate(self.items):
            if (
                existing.matches(item.name, item.variation)
                and existing.observations == item.observations
            ):
                self.items[i] = existing.with_quantity(existing.quantity + item.quantity)
                self._touch()
                return

        self.items.append(item)
        self._set_status(OrderStatus.ADDING_ITEMS)
        self._touch()

    def remove_item(
        self, name: str, variation: Optional[str] = None
    ) -> Optional[OrderItem]:
        """
        Remove item from cart.

        Returns the removed item or None if not found.
        """
        for i, item in enumerate(self.items):
            if item.matches(name, variation):
                removed = self.items.pop(i)
                self._touch()
                return removed
        return None

    def update_item_quantity(
        self, name: str, new_quantity: int, variation: Optional[str] = None
    ) -> bool:
        """
        Update quantity of an existing item.

        Returns True if item was found and updated.
        """
        if new_quantity < 1:
            return self.remove_item(name, variation) is not None

        for i, item in enumerate(self.items):
            if item.matches(name, variation):
                self.items[i] = item.with_quantity(new_quantity)
                self._touch()
                return True
        return False

    def clear(self) -> None:
        """Clear all items from cart."""
        self.items = []
        self._set_status(OrderStatus.BROWSING)
        self._touch()

    def set_delivery_address(self, address: str) -> None:
        """Set delivery address."""
        if self.is_empty:
            raise ValueError("Cannot set address with empty cart")
        self.delivery_address = address.strip()
        self._set_status(OrderStatus.COLLECTING_PAYMENT)
        self._touch()

    def set_payment_method(self, method: str) -> None:
        """Set payment method."""
        if not self.delivery_address:
            raise ValueError("Cannot set payment before address")
        self.payment_method = method.strip()
        self._set_status(OrderStatus.CONFIRMING)
        self._touch()

    def confirm(self) -> None:
        """Confirm the order."""
        if self.status != OrderStatus.CONFIRMING:
            raise ValueError(f"Cannot confirm order in status: {self.status}")
        if not self.delivery_address or not self.payment_method:
            raise ValueError("Missing delivery address or payment method")
        self._set_status(OrderStatus.CONFIRMED)
        self._touch()

    def cancel(self) -> None:
        """Cancel the order."""
        self._set_status(OrderStatus.CANCELLED)
        self._touch()

    def start_review(self) -> None:
        """Transition to reviewing status."""
        if self.is_empty:
            raise ValueError("Cannot review empty cart")
        self._set_status(OrderStatus.REVIEWING)
        self._touch()

    def start_collecting_address(self) -> None:
        """Transition to collecting address."""
        if self.is_empty:
            raise ValueError("Cannot collect address with empty cart")
        self._set_status(OrderStatus.COLLECTING_ADDRESS)
        self._touch()

    def _set_status(self, new_status: OrderStatus) -> None:
        """Internal status transition."""
        self.status = new_status

    def _touch(self) -> None:
        """Update the modification timestamp."""
        self.updated_at = datetime.now(timezone.utc)

    def to_summary(self) -> str:
        """
        Generate order summary for display to customer.

        Returns formatted string with items, prices, and total.
        """
        if self.is_empty:
            return "🛒 *Seu carrinho está vazio.*"

        lines = ["📋 *Seu pedido atual:*", ""]

        for i, item in enumerate(self.items, 1):
            lines.append(item.to_line(i))

        lines.append("")
        lines.append(f"*Subtotal: R$ {self.subtotal:.2f}*")

        if self.delivery_address:
            lines.append(f"\n📍 *Endereço:* {self.delivery_address}")

        if self.payment_method:
            lines.append(f"💳 *Pagamento:* {self.payment_method}")

        return "\n".join(lines)

    def to_cart_context(self) -> str:
        """
        Generate cart context for LLM prompt injection.

        More compact format for system prompt.
        """
        if self.is_empty:
            return "Carrinho: vazio"

        lines = [f"Carrinho ({self.item_count} itens, R$ {self.subtotal:.2f}):"]
        for item in self.items:
            line = f"- {item.quantity}x {item.display_name}: R$ {item.total_price:.2f}"
            if item.observations:
                line += f" ({item.observations})"
            lines.append(line)

        if self.delivery_address:
            lines.append(f"Endereço: {self.delivery_address}")
        if self.payment_method:
            lines.append(f"Pagamento: {self.payment_method}")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Serialize to dictionary for Redis storage."""
        return {
            "restaurant_id": str(self.restaurant_id),
            "customer_phone": self.customer_phone,
            "customer_name": self.customer_name,
            "status": self.status.value,
            "items": [item.to_dict() for item in self.items],
            "delivery_address": self.delivery_address,
            "payment_method": self.payment_method,
            "observations": self.observations,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OrderState":
        """Deserialize from dictionary."""
        items = [OrderItem.from_dict(item_data) for item_data in data.get("items", [])]

        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        else:
            created_at = datetime.now(timezone.utc)

        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        else:
            updated_at = datetime.now(timezone.utc)

        return cls(
            restaurant_id=UUID(data["restaurant_id"]),
            customer_phone=data["customer_phone"],
            customer_name=data.get("customer_name"),
            status=OrderStatus(data.get("status", "browsing")),
            items=items,
            delivery_address=data.get("delivery_address"),
            payment_method=data.get("payment_method"),
            observations=data.get("observations"),
            created_at=created_at,
            updated_at=updated_at,
        )

    @classmethod
    def create(
        cls,
        restaurant_id: UUID,
        customer_phone: str,
        customer_name: Optional[str] = None,
    ) -> "OrderState":
        """Factory method to create a new order state."""
        return cls(
            restaurant_id=restaurant_id,
            customer_phone=customer_phone,
            customer_name=customer_name,
        )
