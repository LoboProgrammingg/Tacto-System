"""
Redis Message Buffer Implementation.

Implements the MessageBufferPort for storing buffered messages in Redis.
"""

import json
from datetime import datetime
from typing import Optional

from tacto.domain.messaging.services.message_buffer_service import (
    BufferedMessage,
    MessageBufferPort,
)
from tacto.domain.shared.result import Err, Failure, Ok, Success
from tacto.infrastructure.redis.redis_client import RedisClient


class RedisMessageBuffer(MessageBufferPort):
    """
    Redis implementation of MessageBufferPort.

    Stores buffered messages as a Redis list with JSON serialization.
    """

    def __init__(self, redis_client: RedisClient) -> None:
        """
        Initialize buffer with Redis client.

        Args:
            redis_client: Redis client instance
        """
        self._redis = redis_client

    async def add_to_buffer(
        self, key: str, message: BufferedMessage, ttl_seconds: int
    ) -> Success[bool] | Failure[Exception]:
        """Add message to buffer list."""
        try:
            message_data = {
                "conversation_key": message.conversation_key,
                "body": message.body,
                "timestamp": message.timestamp.isoformat(),
                "instance_key": message.instance_key,
                "from_phone": message.from_phone,
                "source": message.source,
                "message_id": message.message_id,
                "push_name": message.push_name,
            }

            result = await self._redis.list_push(key, json.dumps(message_data))

            if isinstance(result, Failure):
                return result

            await self._redis.set_with_expiry(
                f"{key}:ttl", "1", ttl_seconds
            )

            return Ok(True)

        except Exception as e:
            return Err(e)

    async def get_buffer(
        self, key: str
    ) -> Success[list[BufferedMessage]] | Failure[Exception]:
        """Get all messages in buffer."""
        try:
            result = await self._redis.list_range(key, 0, -1)

            if isinstance(result, Failure):
                return result

            messages = []
            for item in result.value:
                data = json.loads(item)
                messages.append(
                    BufferedMessage(
                        conversation_key=data["conversation_key"],
                        body=data["body"],
                        timestamp=datetime.fromisoformat(data["timestamp"]),
                        instance_key=data["instance_key"],
                        from_phone=data["from_phone"],
                        source=data["source"],
                        message_id=data.get("message_id"),
                        push_name=data.get("push_name"),
                    )
                )

            return Ok(messages)

        except Exception as e:
            return Err(e)

    async def clear_buffer(self, key: str) -> Success[bool] | Failure[Exception]:
        """Clear buffer for key."""
        try:
            result = await self._redis.delete(key)

            if isinstance(result, Failure):
                return result

            await self._redis.delete(f"{key}:ttl")

            return Ok(True)

        except Exception as e:
            return Err(e)

    async def get_last_message_time(
        self, key: str
    ) -> Success[Optional[datetime]] | Failure[Exception]:
        """Get timestamp of last message in buffer."""
        try:
            result = await self._redis.list_range(key, -1, -1)

            if isinstance(result, Failure):
                return result

            if not result.value:
                return Ok(None)

            data = json.loads(result.value[0])
            timestamp = datetime.fromisoformat(data["timestamp"])

            return Ok(timestamp)

        except Exception as e:
            return Err(e)
