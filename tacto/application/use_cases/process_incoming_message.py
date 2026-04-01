"""
ProcessIncomingMessage Use Case.

Core use case for processing incoming WhatsApp messages.
This is the main entry point for the message processing pipeline.
"""

from typing import Optional

import structlog

from tacto.application.dto.message_dto import IncomingMessageDTO, MessageResponseDTO
from tacto.config.settings import get_settings
from tacto.application.ports.agent_port import BaseAgent
from tacto.application.factories.agent_factory import AgentFactory
from tacto.domain.ai_assistance.value_objects.agent_context import AgentContext
from tacto.application.services.memory_orchestration_service import MemoryManager
from tacto.application.ports.embedding_client import EmbeddingClient
from tacto.application.ports.menu_provider import MenuProvider
from tacto.application.ports.messaging_client import MessagingClient
from tacto.application.ports.vector_store import VectorStore
from tacto.domain.messaging.entities.conversation import Conversation
from tacto.domain.messaging.entities.message import Message
from tacto.domain.messaging.repository import ConversationRepository, MessageRepository
from tacto.domain.messaging.value_objects.message_source import MessageSource
from tacto.domain.restaurant.repository import RestaurantRepository
from tacto.domain.restaurant.value_objects.automation_type import AutomationType
from tacto.domain.customer_memory.services.style_analyzer import CustomerStyleAnalyzer
from tacto.shared.application import Failure, Ok, Success
from tacto.shared.domain.value_objects import PhoneNumber


logger = structlog.get_logger()


