"""
Level 2 (ORDER) AI Agent — Coleta Pedidos com Handoff.

Infrastructure implementation for order-taking conversations.
Implements the BaseAgent port defined in domain/ai_assistance/ports/agent_port.py.

Features:
- Order taking with price calculation
- Cart state management
- Menu item lookup via RAG
- Multi-tenant support via restaurant_id
- Three-level memory integration
- Same deactivation rules as Level 1

IMPORTANTE:
Este agente NUNCA finaliza pedidos automaticamente.
Após coletar todos os dados (itens, endereço, pagamento),
ele SEMPRE faz handoff para um atendente humano confirmar
a taxa de entrega e finalizar o pedido.
"""

import time
from typing import Optional

import structlog
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from langchain_google_genai import ChatGoogleGenerativeAI

from tacto.config import get_settings
from tacto.application.ports.agent_port import BaseAgent
from tacto.application.services.order_state_service import OrderStateService
from tacto.domain.ai_assistance.value_objects.agent_context import AgentContext
from tacto.domain.ai_assistance.value_objects.agent_response import AgentResponse
from tacto.domain.order.value_objects.order_state import OrderState
from tacto.infrastructure.ai.prompts.level2_prompts import Level2Prompts
from tacto.application.services.memory_orchestration_service import MemoryManager
from tacto.shared.application import Err, Failure, Ok, Success


logger = structlog.get_logger()


