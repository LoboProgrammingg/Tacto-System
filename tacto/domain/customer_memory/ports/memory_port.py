"""
Memory Port — Domain Interface.

Pure interface for memory storage operations.
Implementations live in infrastructure/ (Redis, PostgreSQL).
"""

from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from tacto.shared.application import Failure, Success
from tacto.domain.customer_memory.value_objects.memory_entry import MemoryEntry, MemoryType


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
