"""
Order State Service.

Application service for managing order state during Level 2 conversations.
Orchestrates order persistence and provides business operations.
"""

from typing import Optional
from uuid import UUID

import structlog

from tacto.domain.order.ports import OrderStatePort
from tacto.domain.order.value_objects.order_item import OrderItem
from tacto.domain.order.value_objects.order_state import OrderState
from tacto.domain.order.value_objects.order_status import OrderStatus
from tacto.shared.application import Err, Failure, Ok, Success


logger = structlog.get_logger()


class OrderStateService:
    """
    Application service for order state management.

    Provides high-level operations for the Level 2 agent:
    - Get or create order session
    - Add/remove items with validation
    - Transition order through states
    - Calculate totals
    """

    def __init__(self, order_state_port: OrderStatePort) -> None:
        """
        Initialize service with required port.

        Args:
            order_state_port: Infrastructure adapter for order persistence
        """
        self._port = order_state_port

    async def get_or_create(
        self,
        restaurant_id: UUID,
        customer_phone: str,
        customer_name: Optional[str] = None,
    ) -> Success[OrderState] | Failure[Exception]:
        """
        Get existing order or create new one.

        This is the main entry point for order operations.
        """
        log = logger.bind(
            restaurant_id=str(restaurant_id),
            customer_phone=customer_phone,
        )

        result = await self._port.get(restaurant_id, customer_phone)

        if isinstance(result, Failure):
            log.error("Failed to get order state", error=str(result.error))
            return result

        if result.value is not None:
            log.debug("Found existing order", status=result.value.status.value)
            return Ok(result.value)

        order = OrderState.create(
            restaurant_id=restaurant_id,
            customer_phone=customer_phone,
            customer_name=customer_name,
        )

        save_result = await self._port.save(order)
        if isinstance(save_result, Failure):
            log.error("Failed to create order", error=str(save_result.error))
            return save_result

        log.info("Created new order session")
        return Ok(order)

    async def get_current(
        self, restaurant_id: UUID, customer_phone: str
    ) -> Success[Optional[OrderState]] | Failure[Exception]:
        """Get current order state if exists."""
        return await self._port.get(restaurant_id, customer_phone)

    async def add_item(
        self,
        restaurant_id: UUID,
        customer_phone: str,
        item: OrderItem,
    ) -> Success[OrderState] | Failure[Exception]:
        """
        Add item to order.

        Creates order if doesn't exist.
        """
        log = logger.bind(
            restaurant_id=str(restaurant_id),
            customer_phone=customer_phone,
            item_name=item.name,
        )

        order_result = await self.get_or_create(restaurant_id, customer_phone)
        if isinstance(order_result, Failure):
            return order_result

        order = order_result.value

        try:
            order.add_item(item)
        except ValueError as e:
            log.warning("Cannot add item", error=str(e))
            return Err(e)

        save_result = await self._port.save(order)
        if isinstance(save_result, Failure):
            return save_result

        log.info(
            "Item added to order",
            quantity=item.quantity,
            price=item.unit_price,
            total_items=order.item_count,
        )
        return Ok(order)

    async def remove_item(
        self,
        restaurant_id: UUID,
        customer_phone: str,
        item_name: str,
        variation: Optional[str] = None,
    ) -> Success[OrderState] | Failure[Exception]:
        """Remove item from order."""
        log = logger.bind(
            restaurant_id=str(restaurant_id),
            customer_phone=customer_phone,
            item_name=item_name,
        )

        order_result = await self._port.get(restaurant_id, customer_phone)
        if isinstance(order_result, Failure):
            return order_result

        order = order_result.value
        if order is None:
            return Err(ValueError("No active order found"))

        removed = order.remove_item(item_name, variation)
        if removed is None:
            return Err(ValueError(f"Item not found: {item_name}"))

        save_result = await self._port.save(order)
        if isinstance(save_result, Failure):
            return save_result

        log.info("Item removed from order", removed_item=removed.name)
        return Ok(order)

    async def clear_order(
        self, restaurant_id: UUID, customer_phone: str
    ) -> Success[OrderState] | Failure[Exception]:
        """Clear all items from order."""
        order_result = await self._port.get(restaurant_id, customer_phone)
        if isinstance(order_result, Failure):
            return order_result

        order = order_result.value
        if order is None:
            return Err(ValueError("No active order found"))

        order.clear()

        save_result = await self._port.save(order)
        if isinstance(save_result, Failure):
            return save_result

        return Ok(order)

    async def set_delivery_address(
        self,
        restaurant_id: UUID,
        customer_phone: str,
        address: str,
    ) -> Success[OrderState] | Failure[Exception]:
        """Set delivery address for order."""
        order_result = await self._port.get(restaurant_id, customer_phone)
        if isinstance(order_result, Failure):
            return order_result

        order = order_result.value
        if order is None:
            return Err(ValueError("No active order found"))

        try:
            order.set_delivery_address(address)
        except ValueError as e:
            return Err(e)

        save_result = await self._port.save(order)
        if isinstance(save_result, Failure):
            return save_result

        logger.info(
            "Delivery address set",
            restaurant_id=str(restaurant_id),
            customer_phone=customer_phone,
        )
        return Ok(order)

    async def set_payment_method(
        self,
        restaurant_id: UUID,
        customer_phone: str,
        payment_method: str,
    ) -> Success[OrderState] | Failure[Exception]:
        """Set payment method for order."""
        order_result = await self._port.get(restaurant_id, customer_phone)
        if isinstance(order_result, Failure):
            return order_result

        order = order_result.value
        if order is None:
            return Err(ValueError("No active order found"))

        try:
            order.set_payment_method(payment_method)
        except ValueError as e:
            return Err(e)

        save_result = await self._port.save(order)
        if isinstance(save_result, Failure):
            return save_result

        logger.info(
            "Payment method set",
            restaurant_id=str(restaurant_id),
            customer_phone=customer_phone,
            method=payment_method,
        )
        return Ok(order)

    async def confirm_order(
        self, restaurant_id: UUID, customer_phone: str
    ) -> Success[OrderState] | Failure[Exception]:
        """
        Confirm order and prepare for submission.

        After confirmation, the order should be sent to Tacto API.
        """
        order_result = await self._port.get(restaurant_id, customer_phone)
        if isinstance(order_result, Failure):
            return order_result

        order = order_result.value
        if order is None:
            return Err(ValueError("No active order found"))

        try:
            order.confirm()
        except ValueError as e:
            return Err(e)

        save_result = await self._port.save(order)
        if isinstance(save_result, Failure):
            return save_result

        logger.info(
            "Order confirmed",
            restaurant_id=str(restaurant_id),
            customer_phone=customer_phone,
            total=order.total,
            item_count=order.item_count,
        )
        return Ok(order)

    async def cancel_order(
        self, restaurant_id: UUID, customer_phone: str
    ) -> Success[bool] | Failure[Exception]:
        """Cancel and remove order."""
        order_result = await self._port.get(restaurant_id, customer_phone)
        if isinstance(order_result, Failure):
            return order_result

        order = order_result.value
        if order is None:
            return Ok(True)

        order.cancel()

        delete_result = await self._port.delete(restaurant_id, customer_phone)
        if isinstance(delete_result, Failure):
            return delete_result

        logger.info(
            "Order cancelled",
            restaurant_id=str(restaurant_id),
            customer_phone=customer_phone,
        )
        return Ok(True)

    async def finalize_order(
        self, restaurant_id: UUID, customer_phone: str
    ) -> Success[bool] | Failure[Exception]:
        """
        Finalize order after successful submission to Tacto.

        Cleans up the order state from Redis.
        """
        return await self._port.delete(restaurant_id, customer_phone)
