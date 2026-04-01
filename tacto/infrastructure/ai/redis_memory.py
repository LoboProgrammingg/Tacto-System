"""
Redis Memory Adapter.

Implements short-term and medium-term memory storage using Redis.
"""

import json
from datetime import datetime
from typing import Optional
from uuid import UUID

import structlog

from tacto.domain.customer_memory.value_objects.memory_entry import MemoryEntry, MemoryType
from tacto.domain.customer_memory.ports.memory_port import MemoryPort
from tacto.shared.application import Err, Failure, Ok, Success
from tacto.infrastructure.redis.redis_client import RedisClient


logger = structlog.get_logger()


class RedisMemoryAdapter(MemoryPort):
    """
    Redis implementation for short-term and medium-term memory.

    TTLs:
    - Short-term: 30 minutes (current conversation)
    - Medium-term: 24 hours (recent interactions summary)
    """

    SHORT_TERM_TTL = 1800  # 30 minutes
    MEDIUM_TERM_TTL = 86400  # 24 hours

    def __init__(self, redis_client: RedisClient) -> None:
        """Initialize with Redis client."""
        self._redis = redis_client

    def _make_key(
        self,
        restaurant_id: UUID,
        customer_phone: str,
        memory_type: MemoryType,
    ) -> str:
        """Generate Redis key for memory storage."""
        return f"memory:{restaurant_id}:{customer_phone}:{memory_type.value}"

    def _get_ttl(self, memory_type: MemoryType) -> int:
        """Get TTL for memory type."""
        if memory_type == MemoryType.SHORT_TERM:
            return self.SHORT_TERM_TTL
        elif memory_type == MemoryType.MEDIUM_TERM:
            return self.MEDIUM_TERM_TTL
        return self.SHORT_TERM_TTL

    async def store(
        self,
        restaurant_id: UUID,
        customer_phone: str,
        entry: MemoryEntry,
    ) -> Success[bool] | Failure[Exception]:
        """Store memory entry in Redis."""
        try:
            key = self._make_key(restaurant_id, customer_phone, entry.memory_type)
            ttl = self._get_ttl(entry.memory_type)

            entry_data = {
                "key": entry.key,
                "content": entry.content,
                "memory_type": entry.memory_type.value,
                "timestamp": entry.timestamp.isoformat(),
                "metadata": entry.metadata,
                "relevance_score": entry.relevance_score,
            }

            result = await self._redis.rpush(key, json.dumps(entry_data))

            if isinstance(result, Failure):
                return result

            await self._redis.expire(key, ttl)

            return Ok(True)

        except Exception as e:
            logger.error("Redis memory store error", error=str(e))
            return Err(e)

    async def retrieve(
        self,
        restaurant_id: UUID,
        customer_phone: str,
        memory_type: MemoryType,
        limit: int = 10,
    ) -> Success[list[MemoryEntry]] | Failure[Exception]:
        """Retrieve memory entries from Redis."""
        try:
            key = self._make_key(restaurant_id, customer_phone, memory_type)

            result = await self._redis.lrange(key, -limit, -1)

            if isinstance(result, Failure):
                return result

            entries = []
            for item in result.value:
                data = json.loads(item)
                entries.append(
                    MemoryEntry(
                        key=data["key"],
                        content=data["content"],
                        memory_type=MemoryType(data["memory_type"]),
                        timestamp=datetime.fromisoformat(data["timestamp"]),
                        metadata=data.get("metadata", {}),
                        relevance_score=data.get("relevance_score", 1.0),
                    )
                )

            return Ok(entries)

        except Exception as e:
            logger.error("Redis memory retrieve error", error=str(e))
            return Err(e)

    async def search(
        self,
        restaurant_id: UUID,
        customer_phone: str,
        query: str,
        limit: int = 5,
    ) -> Success[list[MemoryEntry]] | Failure[Exception]:
        """
        Search memories (basic text matching for Redis).

        Note: For semantic search, use PostgresMemoryAdapter with pgvector.
        """
        try:
            all_entries = []

            for memory_type in [MemoryType.SHORT_TERM, MemoryType.MEDIUM_TERM]:
                result = await self.retrieve(
                    restaurant_id, customer_phone, memory_type, limit=50
                )
                if isinstance(result, Success):
                    all_entries.extend(result.value)

            query_lower = query.lower()
            matching = [
                e for e in all_entries
                if query_lower in e.content.lower()
            ]

            return Ok(matching[:limit])

        except Exception as e:
            logger.error("Redis memory search error", error=str(e))
            return Err(e)

    async def clear(
        self,
        restaurant_id: UUID,
        customer_phone: str,
        memory_type: Optional[MemoryType] = None,
    ) -> Success[bool] | Failure[Exception]:
        """Clear memories."""
        try:
            if memory_type:
                key = self._make_key(restaurant_id, customer_phone, memory_type)
                await self._redis.delete(key)
            else:
                for mt in [MemoryType.SHORT_TERM, MemoryType.MEDIUM_TERM]:
                    key = self._make_key(restaurant_id, customer_phone, mt)
                    await self._redis.delete(key)

            return Ok(True)

        except Exception as e:
            logger.error("Redis memory clear error", error=str(e))
            return Err(e)
