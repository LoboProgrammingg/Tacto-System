"""
Level 1 (BASIC) AI Agent.

Humanized conversational agent for informational responses.
Features:
- Natural conversation with customer name usage
- Menu URL sharing on relevant queries
- Opening hours information
- Multi-tenant support via restaurant_id
- Three-level memory integration
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
from tacto.domain.ai.agents.base_agent import AgentContext, AgentResponse, BaseAgent
from tacto.domain.ai.memory.memory_manager import ConversationMemory, MemoryManager
from tacto.domain.ai.prompts.level1_prompts import Level1Prompts
from tacto.domain.shared.result import Err, Failure, Ok, Success


logger = structlog.get_logger()


class Level1Agent(BaseAgent):
    """
    Level 1 (BASIC) AI Agent.

    Provides humanized informational responses for restaurants.
    Multi-tenant: Each restaurant has its own prompt and configuration.
    """

    def __init__(
        self,
        memory_manager: Optional[MemoryManager] = None,
        model_name: Optional[str] = None,
    ) -> None:
        """
        Initialize Level 1 agent.

        Args:
            memory_manager: Optional memory manager for conversation context
            model_name: LLM model name (defaults to settings)
        """
        settings = get_settings()
        self._model_name = model_name or settings.gemini.level1_llm_model
        self._memory = memory_manager
        self._llm: Optional[ChatGoogleGenerativeAI] = None
        self._chain = None
        self._initialized = False

    @property
    def level(self) -> int:
        """Return automation level."""
        return 1

    @property
    def name(self) -> str:
        """Return agent name."""
        return "Level1Agent"

    async def initialize(self) -> Success[bool] | Failure[Exception]:
        """Initialize LangChain components and build LCEL chain."""
        try:
            settings = get_settings()

            self._llm = ChatGoogleGenerativeAI(
                model=self._model_name,
                google_api_key=settings.gemini.api_key,
                temperature=settings.gemini.level1_temperature,
                max_tokens=settings.gemini.level1_max_tokens,
                convert_system_message_to_human=True,
            )

            self._chain = self._build_chain()
            self._initialized = True
            logger.info("Level1Agent initialized", model=self._model_name)

            return Ok(True)

        except Exception as e:
            logger.error("Failed to initialize Level1Agent", error=str(e))
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
        Process incoming message and generate humanized response.

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

            # Check if restaurant is closed — before calling LLM to save tokens
            if not context.is_open:
                closed_message = Level1Prompts.get_closed_response(
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

            # Human handoff detection — before calling LLM to save tokens
            if Level1Prompts.is_human_handoff_request(message):
                handoff_message = Level1Prompts.get_human_handoff_response(
                    customer_name=customer_name,
                    restaurant_name=context.restaurant_name,
                )
                log.info("human_handoff_detected", message=message[:60])
                return Ok(
                    AgentResponse(
                        message=handoff_message,
                        should_send=True,
                        metadata={
                            "customer_name": customer_name,
                            "restaurant_name": context.restaurant_name,
                        },
                        tokens_used=0,
                        processing_time_ms=int((time.time() - start_time) * 1000),
                        triggered_actions=["human_handoff"],
                    )
                )

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

                    # Enrich long-term with semantically relevant past entries
                    relevant_result = await self._memory.search_relevant(
                        context.restaurant_id,
                        context.customer_phone,
                        query=message,
                        limit=4,
                    )
                    if isinstance(relevant_result, Success) and relevant_result.value:
                        extra = "\n".join(
                            f"- {e.content}"
                            for e in relevant_result.value
                            if f"- {e.content}" not in long_term_memory
                        )
                        if extra:
                            long_term_memory = f"{long_term_memory}\n{extra}".strip()

            system_prompt = Level1Prompts.build_system_prompt(
                restaurant_name=context.restaurant_name,
                menu_url=context.menu_url,
                opening_hours=context.opening_hours,
                custom_prompt=context.prompt_default,
                customer_name=context.customer_name,
                short_term_memory=short_term_memory,
                medium_term_memory=medium_term_memory,
                long_term_memory=long_term_memory,
                rag_context=context.rag_context,
                tacto_address=context.tacto_address,
                tacto_hours=context.tacto_hours,
            )

            history = []
            for msg in conversation_history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "user":
                    history.append(HumanMessage(content=content))
                elif role == "assistant":
                    history.append(AIMessage(content=content))

            if Level1Prompts.should_send_menu(message):
                triggered_actions.append("menu_url_sent")
                log.info("Menu trigger detected", message=message[:50])

            config = RunnableConfig(
                tags=["level1", f"restaurant:{context.restaurant_id}"],
                metadata={
                    "restaurant_id": str(context.restaurant_id),
                    "restaurant_name": context.restaurant_name,
                    "customer_phone": context.customer_phone,
                },
                run_name=f"Level1Agent/{context.restaurant_name}",
            )

            response_text = await self._chain.ainvoke(
                {
                    "system_prompt": system_prompt,
                    "history": history,
                    "input": message,
                },
                config=config,
            )

            if "menu_url_sent" in triggered_actions and context.menu_url not in response_text:
                response_text = f"{response_text}\n\n📋 Cardápio: {context.menu_url}"

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
            tokens_used = 0

            log.info(
                "Level1Agent response generated",
                processing_time_ms=processing_time,
                tokens_used=tokens_used,
                actions=triggered_actions,
            )

            return Ok(
                AgentResponse(
                    message=response_text,
                    should_send=True,
                    metadata={
                        "customer_name": customer_name,
                        "restaurant_name": context.restaurant_name,
                    },
                    tokens_used=tokens_used,
                    processing_time_ms=processing_time,
                    triggered_actions=triggered_actions,
                )
            )

        except Exception as e:
            logger.error("Level1Agent processing error", error=str(e))
            return Err(e)
