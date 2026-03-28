"""
Sent Message Tracker.

Tracks AI-sent messages to distinguish from human operator messages.
Uses Redis with short TTL for message_id and phone number tracking.
"""

from typing import Optional

from tacto.config.settings import get_settings
from tacto.infrastructure.redis.redis_client import RedisClient


_PREFIX_ID = "tacto:sent_msg_id:"
_PREFIX_NUM = "tacto:sent_msg_num:"


class SentMessageTracker:
    """Tracks AI-sent messages by message_id and phone number."""

    def __init__(self, redis_client: Optional[RedisClient] = None) -> None:
        self._redis = redis_client
        _settings = get_settings()
        self._ttl_message_id = _settings.redis.message_id_tracker_ttl
        self._ttl_phone = _settings.redis.echo_tracker_ttl

    async def track_sent_message(
        self,
        instance_key: str,
        phone: str,
        message_id: Optional[str] = None,
    ) -> None:
        """Track message as AI-sent (by message_id and phone number)."""
        if not self._redis or not self._redis.is_connected:
            return

        if message_id:
            await self._redis.set(f"{_PREFIX_ID}{instance_key}:{message_id}", "1", ttl=self._ttl_message_id)

        if phone:
            clean_phone = phone.replace("@s.whatsapp.net", "").replace("@c.us", "")
            await self._redis.set(f"{_PREFIX_NUM}{instance_key}:{clean_phone}", "1", ttl=self._ttl_phone)

    async def is_ai_sent_message(
        self,
        instance_key: str,
        message_id: str,
        phone: Optional[str] = None,
    ) -> bool:
        """Check if message was sent by AI (returns True if matched by id or phone)."""
        if not self._redis or not self._redis.is_connected:
            return True  # Assume AI to avoid false positives

        # Check by message_id
        if message_id:
            result = await self._redis.exists(f"{_PREFIX_ID}{instance_key}:{message_id}")
            if result.is_success() and result.value:
                return True

        # Check by phone number
        if phone:
            clean_phone = phone.replace("@s.whatsapp.net", "").replace("@c.us", "")
            result = await self._redis.exists(f"{_PREFIX_NUM}{instance_key}:{clean_phone}")
            if result.is_success() and result.value:
                return True

        return False
