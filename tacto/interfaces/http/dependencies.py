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
) -> None:
    """Create and execute ProcessIncomingMessageUseCase with proper session lifecycle."""
    import structlog
    from tacto.domain.ai.agents.level1_agent import Level1Agent
    from tacto.infrastructure.ai.gemini_client import GeminiClient
    from tacto.infrastructure.vector_store.pgvector_store import PgvectorStore

    logger = structlog.get_logger()

    tacto_client = TactoClient()
    menu_provider = TactoMenuProvider(
        tacto_client=tacto_client,
        redis_client=redis_client,
    )

    messaging_client = JoinClient(message_tracker=SentMessageTracker(redis_client))
    embedding_client = GeminiClient()

    async with get_async_session() as session:
        use_case = ProcessIncomingMessageUseCase(
            restaurant_repository=PostgresRestaurantRepository(session),
            conversation_repository=PostgresConversationRepository(session),
            message_repository=PostgresMessageRepository(session),
            messaging_client=messaging_client,
            ai_agent=Level1Agent(),
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
