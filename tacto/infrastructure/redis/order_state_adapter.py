"""
Redis Order State Adapter.

Infrastructure implementation of OrderStatePort using Redis.
Provides persistence for order state during Level 2 conversations.
"""

from typing import Optional
from uuid import UUID

import structlog

from tacto.config import get_settings
from tacto.domain.order.ports import OrderStatePort
from tacto.domain.order.value_objects.order_state import OrderState
from tacto.infrastructure.redis.redis_client import RedisClient
from tacto.shared.application import Err, Failure, Ok, Success


logger = structlog.get_logger()


class RedisOrderStateAdapter(OrderStatePort):
    """
    Redis implementation of OrderStatePort.

    Stores order state as JSON with configurable TTL.
    Key format: tacto:order:{restaurant_id}:{customer_phone}
    """

    KEY_PREFIX = "tacto:order"

    def __init__(
        self,
        redis_client: RedisClient,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """
        Initialize adapter.

        Args:
            redis_client: Redis client instance
            ttl_seconds: Session TTL in seconds (default from settings)
        """
        self._redis = redis_client
        settings = get_settings()
        self._ttl = ttl_seconds or settings.level2.order_session_ttl

    def _key(self, restaurant_id: UUID, customer_phone: str) -> str:
        """Build Redis key for order state."""
        return f"{self.KEY_PREFIX}:{restaurant_id}:{customer_phone}"

    async def get(
        self, restaurant_id: UUID, customer_phone: str
    ) -> Success[Optional[OrderState]] | Failure[Exception]:
        """Retrieve order state from Redis."""
        key = self._key(restaurant_id, customer_phone)

        try:
            result = await self._redis.get_json(key)

            if isinstance(result, Failure):
                return result

            if result.value is None:
                return Ok(None)

            order = OrderState.from_dict(result.value)
            return Ok(order)

        except Exception as e:
            logger.error(
                "Failed to get order state",
                key=key,
                error=str(e),
            )
            return Err(e)

    async def save(self, order: OrderState) -> Success[bool] | Failure[Exception]:
        """Save order state to Redis with TTL refresh."""
        key = self._key(order.restaurant_id, order.customer_phone)

        try:
            result = await self._redis.set_json(key, order.to_dict(), self._ttl)

            if isinstance(result, Failure):
                return result

            logger.debug(
                "Order state saved",
                key=key,
                status=order.status.value,
                item_count=order.item_count,
                ttl=self._ttl,
            )
            return Ok(True)

        except Exception as e:
            logger.error(
                "Failed to save order state",
                key=key,
                error=str(e),
            )
            return Err(e)

    async def delete(
        self, restaurant_id: UUID, customer_phone: str
    ) -> Success[bool] | Failure[Exception]:
        """Remove order state from Redis."""
        key = self._key(restaurant_id, customer_phone)

        try:
            result = await self._redis.delete(key)

            if isinstance(result, Failure):
                return result

            logger.debug("Order state deleted", key=key)
            return Ok(True)

        except Exception as e:
            logger.error(
                "Failed to delete order state",
                key=key,
                error=str(e),
            )
            return Err(e)

    async def exists(
        self, restaurant_id: UUID, customer_phone: str
    ) -> Success[bool] | Failure[Exception]:
        """Check if order state exists in Redis."""
        key = self._key(restaurant_id, customer_phone)

        try:
            result = await self._redis.exists(key)

            if isinstance(result, Failure):
                return result

            return Ok(result.value)

        except Exception as e:
            logger.error(
                "Failed to check order state existence",
                key=key,
                error=str(e),
            )
            return Err(e)
