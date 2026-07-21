"""
Chat Test Route.

Allows testing the AI agent directly without going through WhatsApp.
Conversation state is persisted — the AI remembers context across calls
with the same customer_phone.
"""

import time
from datetime import datetime, timezone
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import structlog
from fastapi import APIRouter, HTTPException, status

from tacto.config import get_settings
from tacto.domain.ai_assistance.value_objects.agent_context import AgentContext
from tacto.domain.messaging.entities.conversation import Conversation
from tacto.domain.messaging.entities.message import Message
from tacto.domain.messaging.value_objects.message_source import MessageSource
from tacto.shared.application import Failure
from tacto.shared.domain.value_objects import PhoneNumber, RestaurantId
from tacto.infrastructure.agents.agent_factory import create_agent
from tacto.infrastructure.ai.redis_memory import RedisMemoryAdapter
from tacto.infrastructure.ai.postgres_memory import PostgresMemoryAdapter
from tacto.infrastructure.redis.redis_client import RedisClient
from tacto.application.services.memory_orchestration_service import MemoryOrchestrationService
from tacto.infrastructure.database.connection import get_async_session
from tacto.infrastructure.persistence.conversation_repository import (
    PostgresConversationRepository,
)
from tacto.infrastructure.persistence.message_repository import (
    PostgresMessageRepository,
)
from tacto.infrastructure.persistence.restaurant_repository import (
    PostgresRestaurantRepository,
)
from tacto.interfaces.http.schemas.chat import ChatMessage, ChatRequest, ChatResponse


logger = structlog.get_logger()
router = APIRouter()

_WEEKDAY_NAMES_PT = (
    "segunda-feira",
    "terça-feira",
    "quarta-feira",
    "quinta-feira",
    "sexta-feira",
    "sábado",
    "domingo",
)


def _get_restaurant_current_datetime(restaurant_timezone: str) -> datetime:
    """Return the current local datetime for the restaurant timezone."""
    settings = get_settings()
    timezone_name = restaurant_timezone or settings.app.default_timezone

    try:
        timezone_obj = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        logger.warning(
            "invalid_chat_route_timezone_falling_back_to_default",
            restaurant_timezone=restaurant_timezone,
            fallback_timezone=settings.app.default_timezone,
        )
        timezone_obj = ZoneInfo(settings.app.default_timezone)

    return datetime.now(timezone_obj)


def _build_agent_context(
    *,
    restaurant,
    conversation: Conversation,
    customer_phone: str,
    customer_name: str | None,
) -> AgentContext:
    """Build agent context with exact restaurant-local temporal data."""
    current_datetime = _get_restaurant_current_datetime(restaurant.timezone)
    settings = get_settings()
    is_open = (
        True
        if settings.app.bypass_hours_check or not restaurant.opening_hours.is_defined()
        else restaurant.is_open_now()
    )

    return AgentContext(
        restaurant_id=restaurant.id.value,
        restaurant_name=restaurant.name,
        customer_phone=customer_phone,
        customer_name=customer_name or conversation.customer_name,
        conversation_id=conversation.id.value,
        menu_url=restaurant.menu_url,
        prompt_default=restaurant.prompt_default,
        opening_hours=restaurant.opening_hours.to_dict(),
        automation_level=restaurant.automation_type.value,
        is_open=is_open,
        next_opening_text=restaurant.opening_hours.get_next_opening(restaurant.timezone),
        restaurant_timezone=str(current_datetime.tzinfo),
        current_datetime_iso=current_datetime.isoformat(),
        current_date_br=current_datetime.strftime("%d/%m/%Y"),
        current_time_br=current_datetime.strftime("%H:%M"),
        current_weekday_pt=_WEEKDAY_NAMES_PT[current_datetime.weekday()],
    )


