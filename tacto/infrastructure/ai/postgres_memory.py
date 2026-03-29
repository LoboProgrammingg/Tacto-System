"""
PostgreSQL Memory Adapter.

Implements long-term memory storage using PostgreSQL with pgvector.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

import structlog
from sqlalchemy import Column, DateTime, Float, String, Text, select
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession

from tacto.domain.customer_memory.value_objects.memory_entry import MemoryEntry, MemoryType
from tacto.domain.customer_memory.ports.memory_port import MemoryPort
from tacto.shared.application import Err, Failure, Ok, Success
from tacto.infrastructure.database.models import Base


logger = structlog.get_logger()


class CustomerMemoryModel(Base):
    """SQLAlchemy model for long-term customer memories."""

    __tablename__ = "customer_memories"

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default="uuid_generate_v4()")
    restaurant_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    customer_phone = Column(String(20), nullable=False, index=True)
    memory_key = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    extra_data = Column(JSONB, nullable=True)
    relevance_score = Column(Float, default=1.0)
    created_at = Column(DateTime(timezone=True), server_default="NOW()")
    updated_at = Column(DateTime(timezone=True), server_default="NOW()", onupdate="NOW()")


class PostgresMemoryAdapter(MemoryPort):
    """
    PostgreSQL implementation for long-term memory.

    Stores customer preferences, order history summaries, and
    other persistent information.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        self._session = session

    async def store(
        self,
        restaurant_id: UUID,
        customer_phone: str,
        entry: MemoryEntry,
    ) -> Success[bool] | Failure[Exception]:
        """Store memory entry in PostgreSQL."""
        try:
            model = CustomerMemoryModel(
                restaurant_id=restaurant_id,
                customer_phone=customer_phone,
                memory_key=entry.key,
                content=entry.content,
                extra_data=entry.metadata,
                relevance_score=entry.relevance_score,
            )

            self._session.add(model)
            await self._session.commit()

            logger.debug(
                "Long-term memory stored",
                restaurant_id=str(restaurant_id),
                phone=customer_phone,
                key=entry.key,
            )

            return Ok(True)

        except Exception as e:
            await self._session.rollback()
            logger.error("PostgreSQL memory store error", error=str(e))
            return Err(e)

    async def retrieve(
        self,
        restaurant_id: UUID,
        customer_phone: str,
        memory_type: MemoryType,
        limit: int = 10,
    ) -> Success[list[MemoryEntry]] | Failure[Exception]:
        """Retrieve memory entries from PostgreSQL."""
        try:
            stmt = (
                select(CustomerMemoryModel)
                .where(CustomerMemoryModel.restaurant_id == restaurant_id)
                .where(CustomerMemoryModel.customer_phone == customer_phone)
                .order_by(CustomerMemoryModel.created_at.desc())
                .limit(limit)
            )

            result = await self._session.execute(stmt)
            models = result.scalars().all()

            entries = [
                MemoryEntry(
                    key=m.memory_key,
                    content=m.content,
                    memory_type=MemoryType.LONG_TERM,
                    timestamp=m.created_at,
                    metadata=m.extra_data or {},
                    relevance_score=m.relevance_score or 1.0,
                )
                for m in models
            ]

            return Ok(entries)

        except Exception as e:
            logger.error("PostgreSQL memory retrieve error", error=str(e))
            return Err(e)

    async def search(
        self,
        restaurant_id: UUID,
        customer_phone: str,
        query: str,
        limit: int = 5,
    ) -> Success[list[MemoryEntry]] | Failure[Exception]:
        """
        Search memories using text matching.

        TODO: Implement semantic search with pgvector embeddings.
        """
        try:
            stmt = (
                select(CustomerMemoryModel)
                .where(CustomerMemoryModel.restaurant_id == restaurant_id)
                .where(CustomerMemoryModel.customer_phone == customer_phone)
                .where(CustomerMemoryModel.content.ilike(f"%{query}%"))
                .order_by(CustomerMemoryModel.relevance_score.desc())
                .limit(limit)
            )

            result = await self._session.execute(stmt)
            models = result.scalars().all()

            entries = [
                MemoryEntry(
                    key=m.memory_key,
                    content=m.content,
                    memory_type=MemoryType.LONG_TERM,
                    timestamp=m.created_at,
                    metadata=m.extra_data or {},
                    relevance_score=m.relevance_score or 1.0,
                )
                for m in models
            ]

            return Ok(entries)

        except Exception as e:
            logger.error("PostgreSQL memory search error", error=str(e))
            return Err(e)

    async def clear(
        self,
        restaurant_id: UUID,
        customer_phone: str,
        memory_type: Optional[MemoryType] = None,
    ) -> Success[bool] | Failure[Exception]:
        """Clear long-term memories for a customer."""
        try:
            from sqlalchemy import delete

            stmt = (
                delete(CustomerMemoryModel)
                .where(CustomerMemoryModel.restaurant_id == restaurant_id)
                .where(CustomerMemoryModel.customer_phone == customer_phone)
            )

            await self._session.execute(stmt)
            await self._session.commit()

            return Ok(True)

        except Exception as e:
            await self._session.rollback()
            logger.error("PostgreSQL memory clear error", error=str(e))
            return Err(e)
