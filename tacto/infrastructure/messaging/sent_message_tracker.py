"""
Sent Message Tracker.

Tracks AI-sent messages to distinguish from human operator messages.
Uses Redis with short TTL.

Detection strategy (in order):
1. message_id match  — most precise, TTL=300s
2. content hash match — Join API doesn't return message_id, so we hash the
                        exact text sent; echo always has identical content.
                        Human messages almost never match. TTL=60s.
"""

import hashlib
from typing import Optional

from tacto.config.settings import get_settings
from tacto.infrastructure.redis.redis_client import RedisClient


_PREFIX_ID   = "tacto:sent_msg_id:"
_PREFIX_HASH = "tacto:sent_msg_hash:"


class SentMessageTracker:
    """Tracks AI-sent messages by message_id and content hash."""

    def __init__(self, redis_client: Optional[RedisClient] = None) -> None:
        self._redis = redis_client
        _settings = get_settings()
        self._ttl_message_id = _settings.redis.message_id_tracker_ttl
        self._ttl_hash = self._ttl_message_id  # Match message_id TTL — Join echoes can be slow

    async def track_sent_message(
        self,
        instance_key: str,
        phone: str,
        message_id: Optional[str] = None,
        message_text: Optional[str] = None,
    ) -> None:
        """Track message as AI-sent (by message_id and/or content hash)."""
        if not self._redis or not self._redis.is_connected:
            return

        if message_id:
            await self._redis.set(
                f"{_PREFIX_ID}{instance_key}:{message_id}",
                "1",
                ttl=self._ttl_message_id,
            )

        if phone and message_text:
            clean_phone = phone.replace("@s.whatsapp.net", "").replace("@c.us", "")
            content_hash = hashlib.md5(message_text.encode("utf-8")).hexdigest()
            redis_key = f"{_PREFIX_HASH}{instance_key}:{clean_phone}:{content_hash}"
            await self._redis.set(redis_key, "1", ttl=self._ttl_hash)

    async def is_ai_sent_message(
        self,
        instance_key: str,
        message_id: str,
        phone: Optional[str] = None,
        echo_text: Optional[str] = None,
    ) -> bool:
        """
        Check if a from_me=True message was sent by the AI (not a human).

        1. Check by message_id (when Join API returns it).
        2. Fallback: check by content hash (for Join API that returns no message_id).
           The echo always carries the exact same text the AI sent.
           A human operator will virtually never send identical content.
        """
        if not self._redis or not self._redis.is_connected:
            return False

        if message_id:
            result = await self._redis.exists(f"{_PREFIX_ID}{instance_key}:{message_id}")
            if result.is_success() and result.value:
                return True

        if phone and echo_text:
            clean_phone = phone.replace("@s.whatsapp.net", "").replace("@c.us", "")
            content_hash = hashlib.md5(echo_text.encode("utf-8")).hexdigest()
            redis_key = f"{_PREFIX_HASH}{instance_key}:{clean_phone}:{content_hash}"
            result = await self._redis.exists(redis_key)
            if result.is_success() and result.value:
                return True

        return False