@router.post(
    "/test",
    response_model=ChatResponse,
    summary="Test AI Chat",
    description=(
        "Send a message to the AI agent and get the response. "
        "No WhatsApp message is sent — purely for testing. "
        "Conversation context is persisted across calls with the same customer_phone."
    ),
)
async def chat_test(request: ChatRequest) -> ChatResponse:
    start = time.time()

    async with get_async_session() as session:
        restaurant_repo = PostgresRestaurantRepository(session)
        conversation_repo = PostgresConversationRepository(session)
        message_repo = PostgresMessageRepository(session)

        # 1. Resolve restaurant
        restaurant_result = await restaurant_repo.find_by_id(
            RestaurantId(request.restaurant_id)
        )
        if isinstance(restaurant_result, Failure) or restaurant_result.value is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Restaurant {request.restaurant_id} not found",
            )
        restaurant = restaurant_result.value

        if not restaurant.is_active:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Restaurant is inactive",
            )

        # 2. Find or create conversation
        phone = PhoneNumber(request.customer_phone)
        conv_result = await conversation_repo.find_by_restaurant_and_phone(
            restaurant.id, phone
        )
        if isinstance(conv_result, Failure):
            raise HTTPException(status_code=500, detail=str(conv_result.error))

        conversation = conv_result.value
        if conversation is None:
            conversation = Conversation.create(
                restaurant_id=restaurant.id,
                customer_phone=phone,
                customer_name=request.customer_name,
            )
            await conversation_repo.save(conversation)
            logger.info("New test conversation", conversation_id=str(conversation.id.value))

        # 3. Load history BEFORE storing new message (for AI context)
        history_result = await message_repo.find_recent_by_conversation(
            conversation.id, limit=20
        )
        if isinstance(history_result, Failure):
            raise HTTPException(status_code=500, detail=str(history_result.error))

        prior_messages = history_result.value
        conversation_history = [
            {
                "role": "user" if m.direction.is_incoming else "assistant",
                "content": m.body,
            }
            for m in prior_messages
        ]

        # 4. Store incoming message
        incoming = Message.create_incoming(
            conversation_id=conversation.id,
            body=request.message,
            source=MessageSource("app"),
            timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        await message_repo.save(incoming)
        conversation.record_message(datetime.now(timezone.utc).replace(tzinfo=None))
        await conversation_repo.save(conversation)

        # 5. Run AI agent — selected dynamically by restaurant.automation_type
        # Wire 3-level memory (short/medium → Redis, long-term → PostgreSQL)
        redis_client = RedisClient()
        memory_manager = MemoryOrchestrationService(
            short_term_port=RedisMemoryAdapter(redis_client),
            long_term_port=PostgresMemoryAdapter(session),
        )
        agent = create_agent(restaurant.automation_type, memory_manager=memory_manager)
        context = _build_agent_context(
            restaurant=restaurant,
            conversation=conversation,
            customer_phone=request.customer_phone,
            customer_name=request.customer_name,
        )

        agent_result = await agent.process(
            message=request.message,
            context=context,
            conversation_history=conversation_history,
        )

        if isinstance(agent_result, Failure):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"AI agent error: {agent_result.error}",
            )

        agent_response = agent_result.value

        # 6. Store outgoing message
        if agent_response.should_send:
            outgoing = Message.create_outgoing(
                conversation_id=conversation.id,
                body=agent_response.message,
                source=MessageSource.AI,
            )
            await message_repo.save(outgoing)

        processing_ms = int((time.time() - start) * 1000)

        # Build response history (prior + new exchange)
        history_out = [
            ChatMessage(
                role="user" if m.direction.is_incoming else "assistant",
                content=m.body,
            )
            for m in prior_messages[-9:]  # last 9 prior + the new pair = ~10
        ]
        history_out.append(ChatMessage(role="user", content=request.message))
        if agent_response.should_send:
            history_out.append(ChatMessage(role="assistant", content=agent_response.message))

        return ChatResponse(
            response=agent_response.message if agent_response.should_send else "(sem resposta)",
            restaurant_name=restaurant.name,
            conversation_id=str(conversation.id.value),
            processing_time_ms=processing_ms,
            history=history_out,
        )
