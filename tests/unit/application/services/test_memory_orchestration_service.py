"""Tests for MemoryOrchestrationService — focus on the new clear_all_context."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from tacto.application.services.memory_orchestration_service import (
    MemoryOrchestrationService,
)
from tacto.domain.customer_memory.value_objects.memory_entry import MemoryType
from tacto.shared.application import Failure, Success


@pytest.fixture
def short_term_port() -> MagicMock:
    port = MagicMock()
    port.clear = AsyncMock(return_value=Success(True))
    return port


@pytest.fixture
def long_term_port() -> MagicMock:
    port = MagicMock()
    port.clear = AsyncMock(return_value=Success(True))
    return port


@pytest.fixture
def service(short_term_port, long_term_port) -> MemoryOrchestrationService:
    return MemoryOrchestrationService(
        short_term_port=short_term_port,
        long_term_port=long_term_port,
    )


class TestClearAllContext:
    @pytest.mark.asyncio
    async def test_clears_short_medium_and_long_term(
        self, service, short_term_port, long_term_port
    ):
        """clear_all_context must clear all three memory tiers."""
        restaurant_id = uuid4()
        phone = "5565999999999"

        result = await service.clear_all_context(restaurant_id, phone)

        assert isinstance(result, Success)
        # Short-term port handles both SHORT_TERM and MEDIUM_TERM
        assert short_term_port.clear.await_count == 2
        # Long-term port called exactly once
        long_term_port.clear.assert_awaited_once_with(
            restaurant_id, phone, MemoryType.LONG_TERM
        )

    @pytest.mark.asyncio
    async def test_returns_failure_when_long_term_fails(
        self, service, long_term_port
    ):
        """If long-term clear fails, the whole operation must surface the failure."""
        long_term_port.clear = AsyncMock(return_value=Failure(RuntimeError("db down")))

        result = await service.clear_all_context(uuid4(), "5565000000000")

        assert isinstance(result, Failure)

    @pytest.mark.asyncio
    async def test_returns_failure_when_short_term_fails(
        self, service, short_term_port
    ):
        """If short-term clear fails, must short-circuit and not touch long-term."""
        short_term_port.clear = AsyncMock(return_value=Failure(RuntimeError("redis down")))

        result = await service.clear_all_context(uuid4(), "5565000000000")

        assert isinstance(result, Failure)


class TestClearSessionContextStillWorks:
    """Ensure the original method is preserved — used elsewhere."""

    @pytest.mark.asyncio
    async def test_clears_only_short_and_medium(
        self, service, short_term_port, long_term_port
    ):
        result = await service.clear_session_context(uuid4(), "5565000000000")

        assert isinstance(result, Success)
        assert short_term_port.clear.await_count == 2
        long_term_port.clear.assert_not_called()
