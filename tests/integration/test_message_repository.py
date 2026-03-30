"""
Integration Tests for MessageRepository.

Tests repository operations against real PostgreSQL database.
"""

from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from tacto.infrastructure.database.models.conversation import ConversationModel
from tacto.infrastructure.database.models.message import MessageModel
from tacto.infrastructure.persistence.message_repository import PostgresMessageRepository
from tacto.domain.messaging.entities.message import Message
from tacto.domain.messaging.value_objects.message_source import MessageSource
from tacto.shared.domain.value_objects import ConversationId, MessageId


class TestMessageRepositoryIntegration:
    """Integration tests for MessageRepository."""

    @pytest.mark.asyncio
    async def test_find_by_conversation(
        self,
        db_session: AsyncSession,
        sample_conversation: ConversationModel,
        sample_messages: list[MessageModel],
    ):
        """Should find messages by conversation ID."""
        repo = PostgresMessageRepository(db_session)

        results = await repo.find_by_conversation(
            conversation_id=ConversationId(sample_conversation.id),
            limit=10,
        )

        assert len(results) == 3
        # Should be ordered by created_at desc
        assert results[0].content == sample_messages[-1].content

    @pytest.mark.asyncio
    async def test_find_recent_messages(
        self,
        db_session: AsyncSession,
        sample_conversation: ConversationModel,
        sample_messages: list[MessageModel],
    ):
        """Should find recent messages with limit."""
        repo = PostgresMessageRepository(db_session)

        results = await repo.find_recent(
            conversation_id=ConversationId(sample_conversation.id),
            limit=2,
        )

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_save_new_message(
        self,
        db_session: AsyncSession,
        sample_conversation: ConversationModel,
    ):
        """Should save new message to database."""
        repo = PostgresMessageRepository(db_session)

        message = Message.create(
            conversation_id=ConversationId(sample_conversation.id),
            role="user",
            content="Nova mensagem de teste",
            external_id="MSG_NEW_001",
            source=MessageSource.APP,
        )

        saved = await repo.save(message)

        assert saved.id == message.id
        # Verify it's in database
        results = await repo.find_by_conversation(
            ConversationId(sample_conversation.id),
            limit=10,
        )
        assert any(m.external_id == "MSG_NEW_001" for m in results)

    @pytest.mark.asyncio
    async def test_find_by_external_id(
        self,
        db_session: AsyncSession,
        sample_conversation: ConversationModel,
        sample_messages: list[MessageModel],
    ):
        """Should find message by external ID."""
        repo = PostgresMessageRepository(db_session)

        result = await repo.find_by_external_id(
            conversation_id=ConversationId(sample_conversation.id),
            external_id="MSG_001",
        )

        assert result is not None
        assert result.content == "Olá, vocês estão abertos?"

    @pytest.mark.asyncio
    async def test_find_by_external_id_not_found(
        self,
        db_session: AsyncSession,
        sample_conversation: ConversationModel,
    ):
        """Should return None when message not found."""
        repo = PostgresMessageRepository(db_session)

        result = await repo.find_by_external_id(
            conversation_id=ConversationId(sample_conversation.id),
            external_id="NON_EXISTENT",
        )

        assert result is None


class TestMessageRepositoryConversationHistory:
    """Test conversation history functionality."""

    @pytest.mark.asyncio
    async def test_get_conversation_history_format(
        self,
        db_session: AsyncSession,
        sample_conversation: ConversationModel,
        sample_messages: list[MessageModel],
    ):
        """Messages should be properly formatted for AI context."""
        repo = PostgresMessageRepository(db_session)

        messages = await repo.find_by_conversation(
            ConversationId(sample_conversation.id),
            limit=10,
        )

        # Build history format
        history = [{"role": m.role, "content": m.content} for m in reversed(messages)]

        assert len(history) == 3
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"
        assert history[2]["role"] == "user"

    @pytest.mark.asyncio
    async def test_message_ordering(
        self,
        db_session: AsyncSession,
        sample_conversation: ConversationModel,
    ):
        """Messages should be ordered by creation time."""
        repo = PostgresMessageRepository(db_session)

        # Add messages with known order
        for i in range(5):
            msg = Message.create(
                conversation_id=ConversationId(sample_conversation.id),
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
                external_id=f"MSG_ORDER_{i}",
                source=MessageSource.APP,
            )
            await repo.save(msg)

        results = await repo.find_by_conversation(
            ConversationId(sample_conversation.id),
            limit=10,
        )

        # Should have original 3 + 5 new = 8 messages
        # Most recent first
        assert "Message 4" in results[0].content
