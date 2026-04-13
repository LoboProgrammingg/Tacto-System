"""
PostgreSQL Conversation Repository Implementation.

Implements the ConversationRepository interface from the domain layer.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tacto.domain.messaging.entities.conversation import Conversation
from tacto.domain.messaging.repository import ConversationRepository
from tacto.shared.application import Err, Failure, Ok, Success
from tacto.shared.domain.value_objects import ConversationId, PhoneNumber, RestaurantId
from tacto.infrastructure.database.models.conversation import ConversationModel


class PostgresConversationRepository(ConversationRepository):
    """
    PostgreSQL implementation of ConversationRepository.

    Handles persistence of Conversation aggregates using SQLAlchemy.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self._session = session

    async def save(
        self, conversation: Conversation
    ) -> Success[Conversation] | Failure[Exception]:
        """Persist a conversation."""
        try:
            model = self._to_model(conversation)

            existing = await self._session.get(ConversationModel, conversation.id.value)

            if existing:
                for key, value in model.__dict__.items():
                    if not key.startswith("_"):
                        setattr(existing, key, value)
            else:
                self._session.add(model)

            await self._session.flush()
            return Ok(conversation)

        except Exception as e:
            await self._session.rollback()
            return Err(e)

    async def find_by_id(
        self, conversation_id: ConversationId
    ) -> Success[Optional[Conversation]] | Failure[Exception]:
        """Find conversation by ID."""
        try:
            model = await self._session.get(ConversationModel, conversation_id.value)

            if model is None:
                return Ok(None)

            return Ok(self._to_entity(model))

        except Exception as e:
            return Err(e)

    async def find_by_restaurant_and_phone(
        self,
        restaurant_id: RestaurantId,
        customer_phone: PhoneNumber,
    ) -> Success[Optional[Conversation]] | Failure[Exception]:
        """
        Find conversation by restaurant and customer phone.

        This is the primary lookup method for incoming messages.
        """
        try:
            stmt = select(ConversationModel).where(
                ConversationModel.restaurant_id == restaurant_id.value,
                ConversationModel.customer_phone == customer_phone.value,
            )
            result = await self._session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                return Ok(None)

            return Ok(self._to_entity(model))

        except Exception as e:
            return Err(e)

    async def find_active_by_restaurant(
        self,
        restaurant_id: RestaurantId,
        limit: int = 50,
        offset: int = 0,
    ) -> Success[list[Conversation]] | Failure[Exception]:
        """Find active conversations for a restaurant."""
        try:
            stmt = (
                select(ConversationModel)
                .where(ConversationModel.restaurant_id == restaurant_id.value)
                .order_by(ConversationModel.last_message_at.desc())
                .limit(limit)
                .offset(offset)
            )
            result = await self._session.execute(stmt)
            models = result.scalars().all()

            return Ok([self._to_entity(m) for m in models])

        except Exception as e:
            return Err(e)

    async def find_with_disabled_ai(
        self,
        restaurant_id: RestaurantId,
    ) -> Success[list[Conversation]] | Failure[Exception]:
        """Find conversations where AI is currently disabled."""
        try:
            now = datetime.utcnow()
            stmt = (
                select(ConversationModel)
                .where(
                    ConversationModel.restaurant_id == restaurant_id.value,
                    ConversationModel.is_ai_active == False,
                    ConversationModel.ai_disabled_until > now,
                )
                .order_by(ConversationModel.ai_disabled_until)
            )
            result = await self._session.execute(stmt)
            models = result.scalars().all()

            return Ok([self._to_entity(m) for m in models])

        except Exception as e:
            return Err(e)

    def _to_model(self, entity: Conversation) -> ConversationModel:
        """Convert domain entity to SQLAlchemy model."""
        return ConversationModel(
            id=entity.id.value,
            restaurant_id=entity.restaurant_id.value,
            customer_phone=entity.customer_phone.value,
            customer_name=entity.customer_name,
            is_ai_active=entity.is_ai_active,
            ai_disabled_until=entity.ai_disabled_until,
            ai_disabled_reason=entity.ai_disabled_reason,
            last_message_at=entity.last_message_at,
            metadata_=entity.metadata,
        )

    def _to_entity(self, model: ConversationModel) -> Conversation:
        """Convert SQLAlchemy model to domain entity."""
        return Conversation(
            id=ConversationId(model.id),
            restaurant_id=RestaurantId(model.restaurant_id),
            customer_phone=PhoneNumber(model.customer_phone),
            customer_name=model.customer_name,
            is_ai_active=model.is_ai_active,
            ai_disabled_until=model.ai_disabled_until,
            ai_disabled_reason=model.ai_disabled_reason,
            last_message_at=model.last_message_at,
            metadata=model.metadata_,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
