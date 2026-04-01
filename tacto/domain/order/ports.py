"""
Order Domain Ports.

Interfaces for order-related infrastructure operations.
Following Hexagonal Architecture / Ports & Adapters pattern.
"""

from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from tacto.domain.order.value_objects.order_state import OrderState
from tacto.shared.application import Failure, Success


class OrderStatePort(ABC):
    """
    Port for order state persistence.

    This interface defines how order state is stored and retrieved.
    Implementation can be Redis, database, or any other storage.
    """

    @abstractmethod
    async def get(
        self, restaurant_id: UUID, customer_phone: str
    ) -> Success[Optional[OrderState]] | Failure[Exception]:
        """
        Retrieve current order state for a customer.

        Returns None if no active order exists.
        """
        ...

    @abstractmethod
    async def save(self, order: OrderState) -> Success[bool] | Failure[Exception]:
        """
        Persist order state.

        Should update TTL on each save to keep session active.
        """
        ...

    @abstractmethod
    async def delete(
        self, restaurant_id: UUID, customer_phone: str
    ) -> Success[bool] | Failure[Exception]:
        """
        Remove order state (after confirmation or cancellation).
        """
        ...

    @abstractmethod
    async def exists(
        self, restaurant_id: UUID, customer_phone: str
    ) -> Success[bool] | Failure[Exception]:
        """Check if an active order exists."""
        ...