class ProcessIncomingMessageUseCase:
    """
    Use case for processing incoming WhatsApp messages.

    Implements the core message processing flow:
    1. Validate message (ignore fromMe=true)
    2. Find restaurant by instance_key (canal_master_id)
    3. Find or create conversation
    4. Check if AI is active
    5. Store incoming message
    6. Generate AI response (if applicable)
    7. Send response via WhatsApp
    8. Store outgoing message
    """

    def __init__(
        self,
        restaurant_repository: RestaurantRepository,
        conversation_repository: ConversationRepository,
        message_repository: MessageRepository,
        messaging_client: MessagingClient,
        ai_agent: Optional[BaseAgent] = None,
        agent_factory: Optional[AgentFactory] = None,
        memory_manager: Optional[MemoryManager] = None,
        menu_provider: Optional[MenuProvider] = None,
        vector_store: Optional[VectorStore] = None,
        embedding_client: Optional[EmbeddingClient] = None,
    ) -> None:
        self._restaurant_repo = restaurant_repository
        self._conversation_repo = conversation_repository
        self._message_repo = message_repository
        self._messaging_client = messaging_client
        self._ai_agent = ai_agent
        self._agent_factory = agent_factory
        self._memory_manager = memory_manager
        self._menu_provider = menu_provider
        self._vector_store = vector_store
        self._embedding_client = embedding_client

    async def execute(
        self, dto: IncomingMessageDTO
    ) -> Success[MessageResponseDTO] | Failure[Exception]:
        """
        Execute the message processing use case.

        Args:
            dto: Incoming message data from webhook

        Returns:
            Success with MessageResponseDTO or Failure with error
        """
        log = logger.bind(
            instance_key=dto.instance_key,
            from_phone=dto.clean_phone,
            from_me=dto.from_me,
            source=dto.source,
        )

        restaurant_result = await self._restaurant_repo.find_by_canal_master_id(
            dto.instance_key
        )

        if isinstance(restaurant_result, Failure):
            log.error("Failed to find restaurant", error=str(restaurant_result.error))
            return restaurant_result

        restaurant = restaurant_result.value
        if restaurant is None:
            log.warning("Restaurant not found for instance_key")
            return Ok(
                MessageResponseDTO(
                    success=False,
                    error=f"Restaurant not found for instance_key: {dto.instance_key}",
                )
            )

        log = log.bind(restaurant_id=str(restaurant.id.value), restaurant_name=restaurant.name)

        phone = PhoneNumber(dto.clean_phone)
        conversation_result = await self._conversation_repo.find_by_restaurant_and_phone(
            restaurant.id, phone
        )

        if isinstance(conversation_result, Failure):
            return conversation_result

        conversation = conversation_result.value

        if conversation is None:
            conversation = Conversation.create(
                restaurant_id=restaurant.id,
                customer_phone=phone,
                customer_name=dto.push_name,
            )
            save_result = await self._conversation_repo.save(conversation)
            if isinstance(save_result, Failure):
                return save_result
            log.info("Created new conversation")

        source = MessageSource(dto.source)

        if source.is_human_intervention:
            conversation.handle_human_intervention()
            await self._conversation_repo.save(conversation)
            log.info("AI disabled due to human intervention", source=dto.source)
            return Ok(
                MessageResponseDTO(
                    success=True,
                    response_sent=False,
                    ai_disabled=True,
                    ai_disabled_reason="Human intervention detected",
                )
            )

        incoming_message = Message.create_incoming(
            conversation_id=conversation.id,
            body=dto.body,
            source=source,
            timestamp=dto.timestamp_datetime,
            external_id=dto.message_id,
        )

        save_msg_result = await self._message_repo.save(incoming_message)
        if isinstance(save_msg_result, Failure):
            return save_msg_result

        conversation.record_message(dto.timestamp_datetime)
        await self._conversation_repo.save(conversation)

        _was_ai_disabled = not conversation.is_ai_active

        if not conversation.can_ai_respond():
            log.info("AI is disabled for this conversation")
            return Ok(
                MessageResponseDTO(
                    success=True,
                    message_id=str(incoming_message.id.value),
                    response_sent=False,
                    ai_disabled=True,
                    ai_disabled_reason=conversation.ai_disabled_reason or "disabled",
                )
            )

        # If can_ai_respond() auto-enabled AI (expired disable period), persist it
        if _was_ai_disabled and conversation.is_ai_active:
            await self._conversation_repo.save(conversation)
            log.info("AI auto-enabled after expired disable period")

        _settings = get_settings()
        recent_messages_result = await self._message_repo.find_recent_by_conversation(
            conversation.id, limit=_settings.app.conversation_history_limit
        )

        if isinstance(recent_messages_result, Failure):
            return recent_messages_result

        recent_messages = recent_messages_result.value

        conversation_history = [
            {"role": "user" if m.direction.is_incoming else "assistant", "content": m.body}
            for m in recent_messages
        ]

        # Semantic search — embed customer message and find relevant menu items
        # Level 2 (ADVANCED) uses enhanced RAG with prices
        rag_context = ""
        tacto_address = ""
        tacto_hours = ""

        is_level2 = restaurant.automation_type.can_collect_orders

        if is_level2 and self._vector_store and self._embedding_client and self._menu_provider:
            # Level 2: Use pgvector semantic search + REAL prices from Tacto API
            # This guarantees we NEVER invent items or prices
            try:
                embed_result = await self._embedding_client.generate_embedding(dto.body)
                if isinstance(embed_result, Success):
                    # Step 1: Semantic search via pgvector (same as Level 1)
                    search_result = await self._vector_store.search_menu(
                        restaurant.id.value,
                        embed_result.value,
                        limit=_settings.gemini.level2_rag_search_limit,
                    )
                    if isinstance(search_result, Success) and search_result.value:
                        # Step 2: Enrich with REAL prices from Tacto API
                        enriched = await self._menu_provider.enrich_pgvector_results_with_prices(
                            restaurant.id,
                            search_result.value,
                            empresa_base_id=restaurant.empresa_base_id,
                            grupo_empresarial=str(restaurant.chave_grupo_empresarial),
                        )
                        if isinstance(enriched, Success) and enriched.value:
                            rag_context = self._menu_provider.build_rag_context_with_prices(enriched.value)
                            log.debug(
                                "rag_level2_pgvector_with_prices",
                                pgvector_hits=len(search_result.value),
                                enriched_hits=len(enriched.value),
                            )
                        else:
                            # Fallback: use pgvector results without prices
                            rag_context = self._build_rag_context(search_result.value)
                            log.warning("rag_level2_price_enrichment_failed_using_pgvector_only")
            except Exception as exc:
                log.warning("rag_level2_search_failed", error=str(exc))

        elif self._vector_store and self._embedding_client:
            # Level 1: Use pgvector semantic search (no prices)
            try:
                embed_result = await self._embedding_client.generate_embedding(dto.body)
                if isinstance(embed_result, Success):
                    search_result = await self._vector_store.search_menu(
                        restaurant.id.value, embed_result.value, limit=_settings.gemini.level1_rag_search_limit
                    )
                    if isinstance(search_result, Success) and search_result.value:
                        rag_context = self._build_rag_context(search_result.value)
                        log.debug("rag_semantic_search", hits=len(search_result.value))
            except Exception as exc:
                log.warning("rag_search_failed", error=str(exc))

        # Load address + hours from Tacto (cached in Redis 1h)
        if self._menu_provider:
            try:
                menu_result = await self._menu_provider.get_menu(
                    restaurant.id,
                    empresa_base_id=restaurant.empresa_base_id,
                    grupo_empresarial=str(restaurant.chave_grupo_empresarial),
                )
                if isinstance(menu_result, Success):
                    tacto_address = menu_result.value.address or ""
                    tacto_hours = menu_result.value.hours_text or ""
            except Exception as exc:
                log.warning("tacto_meta_fetch_failed", error=str(exc))

        # Calculate if restaurant is open and next opening time
        # BYPASS_HOURS_CHECK=true forces open state — useful for local testing
        is_open = True if _settings.app.bypass_hours_check else restaurant.is_open_now()
        next_opening_text = restaurant.opening_hours.get_next_opening(restaurant.timezone)

        persona = restaurant.agent_config
        agent_context = AgentContext(
            restaurant_id=restaurant.id.value,
            restaurant_name=restaurant.name,
            customer_phone=dto.clean_phone,
            customer_name=dto.push_name or conversation.customer_name,
            conversation_id=conversation.id.value,
            menu_url=restaurant.menu_url,
            prompt_default=restaurant.prompt_default,
            opening_hours=restaurant.opening_hours.to_dict(),
            automation_level=restaurant.automation_type,
            is_open=is_open,
            next_opening_text=next_opening_text,
            rag_context=rag_context,
            tacto_address=tacto_address,
            tacto_hours=tacto_hours,
            attendant_name=persona.effective_attendant_name(_settings.app.attendant_name),
            attendant_gender=persona.effective_gender(_settings.app.attendant_gender),
            persona_style=persona.effective_persona_style(_settings.app.attendant_persona_style),
            max_emojis_per_message=persona.effective_max_emojis(_settings.app.attendant_max_emojis),
        )

        selected_agent = self._select_agent(restaurant.automation_type)
        if selected_agent is None:
            log.error("No AI agent available")
            return Ok(
                MessageResponseDTO(
                    success=True,
                    message_id=str(incoming_message.id.value),
                    response_sent=False,
                    error="No AI agent configured",
                )
            )

        log.debug(
            "Selected agent",
            automation_type=restaurant.automation_type.name,
            agent_level=selected_agent.level,
        )

        response_result = await selected_agent.process(
            message=dto.body,
            context=agent_context,
            conversation_history=conversation_history,
        )

        if isinstance(response_result, Failure):
            log.error("Failed to generate AI response", error=str(response_result.error))
            return Ok(
                MessageResponseDTO(
                    success=True,
                    message_id=str(incoming_message.id.value),
                    response_sent=False,
                    error=f"AI generation failed: {response_result.error}",
                )
            )

        agent_response = response_result.value

        if not agent_response.should_send:
            log.info("AI decided not to respond")
            return Ok(
                MessageResponseDTO(
                    success=True,
                    message_id=str(incoming_message.id.value),
                    response_sent=False,
                )
            )

        response_text = agent_response.message

        _disable_hours = get_settings().app.ai_disable_hours
        if "human_handoff" in agent_response.triggered_actions:
            log.info("human_handoff_requested", customer_phone=dto.clean_phone)
            # Customer asked for a human — disable AI so the attendant can take over.
            conversation.disable_ai(reason="customer_requested_human_handoff", duration_hours=_disable_hours)
            await self._conversation_repo.save(conversation)

        # Level 2 handoff: Customer confirmed order, need human to finalize (delivery fee + confirm)
        if "handoff_to_human" in agent_response.triggered_actions:
            log.info(
                "level2_order_confirmed_handoff",
                customer_phone=dto.clean_phone,
                reason="order_confirmed_awaiting_human",
            )
            conversation.disable_ai(reason="order_confirmed_awaiting_human", duration_hours=_disable_hours)
            await self._conversation_repo.save(conversation)

        if "restaurant_closed" in agent_response.triggered_actions:
            log.info("restaurant_closed_disabled_ai", customer_phone=dto.clean_phone)
            # Restaurant is closed — disable AI until buffer_minutes before next opening.
            # Multi-tenant: each restaurant has its own timezone and opening schedule.
            conversation.disable_ai_until_opening(
                opening_hours=restaurant.opening_hours,
                tz=restaurant.timezone,
                buffer_minutes=_settings.app.ai_reopen_buffer_minutes,
                fallback_hours=_disable_hours,
            )
            await self._conversation_repo.save(conversation)

        # --- RACE CONDITION MITIGATION ---
        # Re-fetch conversation to check if a human intervened during the AI generation time.
        refresh_result = await self._conversation_repo.find_by_restaurant_and_phone(
            restaurant.id, phone
        )
        if isinstance(refresh_result, Success) and refresh_result.value:
            refreshed_conv = refresh_result.value
            if not refreshed_conv.can_ai_respond():
                log.info("human_intervened_during_generation_aborting_send", customer_phone=dto.clean_phone)
                return Ok(
                    MessageResponseDTO(
                        success=True,
                        message_id=str(incoming_message.id.value),
                        response_sent=False,
                        ai_disabled=True,
                        ai_disabled_reason="Human intervened during generation",
                    )
                )

        send_result = await self._messaging_client.send_message(
            instance_key=dto.instance_key,
            phone=dto.clean_phone,
            message=response_text,
            simulate_typing=True,
        )

        if isinstance(send_result, Failure):
            log.error("Failed to send WhatsApp message", error=str(send_result.error))
            return Ok(
                MessageResponseDTO(
                    success=True,
                    message_id=str(incoming_message.id.value),
                    response_sent=False,
                    response_text=response_text,
                    error=f"Failed to send message: {send_result.error}",
                )
            )

        outgoing_message = Message.create_outgoing(
            conversation_id=conversation.id,
            body=response_text,
            source=MessageSource.AI,
        )

        await self._message_repo.save(outgoing_message)

        # --- CUSTOMER STYLE ANALYSIS ---
        # Analyze communication style on first interaction and save to long-term memory.
        # Runs after successful send so it never blocks the response.
        if self._memory_manager:
            await self._analyze_and_save_customer_style(
                restaurant_id=restaurant.id.value,
                customer_phone=dto.clean_phone,
                customer_message=dto.body,
                conversation_history=conversation_history,
            )

        log.info("Successfully processed message and sent response")

        return Ok(
            MessageResponseDTO(
                success=True,
                message_id=str(incoming_message.id.value),
                response_sent=True,
                response_text=response_text,
            )
        )

    async def _analyze_and_save_customer_style(
        self,
        restaurant_id,
        customer_phone: str,
        customer_message: str,
        conversation_history: list[dict],
    ) -> None:
        """
        Detect customer communication style and persist to long-term memory.

        Only saves once per customer (checks for existing style entry).
        Updates the profile after every 10 messages to capture style evolution.
        """
        _STYLE_KEY = "style:communication"
        _UPDATE_INTERVAL = 10

        try:
            existing = await self._memory_manager.load_context(
                restaurant_id, customer_phone
            )

            if isinstance(existing, Success):
                style_entries = [
                    e for e in existing.value.long_term
                    if e.key == f"pref:{_STYLE_KEY}"
                ]

                # Count customer messages in current history
                user_msg_count = sum(
                    1 for m in conversation_history if m.get("role") == "user"
                )

                if style_entries and user_msg_count % _UPDATE_INTERVAL != 0:
                    return

            # Collect all customer messages from conversation history
            customer_messages = [
                m["content"] for m in conversation_history
                if m.get("role") == "user" and m.get("content")
            ]
            if not customer_messages:
                customer_messages = [customer_message]

            profile = CustomerStyleAnalyzer.analyze(customer_messages)
            style_text = profile.to_memory_text()

            await self._memory_manager.upsert_preference(
                restaurant_id=restaurant_id,
                customer_phone=customer_phone,
                preference=style_text,
                category=_STYLE_KEY,
            )

            logger.debug(
                "customer_style_saved",
                phone=customer_phone,
                style=style_text,
            )

        except Exception as exc:
            logger.warning(
                "customer_style_analysis_failed",
                error=str(exc),
                phone=customer_phone,
            )

    def _select_agent(self, automation_type: AutomationType) -> Optional[BaseAgent]:
        """
        Select the appropriate AI agent based on automation type.

        Priority:
        1. AgentFactory (supports multiple automation levels)
        2. Fallback to single ai_agent (backward compatibility)

        Args:
            automation_type: Restaurant's automation level

        Returns:
            Selected agent or None if none available
        """
        if self._agent_factory and self._agent_factory.is_initialized:
            return self._agent_factory.get_agent(automation_type)

        return self._ai_agent

    @staticmethod
    def _build_rag_context(hits: list[dict]) -> str:
        """Build AI context string from semantic search hits — NO prices."""
        lines = ["Itens do cardápio relacionados à pergunta do cliente:"]
        for hit in hits:
            content = hit.get("content", "").strip()
            if content:
                lines.append(f"• {content}")
        return "\n".join(lines)
