"""
Memory Orchestration Service — Application Layer.

Coordinates between short-term (Redis), medium-term (Redis),
and long-term (PostgreSQL + pgvector) memory stores.

This service was moved from domain/ai/memory/memory_manager.py
during DDD refactoring (FASE 2) because it orchestrates I/O,
which is an Application Layer responsibility.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from tacto.config.settings import get_settings
from tacto.domain.customer_memory.value_objects.memory_entry import (
    ConversationMemory,
    MemoryEntry,
    MemoryType,
)
from tacto.domain.customer_memory.ports.memory_port import MemoryPort
from tacto.shared.application import Failure, Success


class MemoryOrchestrationService:
    """
    Manages multi-level memory for AI conversations.

    Coordinates between short-term (Redis), medium-term (Redis),
    and long-term (PostgreSQL + pgvector) memory stores.
    """

    def __init__(
        self,
        short_term_port: MemoryPort,
        long_term_port: MemoryPort,
    ) -> None:
        """
        Initialize memory orchestration service.

        Args:
            short_term_port: Redis-based storage for short/medium term
            long_term_port: PostgreSQL-based storage for long term
        """
        self._short_term = short_term_port
        self._long_term = long_term_port

    async def load_context(
        self,
        restaurant_id: UUID,
        customer_phone: str,
        customer_name: Optional[str] = None,
    ) -> Success[ConversationMemory] | Failure[Exception]:
        """
        Load complete memory context for a conversation.

        Retrieves memories from all three levels.
        """
        memory = ConversationMemory(
            restaurant_id=restaurant_id,
            customer_phone=customer_phone,
            customer_name=customer_name,
        )

        settings = get_settings()

        short_result = await self._short_term.retrieve(
            restaurant_id, customer_phone, MemoryType.SHORT_TERM,
            limit=settings.app.memory_short_term_limit
        )
        if isinstance(short_result, Success):
            memory.short_term = short_result.value

        medium_result = await self._short_term.retrieve(
            restaurant_id, customer_phone, MemoryType.MEDIUM_TERM,
            limit=settings.app.memory_medium_term_limit
        )
        if isinstance(medium_result, Success):
            memory.medium_term = medium_result.value

        long_result = await self._long_term.retrieve(
            restaurant_id, customer_phone, MemoryType.LONG_TERM,
            limit=settings.app.memory_long_term_limit
        )
        if isinstance(long_result, Success):
            memory.long_term = long_result.value

        return Success(memory)

    async def add_message(
        self,
        restaurant_id: UUID,
        customer_phone: str,
        role: str,
        content: str,
    ) -> Success[bool] | Failure[Exception]:
        """Add message to short-term memory."""
        entry = MemoryEntry(
            key=f"msg:{role}",
            content=content,
            memory_type=MemoryType.SHORT_TERM,
            timestamp=datetime.utcnow(),
            metadata={"role": role},
        )

        return await self._short_term.store(restaurant_id, customer_phone, entry)

    async def add_summary(
        self,
        restaurant_id: UUID,
        customer_phone: str,
        summary: str,
    ) -> Success[bool] | Failure[Exception]:
        """Add conversation summary to medium-term memory."""
        entry = MemoryEntry(
            key="summary",
            content=summary,
            memory_type=MemoryType.MEDIUM_TERM,
            timestamp=datetime.utcnow(),
        )

        return await self._short_term.store(restaurant_id, customer_phone, entry)

    async def add_preference(
        self,
        restaurant_id: UUID,
        customer_phone: str,
        preference: str,
        category: str = "general",
    ) -> Success[bool] | Failure[Exception]:
        """Add customer preference to long-term memory."""
        entry = MemoryEntry(
            key=f"pref:{category}",
            content=preference,
            memory_type=MemoryType.LONG_TERM,
            timestamp=datetime.utcnow(),
            metadata={"category": category},
        )

        return await self._long_term.store(restaurant_id, customer_phone, entry)

    async def search_relevant(
        self,
        restaurant_id: UUID,
        customer_phone: str,
        query: str,
        limit: int = 5,
    ) -> Success[list[MemoryEntry]] | Failure[Exception]:
        """Search for relevant memories using semantic search."""
        return await self._long_term.search(
            restaurant_id, customer_phone, query, limit
        )


# Alias for backward compatibility during migration
MemoryManager = MemoryOrchestrationService
