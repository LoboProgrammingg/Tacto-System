"""
Redis Client for TactoFlow.

Provides async Redis operations for caching, message buffering,
and short-term memory storage.
"""

import json
from typing import Any, Optional

import redis.asyncio as redis

from tacto.config import RedisSettings, get_settings
from tacto.shared.application import Err, Failure, Ok, Success


class RedisClient:
    """
    Async Redis client wrapper.

    Provides typed operations for:
    - Key-value storage
    - Message buffering
    - Short-term conversation memory
    """

    def __init__(self, settings: Optional[RedisSettings] = None) -> None:
        """
        Initialize Redis client.

        Args:
            settings: Redis settings. If None, loads from environment.
        """
        self._settings = settings or get_settings().redis
        self._client: Optional[redis.Redis] = None

    async def connect(self) -> Success[bool] | Failure[Exception]:
        """Establish connection to Redis."""
        try:
            self._client = redis.from_url(
                self._settings.url,
                encoding="utf-8",
                decode_responses=True,
            )
            await self._client.ping()
            return Ok(True)
        except Exception as e:
            return Err(e)

    async def disconnect(self) -> Success[bool] | Failure[Exception]:
        """Close Redis connection."""
        try:
            if self._client:
                await self._client.close()
                self._client = None
            return Ok(True)
        except Exception as e:
            return Err(e)

    async def get(self, key: str) -> Success[Optional[str]] | Failure[Exception]:
        """Get value by key."""
        try:
            if not self._client:
                return Err(ConnectionError("Redis not connected"))
            value = await self._client.get(key)
            return Ok(value)
        except Exception as e:
            return Err(e)

    async def set(
        self,
        key: str,
        value: str,
        ttl: Optional[int] = None,
        nx: bool = False,
    ) -> Success[bool] | Failure[Exception]:
        """
        Set key-value with optional TTL.

        Args:
            nx: If True, only set if key does not exist (SET NX).
                Returns Ok(False) if key already existed.
        """
        try:
            if not self._client:
                return Err(ConnectionError("Redis not connected"))
            result = await self._client.set(key, value, ex=ttl, nx=nx if nx else None)
            # SET NX returns None when key already exists
            return Ok(result is not False and result is not None if nx else True)
        except Exception as e:
            return Err(e)

    async def delete(self, key: str) -> Success[bool] | Failure[Exception]:
        """Delete key."""
        try:
            if not self._client:
                return Err(ConnectionError("Redis not connected"))
            await self._client.delete(key)
            return Ok(True)
        except Exception as e:
            return Err(e)

    async def get_json(self, key: str) -> Success[Optional[dict[str, Any]]] | Failure[Exception]:
        """Get and parse JSON value."""
        result = await self.get(key)
        if isinstance(result, Failure):
            return result
        if result.value is None:
            return Ok(None)
        try:
            return Ok(json.loads(result.value))
        except json.JSONDecodeError as e:
            return Err(e)

    async def set_json(
        self,
        key: str,
        value: dict[str, Any],
        ttl: Optional[int] = None,
    ) -> Success[bool] | Failure[Exception]:
        """Set JSON value."""
        try:
            json_str = json.dumps(value, default=str)
            return await self.set(key, json_str, ttl)
        except Exception as e:
            return Err(e)

    async def lpush(self, key: str, *values: str) -> Success[int] | Failure[Exception]:
        """Push values to list (left)."""
        try:
            if not self._client:
                return Err(ConnectionError("Redis not connected"))
            count = await self._client.lpush(key, *values)
            return Ok(count)
        except Exception as e:
            return Err(e)

    async def rpush(self, key: str, *values: str) -> Success[int] | Failure[Exception]:
        """Push values to list (right)."""
        try:
            if not self._client:
                return Err(ConnectionError("Redis not connected"))
            count = await self._client.rpush(key, *values)
            return Ok(count)
        except Exception as e:
            return Err(e)

    async def lrange(
        self, key: str, start: int = 0, end: int = -1
    ) -> Success[list[str]] | Failure[Exception]:
        """Get list range."""
        try:
            if not self._client:
                return Err(ConnectionError("Redis not connected"))
            values = await self._client.lrange(key, start, end)
            return Ok(values)
        except Exception as e:
            return Err(e)

    async def expire(self, key: str, ttl: int) -> Success[bool] | Failure[Exception]:
        """Set TTL on key."""
        try:
            if not self._client:
                return Err(ConnectionError("Redis not connected"))
            await self._client.expire(key, ttl)
            return Ok(True)
        except Exception as e:
            return Err(e)

    async def exists(self, key: str) -> Success[bool] | Failure[Exception]:
        """Check if key exists."""
        try:
            if not self._client:
                return Err(ConnectionError("Redis not connected"))
            result = await self._client.exists(key)
            return Ok(result > 0)
        except Exception as e:
            return Err(e)

    async def incr(self, key: str) -> Success[int] | Failure[Exception]:
        """Increment key value by 1. Creates key with value 1 if it doesn't exist."""
        try:
            if not self._client:
                return Err(ConnectionError("Redis not connected"))
            result = await self._client.incr(key)
            return Ok(result)
        except Exception as e:
            return Err(e)

    async def ttl(self, key: str) -> Success[int] | Failure[Exception]:
        """Get remaining TTL of a key in seconds. Returns -1 if no TTL, -2 if key doesn't exist."""
        try:
            if not self._client:
                return Err(ConnectionError("Redis not connected"))
            result = await self._client.ttl(key)
            return Ok(result)
        except Exception as e:
            return Err(e)

    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._client is not None
