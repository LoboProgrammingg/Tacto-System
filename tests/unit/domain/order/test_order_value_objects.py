"""
Unit tests for Order domain value objects.

Tests OrderItem, OrderStatus, and OrderState following DDD principles.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from tacto.domain.order.value_objects.order_item import OrderItem
from tacto.domain.order.value_objects.order_state import OrderState
from tacto.domain.order.value_objects.order_status import OrderStatus


class TestOrderStatus:
    """Tests for OrderStatus enum."""

    def test_is_active_for_in_progress_statuses(self):
        """Active statuses should return True for is_active."""
        active_statuses = [
            OrderStatus.BROWSING,
            OrderStatus.ADDING_ITEMS,
            OrderStatus.REVIEWING,
            OrderStatus.COLLECTING_ADDRESS,
            OrderStatus.COLLECTING_PAYMENT,
            OrderStatus.CONFIRMING,
        ]
        for status in active_statuses:
            assert status.is_active is True, f"{status} should be active"

    def test_is_active_for_terminal_statuses(self):
        """Terminal statuses should return False for is_active."""
        terminal_statuses = [
            OrderStatus.CONFIRMED,
            OrderStatus.CANCELLED,
        ]
        for status in terminal_statuses:
            assert status.is_active is False, f"{status} should not be active"

    def test_can_add_items(self):
        """Only certain statuses allow adding items."""
        can_add = [
            OrderStatus.BROWSING,
            OrderStatus.ADDING_ITEMS,
            OrderStatus.REVIEWING,
        ]
        cannot_add = [
            OrderStatus.COLLECTING_ADDRESS,
            OrderStatus.COLLECTING_PAYMENT,
            OrderStatus.CONFIRMING,
            OrderStatus.CONFIRMED,
            OrderStatus.CANCELLED,
        ]

        for status in can_add:
            assert status.can_add_items is True, f"{status} should allow adding items"

        for status in cannot_add:
            assert status.can_add_items is False, f"{status} should not allow adding items"


class TestOrderItem:
    """Tests for OrderItem value object."""

    def test_create_valid_item(self):
        """Should create item with valid data."""
        item = OrderItem(
            name="Pizza Calabresa",
            quantity=2,
            unit_price=45.90,
            variation="Grande",
            observations="Sem cebola",
        )

        assert item.name == "Pizza Calabresa"
        assert item.quantity == 2
        assert item.unit_price == 45.90
        assert item.variation == "Grande"
        assert item.observations == "Sem cebola"

    def test_total_price_calculation(self):
        """Should calculate total price correctly."""
        item = OrderItem(name="Pizza", quantity=3, unit_price=40.00)
        assert item.total_price == 120.00

    def test_display_name_with_variation(self):
        """Should include variation in display name."""
        item = OrderItem(name="Pizza", quantity=1, unit_price=40.00, variation="Grande")
        assert item.display_name == "Pizza (Grande)"

    def test_display_name_without_variation(self):
        """Should show just name without variation."""
        item = OrderItem(name="Pizza", quantity=1, unit_price=40.00)
        assert item.display_name == "Pizza"

    def test_matches_same_name(self):
        """Should match items with same name (case insensitive)."""
        item = OrderItem(name="Pizza Calabresa", quantity=1, unit_price=40.00)
        assert item.matches("Pizza Calabresa") is True
        assert item.matches("pizza calabresa") is True
        assert item.matches("PIZZA CALABRESA") is True

    def test_matches_with_variation(self):
        """Should match items with same name and variation."""
        item = OrderItem(
            name="Pizza Calabresa",
            quantity=1,
            unit_price=40.00,
            variation="Grande",
        )
        assert item.matches("Pizza Calabresa", "Grande") is True
        assert item.matches("Pizza Calabresa", "grande") is True
        assert item.matches("Pizza Calabresa", "Média") is False

    def test_invalid_quantity_raises(self):
        """Should raise ValueError for invalid quantity."""
        with pytest.raises(ValueError, match="Quantity must be at least 1"):
            OrderItem(name="Pizza", quantity=0, unit_price=40.00)

    def test_invalid_price_raises(self):
        """Should raise ValueError for negative price."""
        with pytest.raises(ValueError, match="Unit price cannot be negative"):
            OrderItem(name="Pizza", quantity=1, unit_price=-10.00)

    def test_empty_name_raises(self):
        """Should raise ValueError for empty name."""
        with pytest.raises(ValueError, match="Item name cannot be empty"):
            OrderItem(name="", quantity=1, unit_price=40.00)

    def test_with_quantity_returns_new_item(self):
        """Should return new item with updated quantity."""
        original = OrderItem(name="Pizza", quantity=1, unit_price=40.00)
        updated = original.with_quantity(3)

        assert original.quantity == 1
        assert updated.quantity == 3
        assert updated.name == original.name
        assert updated.unit_price == original.unit_price

    def test_serialization_roundtrip(self):
        """Should serialize and deserialize correctly."""
        original = OrderItem(
            name="Pizza Calabresa",
            quantity=2,
            unit_price=45.90,
            variation="Grande",
            observations="Sem cebola",
        )

        data = original.to_dict()
        restored = OrderItem.from_dict(data)

        assert restored.name == original.name
        assert restored.quantity == original.quantity
        assert restored.unit_price == original.unit_price
        assert restored.variation == original.variation
        assert restored.observations == original.observations


class TestOrderState:
    """Tests for OrderState aggregate."""

    @pytest.fixture
    def restaurant_id(self):
        return uuid4()

    @pytest.fixture
    def empty_order(self, restaurant_id):
        return OrderState.create(
            restaurant_id=restaurant_id,
            customer_phone="5511999999999",
            customer_name="João",
        )

    def test_create_empty_order(self, empty_order):
        """Should create order with empty cart."""
        assert empty_order.is_empty is True
        assert empty_order.item_count == 0
        assert empty_order.subtotal == 0.0
        assert empty_order.status == OrderStatus.BROWSING

    def test_add_item(self, empty_order):
        """Should add item to cart."""
        item = OrderItem(name="Pizza", quantity=1, unit_price=40.00)
        empty_order.add_item(item)

        assert empty_order.is_empty is False
        assert empty_order.item_count == 1
        assert empty_order.subtotal == 40.00
        assert empty_order.status == OrderStatus.ADDING_ITEMS

    def test_add_same_item_increases_quantity(self, empty_order):
        """Should increase quantity when adding same item."""
        item1 = OrderItem(name="Pizza", quantity=1, unit_price=40.00)
        item2 = OrderItem(name="Pizza", quantity=2, unit_price=40.00)

        empty_order.add_item(item1)
        empty_order.add_item(item2)

        assert len(empty_order.items) == 1
        assert empty_order.items[0].quantity == 3
        assert empty_order.subtotal == 120.00

    def test_add_different_items(self, empty_order):
        """Should add different items separately."""
        pizza = OrderItem(name="Pizza", quantity=1, unit_price=40.00)
        soda = OrderItem(name="Refrigerante", quantity=2, unit_price=8.00)

        empty_order.add_item(pizza)
        empty_order.add_item(soda)

        assert len(empty_order.items) == 2
        assert empty_order.item_count == 3
        assert empty_order.subtotal == 56.00

    def test_remove_item(self, empty_order):
        """Should remove item from cart."""
        item = OrderItem(name="Pizza", quantity=1, unit_price=40.00)
        empty_order.add_item(item)

        removed = empty_order.remove_item("Pizza")

        assert removed is not None
        assert removed.name == "Pizza"
        assert empty_order.is_empty is True

    def test_remove_nonexistent_item_returns_none(self, empty_order):
        """Should return None when removing nonexistent item."""
        removed = empty_order.remove_item("Pizza")
        assert removed is None

    def test_clear_cart(self, empty_order):
        """Should clear all items from cart."""
        empty_order.add_item(OrderItem(name="Pizza", quantity=1, unit_price=40.00))
        empty_order.add_item(OrderItem(name="Soda", quantity=2, unit_price=8.00))

        empty_order.clear()

        assert empty_order.is_empty is True
        assert empty_order.status == OrderStatus.BROWSING

    def test_set_delivery_address(self, empty_order):
        """Should set delivery address and advance status."""
        empty_order.add_item(OrderItem(name="Pizza", quantity=1, unit_price=40.00))
        empty_order.start_collecting_address()
        empty_order.set_delivery_address("Rua das Flores, 123")

        assert empty_order.delivery_address == "Rua das Flores, 123"
        assert empty_order.status == OrderStatus.COLLECTING_PAYMENT

    def test_set_delivery_address_empty_cart_raises(self, empty_order):
        """Should raise when setting address with empty cart."""
        with pytest.raises(ValueError, match="Cannot set address with empty cart"):
            empty_order.set_delivery_address("Rua das Flores, 123")

    def test_set_payment_method(self, empty_order):
        """Should set payment method and advance to confirming."""
        empty_order.add_item(OrderItem(name="Pizza", quantity=1, unit_price=40.00))
        empty_order.start_collecting_address()
        empty_order.set_delivery_address("Rua das Flores, 123")
        empty_order.set_payment_method("PIX")

        assert empty_order.payment_method == "PIX"
        assert empty_order.status == OrderStatus.CONFIRMING

    def test_confirm_order(self, empty_order):
        """Should confirm order when all info collected."""
        empty_order.add_item(OrderItem(name="Pizza", quantity=1, unit_price=40.00))
        empty_order.start_collecting_address()
        empty_order.set_delivery_address("Rua das Flores, 123")
        empty_order.set_payment_method("PIX")
        empty_order.confirm()

        assert empty_order.status == OrderStatus.CONFIRMED
        assert empty_order.is_active is False

    def test_cancel_order(self, empty_order):
        """Should cancel order at any point."""
        empty_order.add_item(OrderItem(name="Pizza", quantity=1, unit_price=40.00))
        empty_order.cancel()

        assert empty_order.status == OrderStatus.CANCELLED
        assert empty_order.is_active is False

    def test_to_summary_empty(self, empty_order):
        """Should show empty cart message."""
        summary = empty_order.to_summary()
        assert "vazio" in summary.lower()

    def test_to_summary_with_items(self, empty_order):
        """Should show items with prices."""
        empty_order.add_item(OrderItem(name="Pizza", quantity=2, unit_price=40.00))
        summary = empty_order.to_summary()

        assert "Pizza" in summary
        assert "80,00" in summary or "80.00" in summary

    def test_serialization_roundtrip(self, empty_order):
        """Should serialize and deserialize correctly."""
        empty_order.add_item(OrderItem(name="Pizza", quantity=2, unit_price=40.00))
        empty_order.start_collecting_address()
        empty_order.set_delivery_address("Rua das Flores, 123")

        data = empty_order.to_dict()
        restored = OrderState.from_dict(data)

        assert str(restored.restaurant_id) == str(empty_order.restaurant_id)
        assert restored.customer_phone == empty_order.customer_phone
        assert len(restored.items) == len(empty_order.items)
        assert restored.delivery_address == empty_order.delivery_address
        assert restored.status == empty_order.status
