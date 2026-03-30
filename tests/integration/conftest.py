"""
Integration Test Fixtures.

Provides fixtures for integration tests with real PostgreSQL database.
Uses transaction rollback strategy for test isolation.

Requirements:
- PostgreSQL must be running and accessible
- Database must exist with schema migrated
- Run with: pytest tests/integration/ -v
"""

import asyncio
from typing import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from tacto.config.settings import get_settings
from tacto.infrastructure.database.models.base import Base
from tacto.infrastructure.database.models.restaurant import RestaurantModel
from tacto.infrastructure.database.models.conversation import ConversationModel
from tacto.infrastructure.database.models.message import MessageModel


# ──────────────────────────────────────────────────────────────────────────────
# Database Connection Check
# ──────────────────────────────────────────────────────────────────────────────

_db_available = None


def _check_db_connection() -> bool:
    """Check if database is available (cached)."""
    global _db_available
    if _db_available is not None:
        return _db_available

    import asyncio
    from sqlalchemy.ext.asyncio import create_async_engine

    async def _test_connection():
        try:
            settings = get_settings()
            engine = create_async_engine(settings.database.async_url, pool_pre_ping=True)
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            await engine.dispose()
            return True
        except Exception:
            return False

    _db_available = asyncio.get_event_loop().run_until_complete(_test_connection())
    return _db_available


# Skip all integration tests if database not available
pytestmark = pytest.mark.skipif(
    not _check_db_connection(),
    reason="PostgreSQL database not available"
)


# ──────────────────────────────────────────────────────────────────────────────
# Database Engine & Session Fixtures
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def event_loop():
    """Create event loop for async tests."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="module")
async def test_engine():
    """Create test database engine."""
    settings = get_settings()
    engine = create_async_engine(
        settings.database.async_url,
        echo=False,
        pool_pre_ping=True,
    )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Create database session with transaction rollback for test isolation.
    
    Each test runs in a transaction that is rolled back at the end,
    ensuring tests don't affect each other or persist data.
    """
    async with test_engine.connect() as connection:
        transaction = await connection.begin()
        
        session_factory = async_sessionmaker(
            bind=connection,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        session = session_factory()
        
        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()


# ──────────────────────────────────────────────────────────────────────────────
# Test Data Fixtures
# ──────────────────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def sample_restaurant(db_session: AsyncSession) -> RestaurantModel:
    """Create a sample restaurant for testing."""
    restaurant = RestaurantModel(
        id=uuid4(),
        name="Restaurante Teste Integração",
        prompt_default="Você é a atendente virtual do Restaurante Teste.",
        menu_url="https://cardapio.teste.com",
        opening_hours={
            "monday": {"opens_at": "11:00", "closes_at": "23:00"},
            "tuesday": {"opens_at": "11:00", "closes_at": "23:00"},
            "wednesday": {"opens_at": "11:00", "closes_at": "23:00"},
            "thursday": {"opens_at": "11:00", "closes_at": "23:00"},
            "friday": {"opens_at": "11:00", "closes_at": "23:00"},
            "saturday": {"opens_at": "11:00", "closes_at": "23:00"},
            "sunday": {"is_closed": True},
        },
        integration_type=2,  # JOIN
        automation_type=1,   # BASIC
        chave_grupo_empresarial=uuid4(),
        canal_master_id="restaurante_teste_integracao",
        empresa_base_id="1",
        timezone="America/Sao_Paulo",
        is_active=True,
    )
    db_session.add(restaurant)
    await db_session.flush()
    return restaurant


@pytest_asyncio.fixture
async def sample_conversation(
    db_session: AsyncSession,
    sample_restaurant: RestaurantModel,
) -> ConversationModel:
    """Create a sample conversation for testing."""
    conversation = ConversationModel(
        id=uuid4(),
        restaurant_id=sample_restaurant.id,
        customer_phone="5565992540370",
        customer_name="Cliente Teste",
        is_ai_active=True,
    )
    db_session.add(conversation)
    await db_session.flush()
    return conversation


@pytest_asyncio.fixture
async def sample_messages(
    db_session: AsyncSession,
    sample_conversation: ConversationModel,
) -> list[MessageModel]:
    """Create sample messages for testing."""
    messages = [
        MessageModel(
            id=uuid4(),
            conversation_id=sample_conversation.id,
            role="user",
            content="Olá, vocês estão abertos?",
            external_id="MSG_001",
        ),
        MessageModel(
            id=uuid4(),
            conversation_id=sample_conversation.id,
            role="assistant",
            content="Oi! Sim, estamos abertos até às 23h.",
            external_id="MSG_002",
        ),
        MessageModel(
            id=uuid4(),
            conversation_id=sample_conversation.id,
            role="user",
            content="Quero ver o cardápio",
            external_id="MSG_003",
        ),
    ]
    for msg in messages:
        db_session.add(msg)
    await db_session.flush()
    return messages


