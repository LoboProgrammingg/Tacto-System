"""
Tests for ProcessIncomingMessageUseCase.

Tests the core message processing pipeline:
1. Restaurant lookup by instance_key
2. Conversation creation/retrieval
3. Human intervention detection
4. AI response generation
5. Message sending via WhatsApp
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from tacto.application.dto.message_dto import IncomingMessageDTO, MessageResponseDTO
from tacto.application.use_cases.process_incoming_message import ProcessIncomingMessageUseCase
from tacto.domain.messaging.entities.conversation import Conversation
from tacto.domain.messaging.entities.message import Message
from tacto.domain.restaurant.entities.restaurant import Restaurant
from tacto.domain.restaurant.value_objects.automation_type import AutomationType
from tacto.domain.restaurant.value_objects.integration_type import IntegrationType
from tacto.domain.restaurant.value_objects.opening_hours import OpeningHours
from tacto.shared.application import Failure, Success
from tacto.shared.domain.value_objects import PhoneNumber, RestaurantId


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_restaurant() -> Restaurant:
    """Create a mock restaurant entity."""
    return Restaurant(
        id=RestaurantId(uuid4()),
        name="Restaurante Teste",
        prompt_default="Você é Maria, atendente virtual do Restaurante Teste.",
        menu_url="https://cardapio.test.com",
        opening_hours=OpeningHours.from_dict({
            "monday": {"opens_at": "11:00", "closes_at": "23:00"},
            "tuesday": {"opens_at": "11:00", "closes_at": "23:00"},
            "wednesday": {"opens_at": "11:00", "closes_at": "23:00"},
            "thursday": {"opens_at": "11:00", "closes_at": "23:00"},
            "friday": {"opens_at": "11:00", "closes_at": "23:00"},
            "saturday": {"opens_at": "11:00", "closes_at": "23:00"},
            "sunday": {"opens_at": "11:00", "closes_at": "23:00"},
        }),
        integration_type=IntegrationType.JOIN,
        automation_type=AutomationType.BASIC,
        chave_grupo_empresarial=uuid4(),
        canal_master_id="restaurante_teste",
        empresa_base_id="1",
        timezone="America/Sao_Paulo",
    )


@pytest.fixture
def mock_conversation(mock_restaurant: Restaurant) -> Conversation:
    """Create a mock conversation entity."""
    return Conversation.create(
        restaurant_id=mock_restaurant.id,
        customer_phone=PhoneNumber("5565992540370"),
        customer_name="Cliente Teste",
    )


@pytest.fixture
def incoming_message_dto() -> IncomingMessageDTO:
    """Create a sample incoming message DTO."""
    return IncomingMessageDTO(
        instance_key="restaurante_teste",
        from_phone="5565992540370",
        body="Oi, quero fazer um pedido",
        from_me=False,
        source="app",
        timestamp=int(datetime.now(timezone.utc).timestamp()),
        message_id="MSG_123",
        push_name="Cliente Teste",
    )


@pytest.fixture
def human_intervention_dto() -> IncomingMessageDTO:
    """Create a DTO that simulates human intervention."""
    return IncomingMessageDTO(
        instance_key="restaurante_teste",
        from_phone="5565992540370",
        body="Mensagem do operador",
        from_me=True,
        source="phone",  # MessageSource.PHONE triggers human intervention
        timestamp=int(datetime.now(timezone.utc).timestamp()),
        message_id="MSG_HUMAN",
        push_name="",
    )


@pytest.fixture
def mock_restaurant_repository(mock_restaurant: Restaurant) -> MagicMock:
    """Create mock restaurant repository."""
    repo = MagicMock()
    repo.find_by_canal_master_id = AsyncMock(return_value=Success(mock_restaurant))
    return repo


@pytest.fixture
def mock_conversation_repository(mock_conversation: Conversation) -> MagicMock:
    """Create mock conversation repository."""
    repo = MagicMock()
    repo.find_by_restaurant_and_phone = AsyncMock(return_value=Success(mock_conversation))
    repo.save = AsyncMock(return_value=Success(None))
    return repo


@pytest.fixture
def mock_message_repository() -> MagicMock:
    """Create mock message repository."""
    repo = MagicMock()
    repo.save = AsyncMock(return_value=Success(None))
    repo.find_recent_by_conversation = AsyncMock(return_value=Success([]))
    return repo


@pytest.fixture
def mock_messaging_client() -> MagicMock:
    """Create mock messaging client."""
    client = MagicMock()
    client.send_message = AsyncMock(return_value=Success("MSG_SENT_123"))
    return client


@pytest.fixture
def mock_ai_agent() -> MagicMock:
    """Create mock AI agent."""
    agent = MagicMock()
    agent_response = MagicMock()
    agent_response.message = "Olá! Bem-vindo ao restaurante. Como posso ajudar?"
    agent_response.should_send = True
    agent_response.triggered_actions = []
    agent.process = AsyncMock(return_value=Success(agent_response))
    return agent


# ──────────────────────────────────────────────────────────────────────────────
# Test Classes
# ──────────────────────────────────────────────────────────────────────────────

class TestProcessIncomingMessageUseCase:
    """Test ProcessIncomingMessageUseCase execution."""

    @pytest.mark.asyncio
    async def test_successful_message_processing(
        self,
        mock_restaurant_repository,
        mock_conversation_repository,
        mock_message_repository,
        mock_messaging_client,
        mock_ai_agent,
        incoming_message_dto,
    ):
        """Test successful end-to-end message processing."""
        use_case = ProcessIncomingMessageUseCase(
            restaurant_repository=mock_restaurant_repository,
            conversation_repository=mock_conversation_repository,
            message_repository=mock_message_repository,
            messaging_client=mock_messaging_client,
            ai_agent=mock_ai_agent,
        )

        with patch("tacto.application.use_cases.process_incoming_message.get_settings") as mock_settings:
            mock_settings.return_value.app.conversation_history_limit = 10
            mock_settings.return_value.app.bypass_hours_check = True
            mock_settings.return_value.app.ai_disable_hours = 12
            mock_settings.return_value.gemini.level1_rag_search_limit = 5

            result = await use_case.execute(incoming_message_dto)

        assert isinstance(result, Success)
        assert result.value.success is True
        assert result.value.response_sent is True
        assert "Olá" in result.value.response_text

        # Verify interactions
        mock_restaurant_repository.find_by_canal_master_id.assert_called_once()
        mock_conversation_repository.find_by_restaurant_and_phone.assert_called_once()
        mock_ai_agent.process.assert_called_once()
        mock_messaging_client.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_restaurant_not_found(
        self,
        mock_restaurant_repository,
        mock_conversation_repository,
        mock_message_repository,
        mock_messaging_client,
        mock_ai_agent,
        incoming_message_dto,
    ):
        """Test handling when restaurant is not found."""
        mock_restaurant_repository.find_by_canal_master_id = AsyncMock(
            return_value=Success(None)
        )

        use_case = ProcessIncomingMessageUseCase(
            restaurant_repository=mock_restaurant_repository,
            conversation_repository=mock_conversation_repository,
            message_repository=mock_message_repository,
            messaging_client=mock_messaging_client,
            ai_agent=mock_ai_agent,
        )

        result = await use_case.execute(incoming_message_dto)

        assert isinstance(result, Success)
        assert result.value.success is False
        assert "not found" in result.value.error.lower()

    @pytest.mark.asyncio
    async def test_human_intervention_disables_ai(
        self,
        mock_restaurant_repository,
        mock_conversation_repository,
        mock_message_repository,
        mock_messaging_client,
        mock_ai_agent,
        human_intervention_dto,
    ):
        """Test that human intervention disables AI for the conversation."""
        use_case = ProcessIncomingMessageUseCase(
            restaurant_repository=mock_restaurant_repository,
            conversation_repository=mock_conversation_repository,
            message_repository=mock_message_repository,
            messaging_client=mock_messaging_client,
            ai_agent=mock_ai_agent,
        )

        result = await use_case.execute(human_intervention_dto)

        assert isinstance(result, Success)
        assert result.value.ai_disabled is True
        assert "human" in result.value.ai_disabled_reason.lower()

        # AI agent should NOT be called
        mock_ai_agent.process.assert_not_called()
        # No message should be sent
        mock_messaging_client.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_ai_disabled_conversation(
        self,
        mock_restaurant_repository,
        mock_conversation_repository,
        mock_message_repository,
        mock_messaging_client,
        mock_ai_agent,
        mock_conversation,
        incoming_message_dto,
    ):
        """Test that messages are not processed when AI is disabled."""
        # Disable AI on the conversation
        mock_conversation.disable_ai(reason="test_disabled", duration_hours=12)
        mock_conversation_repository.find_by_restaurant_and_phone = AsyncMock(
            return_value=Success(mock_conversation)
        )

        use_case = ProcessIncomingMessageUseCase(
            restaurant_repository=mock_restaurant_repository,
            conversation_repository=mock_conversation_repository,
            message_repository=mock_message_repository,
            messaging_client=mock_messaging_client,
            ai_agent=mock_ai_agent,
        )

        result = await use_case.execute(incoming_message_dto)

        assert isinstance(result, Success)
        assert result.value.ai_disabled is True

        # AI agent should NOT be called
        mock_ai_agent.process.assert_not_called()

    @pytest.mark.asyncio
    async def test_new_conversation_created(
        self,
        mock_restaurant_repository,
        mock_conversation_repository,
        mock_message_repository,
        mock_messaging_client,
        mock_ai_agent,
        incoming_message_dto,
    ):
        """Test that a new conversation is created when none exists."""
        # Return None to simulate no existing conversation
        mock_conversation_repository.find_by_restaurant_and_phone = AsyncMock(
            return_value=Success(None)
        )

        use_case = ProcessIncomingMessageUseCase(
            restaurant_repository=mock_restaurant_repository,
            conversation_repository=mock_conversation_repository,
            message_repository=mock_message_repository,
            messaging_client=mock_messaging_client,
            ai_agent=mock_ai_agent,
        )

        with patch("tacto.application.use_cases.process_incoming_message.get_settings") as mock_settings:
            mock_settings.return_value.app.conversation_history_limit = 10
            mock_settings.return_value.app.bypass_hours_check = True
            mock_settings.return_value.app.ai_disable_hours = 12
            mock_settings.return_value.gemini.level1_rag_search_limit = 5

            result = await use_case.execute(incoming_message_dto)

        assert isinstance(result, Success)
        # Conversation should be saved (created)
        assert mock_conversation_repository.save.call_count >= 1


class TestProcessIncomingMessageTriggeredActions:
    """Test triggered actions from AI agent."""

    @pytest.mark.asyncio
    async def test_human_handoff_action(
        self,
        mock_restaurant_repository,
        mock_conversation_repository,
        mock_message_repository,
        mock_messaging_client,
        mock_ai_agent,
        incoming_message_dto,
    ):
        """Test that human_handoff action disables AI."""
        # Configure agent to trigger human_handoff
        agent_response = MagicMock()
        agent_response.message = "Vou transferir para um atendente humano."
        agent_response.should_send = True
        agent_response.triggered_actions = ["human_handoff"]
        mock_ai_agent.process = AsyncMock(return_value=Success(agent_response))

        use_case = ProcessIncomingMessageUseCase(
            restaurant_repository=mock_restaurant_repository,
            conversation_repository=mock_conversation_repository,
            message_repository=mock_message_repository,
            messaging_client=mock_messaging_client,
            ai_agent=mock_ai_agent,
        )

        with patch("tacto.application.use_cases.process_incoming_message.get_settings") as mock_settings:
            mock_settings.return_value.app.conversation_history_limit = 10
            mock_settings.return_value.app.bypass_hours_check = True
            mock_settings.return_value.app.ai_disable_hours = 12
            mock_settings.return_value.gemini.level1_rag_search_limit = 5

            result = await use_case.execute(incoming_message_dto)

        assert isinstance(result, Success)
        assert result.value.response_sent is True
        # Conversation should be saved with AI disabled
        assert mock_conversation_repository.save.call_count >= 2

    @pytest.mark.asyncio
    async def test_restaurant_closed_action(
        self,
        mock_restaurant_repository,
        mock_conversation_repository,
        mock_message_repository,
        mock_messaging_client,
        mock_ai_agent,
        incoming_message_dto,
    ):
        """Test that restaurant_closed action disables AI until opening."""
        # Configure agent to trigger restaurant_closed
        agent_response = MagicMock()
        agent_response.message = "Estamos fechados. Abrimos amanhã às 11h."
        agent_response.should_send = True
        agent_response.triggered_actions = ["restaurant_closed"]
        mock_ai_agent.process = AsyncMock(return_value=Success(agent_response))

        use_case = ProcessIncomingMessageUseCase(
            restaurant_repository=mock_restaurant_repository,
            conversation_repository=mock_conversation_repository,
            message_repository=mock_message_repository,
            messaging_client=mock_messaging_client,
            ai_agent=mock_ai_agent,
        )

        with patch("tacto.application.use_cases.process_incoming_message.get_settings") as mock_settings:
            mock_settings.return_value.app.conversation_history_limit = 10
            mock_settings.return_value.app.bypass_hours_check = True
            mock_settings.return_value.app.ai_disable_hours = 12
            mock_settings.return_value.app.ai_reopen_buffer_minutes = 30
            mock_settings.return_value.gemini.level1_rag_search_limit = 5

            result = await use_case.execute(incoming_message_dto)

        assert isinstance(result, Success)
        assert result.value.response_sent is True


class TestProcessIncomingMessageErrorHandling:
    """Test error handling in use case."""

    @pytest.mark.asyncio
    async def test_ai_generation_failure(
        self,
        mock_restaurant_repository,
        mock_conversation_repository,
        mock_message_repository,
        mock_messaging_client,
        mock_ai_agent,
        incoming_message_dto,
    ):
        """Test handling when AI fails to generate response."""
        mock_ai_agent.process = AsyncMock(
            return_value=Failure(Exception("AI service unavailable"))
        )

        use_case = ProcessIncomingMessageUseCase(
            restaurant_repository=mock_restaurant_repository,
            conversation_repository=mock_conversation_repository,
            message_repository=mock_message_repository,
            messaging_client=mock_messaging_client,
            ai_agent=mock_ai_agent,
        )

        with patch("tacto.application.use_cases.process_incoming_message.get_settings") as mock_settings:
            mock_settings.return_value.app.conversation_history_limit = 10
            mock_settings.return_value.app.bypass_hours_check = True
            mock_settings.return_value.gemini.level1_rag_search_limit = 5

            result = await use_case.execute(incoming_message_dto)

        assert isinstance(result, Success)
        assert result.value.response_sent is False
        assert "AI generation failed" in result.value.error

    @pytest.mark.asyncio
    async def test_messaging_client_failure(
        self,
        mock_restaurant_repository,
        mock_conversation_repository,
        mock_message_repository,
        mock_messaging_client,
        mock_ai_agent,
        incoming_message_dto,
    ):
        """Test handling when messaging client fails to send."""
        mock_messaging_client.send_message = AsyncMock(
            return_value=Failure(Exception("WhatsApp API error"))
        )

        use_case = ProcessIncomingMessageUseCase(
            restaurant_repository=mock_restaurant_repository,
            conversation_repository=mock_conversation_repository,
            message_repository=mock_message_repository,
            messaging_client=mock_messaging_client,
            ai_agent=mock_ai_agent,
        )

        with patch("tacto.application.use_cases.process_incoming_message.get_settings") as mock_settings:
            mock_settings.return_value.app.conversation_history_limit = 10
            mock_settings.return_value.app.bypass_hours_check = True
            mock_settings.return_value.app.ai_disable_hours = 12
            mock_settings.return_value.gemini.level1_rag_search_limit = 5

            result = await use_case.execute(incoming_message_dto)

        assert isinstance(result, Success)
        assert result.value.response_sent is False
        assert "Failed to send" in result.value.error
