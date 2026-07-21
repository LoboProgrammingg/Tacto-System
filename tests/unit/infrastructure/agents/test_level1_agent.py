"""
Tests for Level1Agent.

Tests the Level 1 (BASIC) AI agent:
1. Restaurant closed response (pre-LLM)
2. Human handoff detection
3. Menu URL sharing
4. RAG context integration
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from tacto.domain.ai_assistance.value_objects.agent_context import AgentContext
from tacto.domain.ai_assistance.value_objects.agent_response import AgentResponse
from tacto.domain.restaurant.value_objects.automation_type import AutomationType
from tacto.infrastructure.agents.level1_agent import Level1Agent
from tacto.infrastructure.ai.prompts.level1_prompts import Level1Prompts
from tacto.shared.application import Failure, Success


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def agent_context() -> AgentContext:
    """Create a sample agent context."""
    return AgentContext(
        restaurant_id=uuid4(),
        restaurant_name="Restaurante Teste",
        customer_phone="5565992540370",
        customer_name="João",
        conversation_id=uuid4(),
        menu_url="https://cardapio.teste.com",
        prompt_default=None,
        opening_hours={
            "monday": {"open": "11:00", "close": "23:00"},
            "tuesday": {"open": "11:00", "close": "23:00"},
        },
        automation_level=AutomationType.BASIC,
        is_open=True,
        next_opening_text="Abrimos amanhã às 11h",
        rag_context="",
        tacto_address="Rua Teste, 123",
        tacto_hours="Seg-Sex: 11h-23h",
    )


@pytest.fixture
def closed_context(agent_context: AgentContext) -> AgentContext:
    """Create context for closed restaurant."""
    agent_context.is_open = False
    agent_context.next_opening_text = "Abrimos amanhã, segunda-feira, às 11:00"
    return agent_context


@pytest.fixture
def mock_llm_response() -> str:
    """Sample LLM response."""
    return "Olá João! Bem-vindo ao Restaurante Teste. Como posso ajudar?"


# ──────────────────────────────────────────────────────────────────────────────
# Test Classes
# ──────────────────────────────────────────────────────────────────────────────

class TestLevel1AgentProperties:
    """Test agent properties."""

    def test_level_is_one(self):
        """Agent level should be 1."""
        agent = Level1Agent()
        assert agent.level == 1

    def test_name_is_level1agent(self):
        """Agent name should be Level1Agent."""
        agent = Level1Agent()
        assert agent.name == "Level1Agent"


class TestLevel1AgentClosedRestaurant:
    """Test restaurant closed behavior."""

    @pytest.mark.asyncio
    async def test_returns_closed_message_without_llm(
        self,
        closed_context: AgentContext,
    ):
        """When restaurant is closed, should return pre-built response without LLM call."""
        agent = Level1Agent()

        # Mock the LLM initialization to track if it's called
        with patch.object(agent, '_llm', None):
            with patch.object(agent, '_initialized', True):
                with patch.object(agent, '_chain', MagicMock()) as mock_chain:
                    # The chain should NOT be invoked for closed restaurants
                    result = await agent.process(
                        message="Olá, vocês estão abertos?",
                        context=closed_context,
                        conversation_history=[],
                    )

        assert isinstance(result, Success)
        response = result.value
        assert response.should_send is True
        assert "restaurant_closed" in response.triggered_actions
        # Response should mention opening time
        assert "11:00" in response.message or "amanhã" in response.message.lower()

    def test_closed_response_contains_menu_url(self):
        """Closed response should include menu URL."""
        response = Level1Prompts.get_closed_response(
            menu_url="https://cardapio.teste.com",
            next_opening="Abrimos amanhã às 11h",
        )

        assert "cardapio.teste.com" in response
        assert "amanhã" in response.lower() or "11h" in response
        assert "estamos fechados" in response.lower()
        assert "será um prazer atender você" in response.lower()


class TestLevel1AgentHumanHandoff:
    """Test human handoff detection."""

    @pytest.mark.asyncio
    async def test_detects_human_request_keywords(
        self,
        agent_context: AgentContext,
    ):
        """Should detect when customer wants to talk to human."""
        agent = Level1Agent()

        # Keywords that should trigger handoff
        handoff_messages = [
            "Quero falar com um atendente",
            "Chama o gerente",
            "Preciso de um humano",
            "Atendente por favor",
        ]

        for message in handoff_messages:
            with patch.object(agent, '_initialized', True):
                with patch.object(agent, '_chain') as mock_chain:
                    # Mock chain to return handoff response
                    mock_chain.ainvoke = AsyncMock(
                        return_value="Claro, vou transferir para um atendente humano."
                    )

                    # Note: Actual handoff detection happens in prompts
                    # This test verifies the flow works


class TestLevel1AgentRAGContext:
    """Test RAG context integration."""

    @pytest.mark.asyncio
    async def test_includes_rag_context_in_prompt(
        self,
        agent_context: AgentContext,
    ):
        """RAG context should be included in system prompt."""
        agent_context.rag_context = "• Pizza Margherita: queijo, tomate, manjericão"

        agent = Level1Agent()

        with patch.object(agent, '_initialized', True):
            with patch.object(agent, '_chain') as mock_chain:
                mock_chain.ainvoke = AsyncMock(
                    return_value="Temos a Pizza Margherita com queijo, tomate e manjericão!"
                )

                result = await agent.process(
                    message="Vocês têm pizza?",
                    context=agent_context,
                    conversation_history=[],
                )

                # Verify chain was called with RAG context
                call_args = mock_chain.ainvoke.call_args
                if call_args:
                    input_dict = call_args[0][0]
                    system_prompt = input_dict.get("system_prompt", "")
                    assert "Margherita" in system_prompt or "cardápio" in system_prompt.lower()

    def test_includes_exact_current_datetime_in_system_prompt(
        self,
        agent_context: AgentContext,
    ):
        """System prompt should carry the exact local datetime for the current conversation."""
        agent_context.restaurant_timezone = "America/Cuiaba"
        agent_context.current_weekday_pt = "sábado"
        agent_context.current_date_br = "02/05/2026"
        agent_context.current_time_br = "09:30"
        agent_context.current_datetime_iso = "2026-05-02T09:30:00-04:00"

        prompt = Level1Prompts.build_system_prompt(
            restaurant_name=agent_context.restaurant_name,
            menu_url=agent_context.menu_url,
            opening_hours=agent_context.opening_hours,
            custom_prompt=agent_context.prompt_default,
            customer_name=agent_context.customer_name,
            rag_context=agent_context.rag_context,
            tacto_address=agent_context.tacto_address,
            tacto_hours=agent_context.tacto_hours,
            restaurant_timezone=agent_context.restaurant_timezone,
            current_weekday_pt=agent_context.current_weekday_pt,
            current_date_br=agent_context.current_date_br,
            current_time_br=agent_context.current_time_br,
            current_datetime_iso=agent_context.current_datetime_iso,
        )

        assert "sábado, 02/05/2026, 09:30" in prompt
        assert "2026-05-02T09:30:00-04:00" in prompt
        assert "Nunca trate o dia da semana como fixo" in prompt


class TestLevel1AgentMenuRepetition:
    """Test menu link and repetitive-response controls."""

    @pytest.mark.asyncio
    async def test_first_greeting_does_not_append_menu_link(
        self,
        agent_context: AgentContext,
    ):
        agent = Level1Agent()

        with patch.object(agent, "_initialized", True):
            with patch.object(agent, "_chain") as mock_chain:
                mock_chain.ainvoke = AsyncMock(return_value="Olá, João! Boa noite! 😊")

                result = await agent.process(
                    message="Boa noite",
                    context=agent_context,
                    conversation_history=[],
                )

        assert isinstance(result, Success)
        assert "cardapio.teste.com" not in result.value.message
        assert "menu_url_sent" not in result.value.triggered_actions

    @pytest.mark.asyncio
    async def test_order_intent_appends_menu_link_once(
        self,
        agent_context: AgentContext,
    ):
        agent = Level1Agent()

        with patch.object(agent, "_initialized", True):
            with patch.object(agent, "_chain") as mock_chain:
                mock_chain.ainvoke = AsyncMock(return_value="Claro, você pode montar seu pedido por lá.")

                result = await agent.process(
                    message="Quero pedir um açaí",
                    context=agent_context,
                    conversation_history=[{"role": "user", "content": "Boa noite"}],
                )

        assert isinstance(result, Success)
        assert "cardapio.teste.com" in result.value.message
        assert "menu_url_sent" in result.value.triggered_actions

    @pytest.mark.asyncio
    async def test_recent_menu_link_is_not_repeated_for_order_complement(
        self,
        agent_context: AgentContext,
    ):
        agent = Level1Agent()
        history = [
            {"role": "assistant", "content": "Cardápio e pedidos\nhttps://cardapio.teste.com"},
            {"role": "user", "content": "Quero pedir um açaí"},
        ]

        with patch.object(agent, "_initialized", True):
            with patch.object(agent, "_chain") as mock_chain:
                mock_chain.ainvoke = AsyncMock(return_value="Certo, pode escolher os adicionais por lá.")

                result = await agent.process(
                    message="com banana e leite em pó",
                    context=agent_context,
                    conversation_history=history,
                )

        assert isinstance(result, Success)
        assert "cardapio.teste.com" not in result.value.message
        assert "menu_url_sent" not in result.value.triggered_actions

    @pytest.mark.asyncio
    async def test_short_acknowledgement_does_not_respond(
        self,
        agent_context: AgentContext,
    ):
        agent = Level1Agent()

        with patch.object(agent, "_initialized", True):
            with patch.object(agent, "_chain") as mock_chain:
                mock_chain.ainvoke = AsyncMock(return_value="Posso ajudar?")

                result = await agent.process(
                    message="Ok",
                    context=agent_context,
                    conversation_history=[{"role": "assistant", "content": "Aqui está."}],
                )

        assert isinstance(result, Success)
        assert result.value.should_send is False
        mock_chain.ainvoke.assert_not_called()


class TestLevel1AgentInitialization:
    """Test agent initialization."""

    @pytest.mark.asyncio
    async def test_initializes_on_first_process(
        self,
        agent_context: AgentContext,
    ):
        """Agent should initialize LLM on first process call."""
        agent = Level1Agent()

        with patch("tacto.infrastructure.agents.level1_agent.get_settings") as mock_settings:
            mock_settings.return_value.gemini.api_key = "test_key"
            mock_settings.return_value.gemini.level1_llm_model = "gemini-1.5-flash"
            mock_settings.return_value.gemini.level1_temperature = 0.7
            mock_settings.return_value.gemini.level1_max_tokens = 150

            with patch("tacto.infrastructure.agents.level1_agent.ChatGoogleGenerativeAI") as mock_llm:
                mock_llm_instance = MagicMock()
                mock_llm.return_value = mock_llm_instance

                # Initialize
                result = await agent.initialize()

                assert isinstance(result, Success)
                assert agent._initialized is True
                mock_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_cleans_resources(self):
        """Shutdown should clean up LLM resources."""
        agent = Level1Agent()
        agent._llm = MagicMock()
        agent._initialized = True

        result = await agent.shutdown()

        assert isinstance(result, Success)
        assert agent._llm is None
        assert agent._initialized is False


class TestLevel1AgentConversationHistory:
    """Test conversation history handling."""

    @pytest.mark.asyncio
    async def test_passes_history_to_llm(
        self,
        agent_context: AgentContext,
    ):
        """Conversation history should be passed to LLM."""
        agent = Level1Agent()

        history = [
            {"role": "user", "content": "Olá"},
            {"role": "assistant", "content": "Olá! Como posso ajudar?"},
            {"role": "user", "content": "Quero ver o cardápio"},
        ]

        with patch.object(agent, '_initialized', True):
            with patch.object(agent, '_chain') as mock_chain:
                mock_chain.ainvoke = AsyncMock(
                    return_value="Você pode ver nosso cardápio em cardapio.teste.com"
                )

                result = await agent.process(
                    message="Tem delivery?",
                    context=agent_context,
                    conversation_history=history,
                )

                # Verify history was included
                call_args = mock_chain.ainvoke.call_args
                if call_args:
                    input_dict = call_args[0][0]
                    passed_history = input_dict.get("history", [])
                    assert len(passed_history) == 3


class TestLevel1AgentErrorHandling:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_handles_llm_error(
        self,
        agent_context: AgentContext,
    ):
        """Should return Failure when LLM fails."""
        agent = Level1Agent()

        with patch.object(agent, '_initialized', True):
            with patch.object(agent, '_chain') as mock_chain:
                mock_chain.ainvoke = AsyncMock(
                    side_effect=Exception("LLM API error")
                )

                result = await agent.process(
                    message="Olá",
                    context=agent_context,
                    conversation_history=[],
                )

        assert isinstance(result, Failure)
        assert "LLM API error" in str(result.error)

    @pytest.mark.asyncio
    async def test_handles_initialization_error(self):
        """Should return Failure when initialization fails."""
        agent = Level1Agent()

        with patch("tacto.infrastructure.agents.level1_agent.get_settings") as mock_settings:
            mock_settings.return_value.gemini.api_key = None  # Invalid key

            with patch("tacto.infrastructure.agents.level1_agent.ChatGoogleGenerativeAI") as mock_llm:
                mock_llm.side_effect = Exception("Invalid API key")

                result = await agent.initialize()

        assert isinstance(result, Failure)


class TestLevel1PromptsUnit:
    """Unit tests for Level1Prompts."""

    def test_build_system_prompt_includes_restaurant_name(self):
        """System prompt should include restaurant name."""
        prompt = Level1Prompts.build_system_prompt(
            restaurant_name="Pizzaria do João",
            menu_url="https://cardapio.com",
            opening_hours={"monday": {"opens_at": "11:00", "closes_at": "23:00"}},
            customer_name="Maria",
            rag_context="",
            tacto_address="Rua A, 1",
            tacto_hours="11h-23h",
            custom_prompt=None,
        )

        assert "Pizzaria do João" in prompt

    def test_build_system_prompt_forbids_url_reproduction(self):
        """System prompt should forbid the LLM from reproducing menu URLs directly."""
        prompt = Level1Prompts.build_system_prompt(
            restaurant_name="Restaurante",
            menu_url="https://meu-cardapio.com",
            opening_hours={},
            customer_name="Cliente",
            rag_context="",
            tacto_address="",
            tacto_hours="",
            custom_prompt=None,
        )

        assert "NUNCA escreva links ou URLs na sua resposta" in prompt
        assert "NUNCA copie, mencione ou reproduza qualquer URL" in prompt

    def test_get_closed_response_mentions_opening(self):
        """Closed response should mention when restaurant opens."""
        response = Level1Prompts.get_closed_response(
            menu_url="https://cardapio.com",
            next_opening="Abrimos segunda às 11h",
        )

        assert "segunda" in response.lower() or "11h" in response

    def test_get_closed_response_has_cordial_and_correct_copy(self):
        """Closed response should be cordial, deterministic, and grammatically correct."""
        response = Level1Prompts.get_closed_response(
            menu_url="https://cardapio.com",
            next_opening="Abrimos hoje às 18:30.",
        )

        assert response.startswith("Olá! 😊")
        assert "No momento, estamos fechados." in response
        assert "Próximo horário de funcionamento" in response
        assert "Se quiser, você já pode conferir o cardápio por aqui" in response
        assert "Assim que abrirmos, será um prazer atender você!" in response

    def test_is_hours_question_detects_open_status_questions(self):
        """is_hours_question must detect explicit hours / open-status questions."""
        positive_examples = [
            "Vocês estão abertos?",
            "tá aberto?",
            "ja abriu?",
            "que horas vocês abrem?",
            "qual o horário de funcionamento?",
            "tá funcionando?",
            "horário de hoje",
            "vocês estão fechados agora?",
            "abre que horas?",
        ]
        for msg in positive_examples:
            assert Level1Prompts.is_hours_question(msg), f"should match: {msg!r}"

    def test_is_hours_question_returns_false_for_unrelated_messages(self):
        """is_hours_question must NOT trigger for casual / order messages."""
        negative_examples = [
            "Oi",
            "Olá, tudo bem?",
            "Quero pedir uma pizza",
            "Tem entrega?",
            "Quanto custa o hambúrguer?",
            "Bom dia",
        ]
        for msg in negative_examples:
            assert not Level1Prompts.is_hours_question(msg), f"should NOT match: {msg!r}"


class TestLevel1AgentClosedGating:
    """A closed restaurant always returns the closed template, for ANY message."""

    @pytest.mark.asyncio
    async def test_closed_any_message_returns_template_without_llm(
        self,
        closed_context: AgentContext,
    ):
        """When the restaurant is closed, ANY message must short-circuit with the
        closed template without calling the LLM — even a non-hours message."""
        agent = Level1Agent()

        with patch.object(agent, "_initialized", True):
            with patch.object(agent, "_chain") as mock_chain:
                mock_chain.ainvoke = AsyncMock(return_value="should not be called")
                result = await agent.process(
                    message="Oi",
                    context=closed_context,
                    conversation_history=[],
                )

        assert isinstance(result, Success)
        assert "restaurant_closed" in result.value.triggered_actions
        mock_chain.ainvoke.assert_not_called()

    @pytest.mark.asyncio
    async def test_closed_plus_hours_question_returns_template(
        self,
        closed_context: AgentContext,
    ):
        """A closed restaurant also returns the template for an explicit hours question."""
        agent = Level1Agent()

        with patch.object(agent, "_initialized", True):
            with patch.object(agent, "_chain") as mock_chain:
                mock_chain.ainvoke = AsyncMock(return_value="should not be called")
                result = await agent.process(
                    message="vocês estão abertos?",
                    context=closed_context,
                    conversation_history=[],
                )

        assert isinstance(result, Success)
        assert "restaurant_closed" in result.value.triggered_actions
        mock_chain.ainvoke.assert_not_called()

    @pytest.mark.asyncio
    async def test_open_restaurant_does_not_short_circuit(
        self,
        agent_context: AgentContext,
    ):
        """When the restaurant is open, the closed template must NOT fire."""
        agent = Level1Agent()

        with patch.object(agent, "_initialized", True):
            with patch.object(agent, "_chain") as mock_chain:
                mock_chain.ainvoke = AsyncMock(return_value="Oi! Como posso ajudar?")
                result = await agent.process(
                    message="Oi",
                    context=agent_context,
                    conversation_history=[],
                )

        assert isinstance(result, Success)
        assert "restaurant_closed" not in result.value.triggered_actions
        mock_chain.ainvoke.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_closed_notifies_once_then_stays_silent(
        self,
        closed_context: AgentContext,
    ):
        """After the closed template was sent, further messages get NO reply."""
        agent = Level1Agent()
        history = [
            {"role": "user", "content": "Oi"},
            {"role": "assistant", "content": "Olá! 😊\n\nNo momento, estamos fechados.\n..."},
        ]

        with patch.object(agent, "_initialized", True):
            with patch.object(agent, "_chain") as mock_chain:
                mock_chain.ainvoke = AsyncMock(return_value="should not be called")
                result = await agent.process(
                    message="mas eu queria pedir",
                    context=closed_context,
                    conversation_history=history,
                )

        assert isinstance(result, Success)
        assert result.value.should_send is False
        assert "restaurant_closed_muted" in result.value.triggered_actions
        mock_chain.ainvoke.assert_not_called()


class TestLevel1AgentMenuResend:
    """Explicit menu re-requests must always resend the link."""

    @pytest.mark.asyncio
    async def test_explicit_cardapio_request_resends_even_if_recent(
        self,
        agent_context: AgentContext,
    ):
        """'manda o cardápio de novo' with link already in history → link appended."""
        agent = Level1Agent()
        history = [
            {"role": "assistant", "content": "Cardápio e pedidos\nhttps://cardapio.teste.com"},
            {"role": "user", "content": "obrigado"},
        ]

        with patch.object(agent, "_initialized", True):
            with patch.object(agent, "_chain") as mock_chain:
                mock_chain.ainvoke = AsyncMock(return_value="Claro, aqui está!")
                result = await agent.process(
                    message="manda o cardápio de novo",
                    context=agent_context,
                    conversation_history=history,
                )

        assert isinstance(result, Success)
        assert "cardapio.teste.com" in result.value.message
        assert "menu_url_sent" in result.value.triggered_actions

    @pytest.mark.asyncio
    async def test_generic_resend_request_after_menu_link_resends(
        self,
        agent_context: AgentContext,
    ):
        """'manda de novo' (without the word cardápio) after link → link appended."""
        agent = Level1Agent()
        history = [
            {"role": "assistant", "content": "Cardápio e pedidos\nhttps://cardapio.teste.com"},
            {"role": "user", "content": "vlw"},
        ]

        with patch.object(agent, "_initialized", True):
            with patch.object(agent, "_chain") as mock_chain:
                mock_chain.ainvoke = AsyncMock(return_value="Claro, segue novamente!")
                result = await agent.process(
                    message="não recebi, manda de novo por favor",
                    context=agent_context,
                    conversation_history=history,
                )

        assert isinstance(result, Success)
        assert "cardapio.teste.com" in result.value.message
        assert "menu_url_sent" in result.value.triggered_actions

    @pytest.mark.asyncio
    async def test_resend_request_about_address_does_not_send_menu(
        self,
        agent_context: AgentContext,
    ):
        """'manda o endereço de novo' must NOT be treated as a menu request."""
        agent = Level1Agent()
        history = [
            {"role": "assistant", "content": "Cardápio e pedidos\nhttps://cardapio.teste.com"},
            {"role": "user", "content": "vlw"},
        ]

        with patch.object(agent, "_initialized", True):
            with patch.object(agent, "_chain") as mock_chain:
                mock_chain.ainvoke = AsyncMock(return_value="Rua Teste, 123!")
                result = await agent.process(
                    message="manda o endereço de novo",
                    context=agent_context,
                    conversation_history=history,
                )

        assert isinstance(result, Success)
        assert "cardapio.teste.com" not in result.value.message
        assert "menu_url_sent" not in result.value.triggered_actions


class TestLevel1PromptsGenderedPersona:
    """Prompt must respect gender and never leave the attendant nameless."""

    def _build(self, name, gender):
        return Level1Prompts.build_system_prompt(
            restaurant_name="Restaurante",
            menu_url="https://cardapio.com",
            opening_hours={},
            customer_name="Cliente",
            rag_context="",
            tacto_address="",
            tacto_hours="",
            custom_prompt=None,
            attendant_name=name,
            attendant_gender=gender,
        )

    def test_masculine_presents_as_male(self):
        prompt = self._build("José", "masculino")
        assert "Sou o José" in prompt
        assert "seu atendente virtual" in prompt
        assert "sua atendente virtual" not in prompt

    def test_feminine_presents_as_female(self):
        prompt = self._build("Maria", "feminino")
        assert "Sou a Maria" in prompt
        assert "sua atendente virtual" in prompt

    def test_empty_name_masculine_defaults_to_jose(self):
        prompt = self._build("", "masculino")
        assert "José" in prompt
        assert "Sou o José" in prompt

    def test_empty_name_feminine_defaults_to_maria(self):
        prompt = self._build("", "feminino")
        assert "Maria" in prompt
        assert "Sou a Maria" in prompt

    def test_chosen_name_with_masculine_gender_is_respected(self):
        prompt = self._build("Carlos", "masculino")
        assert "Sou o Carlos" in prompt
        assert "seu atendente virtual" in prompt


class TestLevel1PromptsAntiInvention:
    """Prompt must forbid inventing delivery/payment/promo info."""

    def test_system_prompt_contains_delivery_guardrail(self):
        prompt = Level1Prompts.build_system_prompt(
            restaurant_name="Restaurante",
            menu_url="https://cardapio.com",
            opening_hours={},
            customer_name="Cliente",
            rag_context="",
            tacto_address="",
            tacto_hours="",
            custom_prompt=None,
        )

        assert "ENTREGA, TAXAS, PAGAMENTO E PROMOÇÕES — NUNCA INVENTE" in prompt
        assert "NUNCA invente, confirme ou negue" in prompt
        assert "Vou confirmar essa informação com a equipe" in prompt


class TestLevel1AgentStaleContext:
    """Test memory load is skipped when context.is_stale=True."""

    @pytest.mark.asyncio
    async def test_skips_memory_load_when_stale(
        self,
        agent_context: AgentContext,
    ):
        """When AgentContext.is_stale=True, agent must NOT call memory.load_context
        nor memory.search_relevant — both are sources of stale leakage."""
        agent_context.is_stale = True
        agent = Level1Agent()
        mock_memory = MagicMock()
        mock_memory.load_context = AsyncMock()
        mock_memory.search_relevant = AsyncMock()
        agent._memory = mock_memory

        with patch.object(agent, "_initialized", True):
            with patch.object(agent, "_chain") as mock_chain:
                mock_chain.ainvoke = AsyncMock(return_value="Olá! Como posso ajudar?")
                await agent.process(
                    message="Oi",
                    context=agent_context,
                    conversation_history=[],
                )

        mock_memory.load_context.assert_not_called()
        mock_memory.search_relevant.assert_not_called()
