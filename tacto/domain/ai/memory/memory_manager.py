"""
AI Memory Manager.

Implements three-level memory system:
- Short-term: Current conversation context (Redis, 30min TTL)
- Medium-term: Recent interactions summary (Redis, 24h TTL)
- Long-term: Customer preferences and history (PostgreSQL + pgvector)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from tacto.domain.shared.result import Failure, Success


class MemoryType(Enum):
    """Types of memory storage."""

    SHORT_TERM = "short"  # Current conversation (Redis, 30min)
    MEDIUM_TERM = "medium"  # Recent summary (Redis, 24h)
    LONG_TERM = "long"  # Persistent preferences (PostgreSQL)


@dataclass
class MemoryEntry:
    """A single memory entry."""

    key: str
    content: str
    memory_type: MemoryType
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)
    relevance_score: float = 1.0


@dataclass
class ConversationMemory:
    """Complete memory context for a conversation."""

    restaurant_id: UUID
    customer_phone: str
    customer_name: Optional[str] = None

    short_term: list[MemoryEntry] = field(default_factory=list)
    medium_term: list[MemoryEntry] = field(default_factory=list)
    long_term: list[MemoryEntry] = field(default_factory=list)

    @property
    def has_history(self) -> bool:
        """Check if customer has any history."""
        return bool(self.medium_term or self.long_term)

    @property
    def display_name(self) -> str:
        """Get customer display name."""
        return self.customer_name or "Cliente"

    def get_context_summary(self) -> str:
        """
        Build legacy single-block context summary.

        Kept for backward compatibility. Prefer the three dedicated
        methods below for new prompt integrations.
        """
        parts = [
            self.get_long_term_summary(),
            self.get_medium_term_summary(),
            self.get_short_term_summary(),
        ]
        return "\n\n".join(p for p in parts if p)

    def get_long_term_summary(self) -> str:
        """
        Return long-term memory block for prompt injection.

        Contains persistent customer preferences, known allergies,
        favorite items, and behavioral patterns.
        """
        if not self.long_term:
            return ""
        lines = []
        for entry in self.long_term[:8]:
            lines.append(f"- {entry.content}")
        return "\n".join(lines)

    def get_medium_term_summary(self) -> str:
        """
        Return medium-term memory block for prompt injection.

        Contains recent session summaries and last known orders
        from the past 24 hours.
        """
        if not self.medium_term:
            return ""
        lines = []
        for entry in self.medium_term[:4]:
            lines.append(f"- {entry.content}")
        return "\n".join(lines)

    def get_short_term_summary(self) -> str:
        """
        Return short-term memory block for prompt injection.

        Contains the current active conversation messages
        (last ~30 minutes).
        """
        if not self.short_term:
            return ""
        lines = []
        for entry in self.short_term[-6:]:
            role = entry.metadata.get("role", "user")
            prefix = "Cliente" if role == "user" else "Maria"
            lines.append(f"{prefix}: {entry.content}")
        return "\n".join(lines)


class MemoryPort(ABC):
    """
    Port for memory storage operations.

    Implemented by Redis (short/medium) and PostgreSQL (long-term).
    """

    @abstractmethod
    async def store(
        self,
        restaurant_id: UUID,
        customer_phone: str,
        entry: MemoryEntry,
    ) -> Success[bool] | Failure[Exception]:
        """Store a memory entry."""
        ...

    @abstractmethod
    async def retrieve(
        self,
        restaurant_id: UUID,
        customer_phone: str,
        memory_type: MemoryType,
        limit: int = 10,
    ) -> Success[list[MemoryEntry]] | Failure[Exception]:
        """Retrieve memory entries."""
        ...

    @abstractmethod
    async def search(
        self,
        restaurant_id: UUID,
        customer_phone: str,
        query: str,
        limit: int = 5,
    ) -> Success[list[MemoryEntry]] | Failure[Exception]:
        """Search memories by semantic similarity."""
        ...

    @abstractmethod
    async def clear(
        self,
        restaurant_id: UUID,
        customer_phone: str,
        memory_type: Optional[MemoryType] = None,
    ) -> Success[bool] | Failure[Exception]:
        """Clear memories (optionally by type)."""
        ...


class MemoryManager:
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
        Initialize memory manager.

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

        short_result = await self._short_term.retrieve(
            restaurant_id, customer_phone, MemoryType.SHORT_TERM, limit=20
        )
        if isinstance(short_result, Success):
            memory.short_term = short_result.value

        medium_result = await self._short_term.retrieve(
            restaurant_id, customer_phone, MemoryType.MEDIUM_TERM, limit=5
        )
        if isinstance(medium_result, Success):
            memory.medium_term = medium_result.value

        long_result = await self._long_term.retrieve(
            restaurant_id, customer_phone, MemoryType.LONG_TERM, limit=10
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
