"""
FastAPI Dependencies for HTTP Routes.

Provides dependency injection for use cases and repositories.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from tacto.application.use_cases.create_restaurant import CreateRestaurantUseCase
from tacto.application.use_cases.process_incoming_message import (
    ProcessIncomingMessageUseCase,
)
from tacto.infrastructure.database.connection import get_async_session
from tacto.infrastructure.external.tacto_client import TactoClient
from tacto.infrastructure.external.tacto_menu_provider import TactoMenuProvider
from tacto.infrastructure.messaging.join_client import JoinClient
from tacto.infrastructure.messaging.sent_message_tracker import SentMessageTracker
from tacto.infrastructure.redis.redis_client import RedisClient
from tacto.infrastructure.persistence.conversation_repository import (
    PostgresConversationRepository,
)
from tacto.infrastructure.persistence.message_repository import (
    PostgresMessageRepository,
)
from tacto.infrastructure.persistence.restaurant_repository import (
    PostgresRestaurantRepository,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session dependency."""
    async with get_async_session() as session:
        yield session


async def get_create_restaurant_use_case() -> AsyncGenerator[CreateRestaurantUseCase, None]:
    """
    Get CreateRestaurantUseCase with a live session.

    Uses yield (generator) so FastAPI keeps the session open during
    the entire request and commits/rolls back AFTER the endpoint returns.
    """
    async with get_async_session() as session:
        repository = PostgresRestaurantRepository(session)
        yield CreateRestaurantUseCase(repository)


async def create_and_execute_process_message(
    dto,
    redis_client: RedisClient | None = None,
    tacto_client: TactoClient | None = None,
) -> None:
    """Create and execute ProcessIncomingMessageUseCase with proper session lifecycle."""
    import structlog
    from tacto.infrastructure.agents.agent_factory import create_agent
    from tacto.infrastructure.ai.gemini_client import GeminiClient
    from tacto.infrastructure.database.pgvector_store import PgvectorStore
    from tacto.application.services.order_state_service import OrderStateService
    from tacto.infrastructure.redis.order_state_adapter import RedisOrderStateAdapter

    logger = structlog.get_logger()

    if tacto_client is None:
        tacto_client = TactoClient()
    menu_provider = TactoMenuProvider(
        tacto_client=tacto_client,
        redis_client=redis_client,
    )

    messaging_client = JoinClient(message_tracker=SentMessageTracker(redis_client))
    embedding_client = GeminiClient()

    async with get_async_session() as session:
        from tacto.infrastructure.ai.redis_memory import RedisMemoryAdapter
        from tacto.infrastructure.ai.postgres_memory import PostgresMemoryAdapter
        from tacto.application.services.memory_orchestration_service import MemoryOrchestrationService

        # Resolve the restaurant first to select the correct agent by automation_type
        restaurant_repo_tmp = PostgresRestaurantRepository(session)
        restaurant_result = await restaurant_repo_tmp.find_by_canal_master_id(dto.instance_key)
        automation_type = 1  # fallback BASIC
        if not restaurant_result.is_failure() and restaurant_result.value is not None:
            automation_type = int(restaurant_result.value.automation_type)

        # Wire 3-level memory (short/medium → Redis, long-term → PostgreSQL)
        memory_manager = None
        order_service = None

        if redis_client is not None:
            memory_manager = MemoryOrchestrationService(
                short_term_port=RedisMemoryAdapter(redis_client),
                long_term_port=PostgresMemoryAdapter(session),
            )

            # Order service for Level 2 (ADVANCED automation)
            order_state_adapter = RedisOrderStateAdapter(redis_client)
            order_service = OrderStateService(order_state_adapter)

        use_case = ProcessIncomingMessageUseCase(
            restaurant_repository=PostgresRestaurantRepository(session),
            conversation_repository=PostgresConversationRepository(session),
            message_repository=PostgresMessageRepository(session),
            messaging_client=messaging_client,
            ai_agent=create_agent(
                automation_type,
                memory_manager=memory_manager,
                order_service=order_service,
            ),
            menu_provider=menu_provider,
            vector_store=PgvectorStore(session),
            embedding_client=embedding_client,
        )

        result = await use_case.execute(dto)

        if result.is_failure():
            logger.error("background_processing_failed", error=str(result.error), phone=dto.clean_phone)
        else:
            val = result.value
            logger.info(
                "background_processing_done",
                phone=dto.clean_phone,
                response_sent=val.response_sent,
                ai_disabled=val.ai_disabled,
            )