class Level2Agent(BaseAgent):
    """
    Level 2 (ORDER) AI Agent.

    Provides order-taking capabilities with price calculation.
    Multi-tenant: each restaurant has its own prompt and configuration.
    """

    def __init__(
        self,
        order_service: Optional[OrderStateService] = None,
        memory_manager: Optional[MemoryManager] = None,
        model_name: Optional[str] = None,
    ) -> None:
        """
        Initialize Level 2 agent.

        Args:
            order_service: Service for managing order state
            memory_manager: Optional memory manager for conversation context
            model_name: LLM model name (defaults to settings)
        """
        settings = get_settings()
        self._model_name = model_name or settings.gemini.level2_llm_model
        self._order_service = order_service
        self._memory = memory_manager
        self._llm: Optional[ChatGoogleGenerativeAI] = None
        self._chain = None
        self._initialized = False

    @property
    def level(self) -> int:
        """Return automation level."""
        return 2

    @property
    def name(self) -> str:
        """Return agent name."""
        return "Level2Agent"

    async def initialize(self) -> Success[bool] | Failure[Exception]:
        """Initialize LangChain components and build LCEL chain."""
        try:
            settings = get_settings()

            self._llm = ChatGoogleGenerativeAI(
                model=self._model_name,
                google_api_key=settings.gemini.api_key,
                temperature=settings.gemini.level2_temperature,
                max_tokens=settings.gemini.level2_max_tokens,
                convert_system_message_to_human=True,
            )

            self._chain = self._build_chain()
            self._initialized = True
            logger.info("Level2Agent initialized", model=self._model_name)

            return Ok(True)

        except Exception as e:
            logger.error("Failed to initialize Level2Agent", error=str(e))
            return Err(e)

    def _build_chain(self):
        """Build LCEL chain for structured LangSmith observability."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", "{system_prompt}"),
            MessagesPlaceholder("history"),
            ("human", "{input}"),
        ])
        return prompt | self._llm | StrOutputParser()

    async def shutdown(self) -> Success[bool] | Failure[Exception]:
        """Cleanup resources."""
        self._llm = None
        self._initialized = False
        return Ok(True)

    async def process(
        self,
        message: str,
        context: AgentContext,
        conversation_history: list[dict[str, str]],
    ) -> Success[AgentResponse] | Failure[Exception]:
        """
        Process incoming message and generate order-aware response.

        Args:
            message: Customer message text
            context: Agent context with restaurant info
            conversation_history: Recent messages for context

        Returns:
            Success with AgentResponse or Failure
        """
        start_time = time.time()

        if not self._initialized:
            init_result = await self.initialize()
            if isinstance(init_result, Failure):
                return init_result

        try:
            log = logger.bind(
                restaurant_id=str(context.restaurant_id),
                customer_phone=context.customer_phone,
            )

            customer_name = context.customer_name or "Cliente"
            triggered_actions = []

            # Check if restaurant is closed — before calling LLM
            if not context.is_open:
                closed_message = Level2Prompts.format_closed_response(
                    menu_url=context.menu_url,
                    next_opening=context.next_opening_text,
                )
                log.info("restaurant_closed", customer_phone=context.customer_phone)
                return Ok(
                    AgentResponse(
                        message=closed_message,
                        should_send=True,
                        metadata={
                            "customer_name": customer_name,
                            "restaurant_name": context.restaurant_name,
                        },
                        tokens_used=0,
                        processing_time_ms=int((time.time() - start_time) * 1000),
                        triggered_actions=["restaurant_closed"],
                    )
                )

            # Human handoff detection — before calling LLM
            if Level2Prompts.is_human_handoff_request(message):
                handoff_message = Level2Prompts.get_human_handoff_response()
                log.info("human_handoff_detected", message=message[:60])
                triggered_actions.append("human_handoff")
                return Ok(
                    AgentResponse(
                        message=handoff_message,
                        should_send=True,
                        metadata={
                            "customer_name": customer_name,
                            "restaurant_name": context.restaurant_name,
                            "handoff_requested": True,
                        },
                        tokens_used=0,
                        processing_time_ms=int((time.time() - start_time) * 1000),
                        triggered_actions=triggered_actions,
                    )
                )

            # Detect intent for logging
            intent = Level2Prompts.detect_intent(message)
            log = log.bind(detected_intent=intent)

            # Load order state
            order_state_text = "Carrinho vazio"
            if self._order_service:
                order_result = await self._order_service.get_or_create(
                    context.restaurant_id,
                    context.customer_phone,
                    context.customer_name,
                )
                if isinstance(order_result, Success) and order_result.value:
                    order_state_text = order_result.value.to_cart_context()

            # Load memory context
            short_term_memory = ""
            medium_term_memory = ""
            long_term_memory = ""

            if self._memory:
                memory_result = await self._memory.load_context(
                    context.restaurant_id,
                    context.customer_phone,
                    context.customer_name,
                )
                if isinstance(memory_result, Success):
                    mem = memory_result.value
                    short_term_memory = mem.get_short_term_summary()
                    medium_term_memory = mem.get_medium_term_summary()
                    long_term_memory = mem.get_long_term_summary()

                    # Semantic search for relevant past entries
                    relevant_result = await self._memory.search_relevant(
                        context.restaurant_id,
                        context.customer_phone,
                        query=message,
                        limit=8,
                    )
                    if isinstance(relevant_result, Success) and relevant_result.value:
                        extra = "\n".join(
                            f"- {e.content}"
                            for e in relevant_result.value
                            if f"- {e.content}" not in long_term_memory
                        )
                        if extra:
                            long_term_memory = f"{long_term_memory}\n{extra}".strip()

            # Build system prompt
            system_prompt = Level2Prompts.build_system_prompt(
                restaurant_name=context.restaurant_name,
                attendant_name=context.attendant_name,
                order_state=order_state_text,
                rag_context_with_prices=context.rag_context or "",
                restaurant_address=context.tacto_address or "",
                opening_hours=context.tacto_hours or context.opening_hours or "",
                payment_methods="Dinheiro, Cartão, PIX",
                short_term_memory=short_term_memory,
                medium_term_memory=medium_term_memory,
                long_term_memory=long_term_memory,
                custom_prompt=context.prompt_default or "",
            )

            # Build conversation history
            history = []
            for msg in conversation_history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "user":
                    history.append(HumanMessage(content=content))
                elif role == "assistant":
                    history.append(AIMessage(content=content))

            # Track triggered actions based on intent
            if intent == "add_item":
                triggered_actions.append("order_add_item")
            elif intent == "remove_item":
                triggered_actions.append("order_remove_item")
            elif intent == "review":
                triggered_actions.append("order_review")
            elif intent == "confirm":
                triggered_actions.append("order_confirm")

            # Check if order is ready for handoff (all data collected + customer confirmed)
            should_handoff = False
            if self._order_service:
                current_order = await self._order_service.get_current(
                    context.restaurant_id,
                    context.customer_phone,
                )
                if isinstance(current_order, Success) and current_order.value:
                    order = current_order.value
                    # If order has items, address, payment AND customer is confirming
                    if (
                        intent == "confirm"
                        and not order.is_empty
                        and order.delivery_address
                        and order.payment_method
                        and order.status.value == "confirming"
                    ):
                        should_handoff = True
                        triggered_actions.append("handoff_to_human")
                        log.info("Order complete, triggering handoff to human")

            # Configure LangSmith tracing
            config = RunnableConfig(
                tags=["level2", f"restaurant:{context.restaurant_id}", f"intent:{intent}"],
                metadata={
                    "restaurant_id": str(context.restaurant_id),
                    "restaurant_name": context.restaurant_name,
                    "customer_phone": context.customer_phone,
                    "intent": intent,
                },
                run_name=f"Level2Agent/{context.restaurant_name}",
            )

            # Generate response
            response_text = await self._chain.ainvoke(
                {
                    "system_prompt": system_prompt,
                    "history": history,
                    "input": message,
                },
                config=config,
            )

            # Store messages in memory
            if self._memory:
                await self._memory.add_message(
                    context.restaurant_id,
                    context.customer_phone,
                    "user",
                    message,
                )
                await self._memory.add_message(
                    context.restaurant_id,
                    context.customer_phone,
                    "assistant",
                    response_text,
                )

            processing_time = int((time.time() - start_time) * 1000)

            log.info(
                "Level2Agent response generated",
                processing_time_ms=processing_time,
                intent=intent,
                actions=triggered_actions,
            )

            return Ok(
                AgentResponse(
                    message=response_text,
                    should_send=True,
                    metadata={
                        "customer_name": customer_name,
                        "restaurant_name": context.restaurant_name,
                        "intent": intent,
                        "should_handoff": should_handoff,
                        "disable_ai_after_response": should_handoff,
                    },
                    tokens_used=0,
                    processing_time_ms=processing_time,
                    triggered_actions=triggered_actions,
                )
            )

        except Exception as e:
            logger.error("Level2Agent processing error", error=str(e))
            return Err(e)
