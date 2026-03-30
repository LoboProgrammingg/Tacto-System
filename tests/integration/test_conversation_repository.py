"""
Integration Tests for ConversationRepository.

Tests repository operations against real PostgreSQL database.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from tacto.infrastructure.database.models.restaurant import RestaurantModel
from tacto.infrastructure.database.models.conversation import ConversationModel
from tacto.infrastructure.persistence.conversation_repository import PostgresConversationRepository
from tacto.domain.messaging.entities.conversation import Conversation
from tacto.shared.domain.value_objects import RestaurantId, ConversationId, PhoneNumber


class TestConversationRepositoryIntegration:
    """Integration tests for ConversationRepository."""

    @pytest.mark.asyncio
    async def test_find_by_phone(
        self,
        db_session: AsyncSession,
        sample_conversation: ConversationModel,
        sample_restaurant: RestaurantModel,
    ):
        """Should find conversation by phone number."""
        repo = PostgresConversationRepository(db_session)

        result = await repo.find_by_phone(
            restaurant_id=RestaurantId(sample_restaurant.id),
            phone=PhoneNumber(sample_conversation.customer_phone),
        )

        assert result is not None
        assert result.customer_phone.value == sample_conversation.customer_phone

    @pytest.mark.asyncio
    async def test_find_by_phone_not_found(
        self,
        db_session: AsyncSession,
        sample_restaurant: RestaurantModel,
    ):
        """Should return None when conversation not found."""
        repo = PostgresConversationRepository(db_session)

        result = await repo.find_by_phone(
            restaurant_id=RestaurantId(sample_restaurant.id),
            phone=PhoneNumber("5511999999999"),
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_find_by_id(
        self,
        db_session: AsyncSession,
        sample_conversation: ConversationModel,
    ):
        """Should find conversation by ID."""
        repo = PostgresConversationRepository(db_session)

        result = await repo.find_by_id(ConversationId(sample_conversation.id))

        assert result is not None
        assert result.id.value == sample_conversation.id

    @pytest.mark.asyncio
    async def test_save_new_conversation(
        self,
        db_session: AsyncSession,
        sample_restaurant: RestaurantModel,
    ):
        """Should save new conversation to database."""
        repo = PostgresConversationRepository(db_session)

        conversation = Conversation.create(
            restaurant_id=RestaurantId(sample_restaurant.id),
            customer_phone=PhoneNumber("5511988887777"),
            customer_name="Novo Cliente",
        )

        saved = await repo.save(conversation)

        assert saved.id == conversation.id
        # Verify it's in database
        found = await repo.find_by_id(conversation.id)
        assert found is not None
        assert found.customer_name == "Novo Cliente"

    @pytest.mark.asyncio
    async def test_disable_ai(
        self,
        db_session: AsyncSession,
        sample_conversation: ConversationModel,
    ):
        """Should disable AI for conversation."""
        repo = PostgresConversationRepository(db_session)

        conversation = await repo.find_by_id(ConversationId(sample_conversation.id))
        assert conversation is not None
        assert conversation.ai_enabled is True

        conversation.disable_ai(duration_hours=12)

        saved = await repo.save(conversation)

        assert saved.ai_enabled is False
        assert saved.ai_disabled_until is not None

    @pytest.mark.asyncio
    async def test_find_active_conversations(
        self,
        db_session: AsyncSession,
        sample_restaurant: RestaurantModel,
        sample_conversation: ConversationModel,
    ):
        """Should find active conversations for restaurant."""
        repo = PostgresConversationRepository(db_session)

        results = await repo.find_active_by_restaurant(
            restaurant_id=RestaurantId(sample_restaurant.id),
            limit=10,
        )

        assert len(results) >= 1
        assert any(c.id.value == sample_conversation.id for c in results)


class TestConversationRepositoryAIControl:
    """Test AI enable/disable functionality."""

    @pytest.mark.asyncio
    async def test_ai_disabled_conversation_remains_disabled(
        self,
        db_session: AsyncSession,
        sample_restaurant: RestaurantModel,
    ):
        """AI should remain disabled until time expires."""
        # Create conversation with AI disabled
        conv = ConversationModel(
            id=uuid4(),
            restaurant_id=sample_restaurant.id,
            customer_phone="5511977776666",
            customer_name="Cliente AI Desativado",
            is_ai_active=False,
            ai_disabled_until=datetime(2099, 12, 31, tzinfo=timezone.utc),
            status="active",
        )
        db_session.add(conv)
        await db_session.flush()

        repo = PostgresConversationRepository(db_session)
        found = await repo.find_by_id(ConversationId(conv.id))

        assert found is not None
        assert found.ai_enabled is False
        assert found.should_process_with_ai() is False

    @pytest.mark.asyncio
    async def test_enable_ai_after_disable(
        self,
        db_session: AsyncSession,
        sample_conversation: ConversationModel,
    ):
        """Should be able to re-enable AI."""
        repo = PostgresConversationRepository(db_session)

        conversation = await repo.find_by_id(ConversationId(sample_conversation.id))
        conversation.disable_ai(duration_hours=12)
        await repo.save(conversation)

        # Re-enable
        conversation.enable_ai()
        saved = await repo.save(conversation)

        assert saved.ai_enabled is True
        assert saved.ai_disabled_until is None
