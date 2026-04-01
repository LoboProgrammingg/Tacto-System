"""
Order Status Value Object.

Represents the possible states of an order during the conversation flow.
This is a pure domain enum with no external dependencies.
"""

from enum import Enum


class OrderStatus(str, Enum):
    """
    Status of an in-progress order.

    Follows the natural flow of a food ordering conversation:
    BROWSING → ADDING_ITEMS → REVIEWING → COLLECTING_ADDRESS → COLLECTING_PAYMENT → CONFIRMING → CONFIRMED
    """

    BROWSING = "browsing"
    """Customer is browsing the menu, asking questions."""

    ADDING_ITEMS = "adding_items"
    """Customer is actively adding items to the cart."""

    REVIEWING = "reviewing"
    """Customer is reviewing the current order."""

    COLLECTING_ADDRESS = "collecting_address"
    """System is collecting delivery address."""

    COLLECTING_PAYMENT = "collecting_payment"
    """System is collecting payment method."""

    CONFIRMING = "confirming"
    """Final confirmation before sending to restaurant."""

    AWAITING_HUMAN = "awaiting_human"
    """Customer confirmed order, waiting for human to finalize (Level 2 handoff)."""

    CONFIRMED = "confirmed"
    """Order confirmed and sent to restaurant."""

    CANCELLED = "cancelled"
    """Order cancelled by customer."""

    @property
    def is_active(self) -> bool:
        """Check if order is still in progress."""
        return self not in (OrderStatus.CONFIRMED, OrderStatus.CANCELLED, OrderStatus.AWAITING_HUMAN)

    @property
    def needs_human_handoff(self) -> bool:
        """Check if order is waiting for human to finalize."""
        return self == OrderStatus.AWAITING_HUMAN

    @property
    def is_collecting_info(self) -> bool:
        """Check if system is collecting delivery information."""
        return self in (
            OrderStatus.COLLECTING_ADDRESS,
            OrderStatus.COLLECTING_PAYMENT,
            OrderStatus.CONFIRMING,
        )

    @property
    def can_add_items(self) -> bool:
        """Check if items can still be added."""
        return self in (
            OrderStatus.BROWSING,
            OrderStatus.ADDING_ITEMS,
            OrderStatus.REVIEWING,
        )

    @property
    def requires_cart(self) -> bool:
        """Check if this status requires items in cart."""
        return self in (
            OrderStatus.REVIEWING,
            OrderStatus.COLLECTING_ADDRESS,
            OrderStatus.COLLECTING_PAYMENT,
            OrderStatus.CONFIRMING,
        )
