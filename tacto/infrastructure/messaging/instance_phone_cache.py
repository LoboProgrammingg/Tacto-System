"""
Instance Phone Cache.

Caches the connected phone number for each Join instance in Redis.
Used to detect human operator messages in webhooks.
"""

from typing import Optional

import structlog

from tacto.infrastructure.redis.redis_client import RedisClient


logger = structlog.get_logger()

_PREFIX = "tacto:instance_phone:"
_TTL_SECONDS = 86400  # 24 hours


class InstancePhoneCache:
    """Caches instance_key -> connected phone number mapping."""

    def __init__(self, redis_client: Optional[RedisClient] = None) -> None:
        self._redis = redis_client

    async def set_instance_phone(self, instance_key: str, phone_number: str) -> None:
        """Cache the connected phone number for an instance."""
        if not self._redis or not self._redis.is_connected or not phone_number:
            return

        clean_phone = phone_number.replace("@s.whatsapp.net", "").replace("@c.us", "")
        key = f"{_PREFIX}{instance_key}"
        
        await self._redis.set(key, clean_phone, ttl=_TTL_SECONDS)
        logger.debug("instance_phone_cached", instance_key=instance_key, phone=clean_phone)

    async def get_instance_phone(self, instance_key: str) -> Optional[str]:
        """Get the connected phone number for an instance."""
        if not self._redis or not self._redis.is_connected:
            return None

        key = f"{_PREFIX}{instance_key}"
        result = await self._redis.get(key)
        
        if result.is_success() and result.value:
            return result.value
        return None

    async def is_instance_phone(self, instance_key: str, phone: str) -> bool:
        """Check if the given phone is the instance's connected phone (restaurant number)."""
        if not phone:
            return False
            
        clean_phone = phone.replace("@s.whatsapp.net", "").replace("@c.us", "")
        instance_phone = await self.get_instance_phone(instance_key)
        
        if not instance_phone:
            return False
            
        return clean_phone == instance_phone
