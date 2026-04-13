"""
MessageBufferService — Application Service.

Implements the intelligent message buffering strategy:
- Combines rapid consecutive messages from the same customer within a time window.
- Uses Redis for distributed coordination (list + lock).
- Falls back to immediate processing if Redis is unavailable.

ADR-002: Message Buffer Strategy
"""

import asyncio
import json
from typing import Optional

import structlog

from tacto.application.dto.message_dto import IncomingMessageDTO
from tacto.config.settings import get_settings


logger = structlog.get_logger()

_BUFFER_KEY_PREFIX = "tacto:msg_buffer:"
_BUFFER_LOCK_PREFIX = "tacto:msg_lock:"


class MessageBufferService:
    """
    Application service that buffers incoming messages before processing.

    Coordinates concurrent coroutines via Redis list + NX lock so only
    the last message in a rapid burst triggers the use case.
    """

    def __init__(self, redis_client=None) -> None:
        """
        Initialize buffer service.

        Args:
            redis_client: Connected RedisClient instance. If None or disconnected,
                          messages are processed immediately without buffering.
        """
        self._redis = redis_client
        _settings = get_settings()
        self._window_seconds = _settings.redis.buffer_window_seconds
        self._lock_ttl = _settings.redis.buffer_lock_ttl

    async def buffer_and_process(
        self,
        instance_key: str,
        phone: str,
        text: str,
        timestamp: int,
        message_id: str,
        push_name: str,
        process_callback,
    ) -> None:
        """
        Buffer the message and invoke process_callback when the window closes.

        Args:
            instance_key: Restaurant/canal identifier.
            phone: Sender phone number (clean, no suffix).
            text: Message text content.
            timestamp: Unix timestamp of the message.
            message_id: Join message ID.
            push_name: WhatsApp display name of the sender.
            process_callback: Async callable(IncomingMessageDTO) invoked once per burst.
        """
        if not self._redis or not self._redis.is_connected:
            await self._process_immediately(
                instance_key, phone, text, timestamp, message_id, push_name, process_callback
            )
            return

        buffer_key = f"{_BUFFER_KEY_PREFIX}{instance_key}:{phone}"
        lock_key = f"{_BUFFER_LOCK_PREFIX}{instance_key}:{phone}"

        msg_data = json.dumps({
            "text": text,
            "timestamp": timestamp,
            "message_id": message_id,
            "push_name": push_name,
        })

        push_result = await self._redis.rpush(buffer_key, msg_data)
        await self._redis.expire(buffer_key, self._lock_ttl * 3)

        my_position = push_result.value if push_result.is_success() else 1

        logger.info("message_buffered", phone=phone, position=my_position, text_preview=text[:30])

        await asyncio.sleep(self._window_seconds)

        buffer_result = await self._redis.lrange(buffer_key, 0, -1)
        current_size = len(buffer_result.value) if buffer_result.is_success() else 0

        if current_size != my_position:
            logger.debug(
                "buffer_skip",
                phone=phone,
                reason="newer_messages_exist",
                my_pos=my_position,
                current=current_size,
            )
            return

        lock_acquired = False
        for attempt in range(3):
            lock_result = await self._redis.set(lock_key, "1", ttl=self._lock_ttl, nx=True)
            if lock_result.is_success() and lock_result.value:
                lock_acquired = True
                break
            backoff = (attempt + 1) * 2
            logger.debug(
                "buffer_lock_retry",
                phone=phone,
                attempt=attempt + 1,
                backoff_seconds=backoff,
            )
            await asyncio.sleep(backoff)

        if not lock_acquired:
            logger.warning("buffer_lock_failed_processing_immediately", phone=phone)
            await self._process_immediately(
                instance_key, phone, text, timestamp, message_id, push_name, process_callback
            )
            return

        messages = buffer_result.value if buffer_result.is_success() else []
        await self._redis.delete(buffer_key)

        if not messages:
            await self._redis.delete(lock_key)
            return

        combined_text, latest_timestamp, latest_push_name = self._combine_messages(
            messages, timestamp, push_name
        )

        logger.info(
            "buffer_processing",
            phone=phone,
            message_count=len(messages),
            combined_preview=combined_text[:60],
        )

        dto = IncomingMessageDTO(
            instance_key=instance_key,
            from_phone=phone,
            body=combined_text,
            from_me=False,
            source="app",
            timestamp=latest_timestamp,
            message_id=message_id,
            push_name=latest_push_name,
        )

        try:
            await process_callback(dto)
        finally:
            await self._redis.delete(lock_key)

    async def _process_immediately(
        self,
        instance_key: str,
        phone: str,
        text: str,
        timestamp: int,
        message_id: str,
        push_name: str,
        process_callback,
    ) -> None:
        """Fallback: process without buffering when Redis is unavailable."""
        dto = IncomingMessageDTO(
            instance_key=instance_key,
            from_phone=phone,
            body=text,
            from_me=False,
            source="app",
            timestamp=timestamp,
            message_id=message_id,
            push_name=push_name,
        )
        await process_callback(dto)

    @staticmethod
    def _combine_messages(
        raw_messages: list,
        fallback_timestamp: int,
        fallback_push_name: str,
    ) -> tuple[str, int, str]:
        """
        Parse and combine all buffered message payloads.

        Returns:
            Tuple of (combined_text, latest_timestamp, latest_push_name).
        """
        texts: list[str] = []
        latest_timestamp = fallback_timestamp
        latest_push_name = fallback_push_name

        for msg_json in raw_messages:
            try:
                msg = json.loads(msg_json)
                texts.append(msg["text"])
                if msg["timestamp"] > latest_timestamp:
                    latest_timestamp = msg["timestamp"]
                    latest_push_name = msg.get("push_name", fallback_push_name)
            except (json.JSONDecodeError, KeyError):
                continue

        combined = " ".join(texts) if len(texts) > 1 else (texts[0] if texts else "")
        return combined, latest_timestamp, latest_push_name
