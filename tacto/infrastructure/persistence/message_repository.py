"""
PostgreSQL Message Repository Implementation.

Implements the MessageRepository interface from the domain layer.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tacto.domain.messaging.entities.message import Message
from tacto.domain.messaging.repository import MessageRepository
from tacto.domain.messaging.value_objects.message_direction import MessageDirection
from tacto.domain.messaging.value_objects.message_source import MessageSource
from tacto.shared.application import Err, Failure, Ok, Success
from tacto.shared.domain.value_objects import ConversationId, MessageId
from tacto.infrastructure.database.models.message import MessageModel


class PostgresMessageRepository(MessageRepository):
    """
    PostgreSQL implementation of MessageRepository.

    Handles persistence of Message entities using SQLAlchemy.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self._session = session

    async def save(
        self, message: Message
    ) -> Success[Message] | Failure[Exception]:
        """Persist a message."""
        try:
            model = self._to_model(message)
            self._session.add(model)
            await self._session.flush()
            return Ok(message)

        except Exception as e:
            return Err(e)

    async def save_batch(
        self, messages: list[Message]
    ) -> Success[list[Message]] | Failure[Exception]:
        """Persist multiple messages in a batch."""
        try:
            models = [self._to_model(m) for m in messages]
            self._session.add_all(models)
            await self._session.flush()
            return Ok(messages)

        except Exception as e:
            return Err(e)

    async def find_by_id(
        self, message_id: MessageId
    ) -> Success[Optional[Message]] | Failure[Exception]:
        """Find message by ID."""
        try:
            model = await self._session.get(MessageModel, message_id.value)

            if model is None:
                return Ok(None)

            return Ok(self._to_entity(model))

        except Exception as e:
            return Err(e)

    async def find_by_conversation(
        self,
        conversation_id: ConversationId,
        limit: int = 50,
        before: Optional[datetime] = None,
    ) -> Success[list[Message]] | Failure[Exception]:
        """
        Find messages for a conversation.

        Returns messages ordered by timestamp descending (newest first).
        """
        try:
            stmt = select(MessageModel).where(
                MessageModel.conversation_id == conversation_id.value
            )

            if before:
                stmt = stmt.where(MessageModel.timestamp < before)

            stmt = stmt.order_by(MessageModel.timestamp.desc()).limit(limit)

            result = await self._session.execute(stmt)
            models = result.scalars().all()

            return Ok([self._to_entity(m) for m in models])

        except Exception as e:
            return Err(e)

    async def find_recent_by_conversation(
        self,
        conversation_id: ConversationId,
        limit: int = 10,
    ) -> Success[list[Message]] | Failure[Exception]:
        """
        Find most recent messages for context building.

        Returns messages ordered by timestamp ascending (oldest first)
        for proper context building.
        """
        try:
            subquery = (
                select(MessageModel.id)
                .where(MessageModel.conversation_id == conversation_id.value)
                .order_by(MessageModel.timestamp.desc())
                .limit(limit)
            )

            stmt = (
                select(MessageModel)
                .where(MessageModel.id.in_(subquery))
                .order_by(MessageModel.timestamp.asc())
            )

            result = await self._session.execute(stmt)
            models = result.scalars().all()

            return Ok([self._to_entity(m) for m in models])

        except Exception as e:
            return Err(e)

    async def count_by_conversation(
        self, conversation_id: ConversationId
    ) -> Success[int] | Failure[Exception]:
        """Count total messages in a conversation."""
        try:
            stmt = select(func.count(MessageModel.id)).where(
                MessageModel.conversation_id == conversation_id.value
            )
            result = await self._session.execute(stmt)
            count = result.scalar_one()

            return Ok(count)

        except Exception as e:
            return Err(e)

    def _to_model(self, entity: Message) -> MessageModel:
        """Convert domain entity to SQLAlchemy model."""
        return MessageModel(
            id=entity.id.value,
            conversation_id=entity.conversation_id.value,
            body=entity.body,
            direction=entity.direction.value,
            source=entity.source.value,
            from_me=entity.from_me,
            timestamp=entity.timestamp,
            external_id=entity.external_id,
            media_url=entity.media_url,
            media_type=entity.media_type,
            metadata_=entity.metadata,
            created_at=entity.created_at,
        )

    def _to_entity(self, model: MessageModel) -> Message:
        """Convert SQLAlchemy model to domain entity."""
        return Message(
            id=MessageId(model.id),
            conversation_id=ConversationId(model.conversation_id),
            body=model.body,
            direction=MessageDirection(model.direction),
            source=MessageSource(model.source),
            from_me=model.from_me,
            timestamp=model.timestamp,
            external_id=model.external_id,
            media_url=model.media_url,
            media_type=model.media_type,
            metadata=model.metadata_,
            created_at=model.created_at,
        )
