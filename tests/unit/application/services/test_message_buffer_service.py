"""
Tests for MessageBufferService.

Tests the intelligent message buffering strategy:
1. Message buffering with Redis
2. Burst message combination
3. Fallback to immediate processing without Redis
4. Lock acquisition and release
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tacto.application.services.message_buffer_service import MessageBufferService


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_redis_client() -> MagicMock:
    """Create a mock Redis client."""
    client = MagicMock()
    client.is_connected = True
    client.rpush = AsyncMock(return_value=MagicMock(is_success=lambda: True, value=1))
    client.expire = AsyncMock(return_value=MagicMock(is_success=lambda: True))
    client.lrange = AsyncMock(return_value=MagicMock(is_success=lambda: True, value=[]))
    client.set = AsyncMock(return_value=MagicMock(is_success=lambda: True, value=True))
    client.delete = AsyncMock(return_value=MagicMock(is_success=lambda: True))
    return client


@pytest.fixture
def disconnected_redis_client() -> MagicMock:
    """Create a disconnected Redis client."""
    client = MagicMock()
    client.is_connected = False
    return client


@pytest.fixture
def mock_process_callback() -> AsyncMock:
    """Create a mock process callback."""
    return AsyncMock()


# ──────────────────────────────────────────────────────────────────────────────
# Test Classes
# ──────────────────────────────────────────────────────────────────────────────

class TestMessageBufferServiceFallback:
    """Test fallback behavior when Redis is unavailable."""

    @pytest.mark.asyncio
    async def test_processes_immediately_without_redis(
        self,
        mock_process_callback,
    ):
        """When Redis is None, message should be processed immediately."""
        service = MessageBufferService(redis_client=None)

        with patch.object(service, '_window_seconds', 0.1):
            await service.buffer_and_process(
                instance_key="restaurante_teste",
                phone="5565992540370",
                text="Olá",
                timestamp=1234567890,
                message_id="MSG_123",
                push_name="Cliente",
                process_callback=mock_process_callback,
            )

        mock_process_callback.assert_called_once()
        dto = mock_process_callback.call_args[0][0]
        assert dto.body == "Olá"
        assert dto.instance_key == "restaurante_teste"
        assert dto.clean_phone == "5565992540370"

    @pytest.mark.asyncio
    async def test_processes_immediately_when_redis_disconnected(
        self,
        disconnected_redis_client,
        mock_process_callback,
    ):
        """When Redis is disconnected, message should be processed immediately."""
        service = MessageBufferService(redis_client=disconnected_redis_client)

        with patch.object(service, '_window_seconds', 0.1):
            await service.buffer_and_process(
                instance_key="restaurante_teste",
                phone="5565992540370",
                text="Olá",
                timestamp=1234567890,
                message_id="MSG_123",
                push_name="Cliente",
                process_callback=mock_process_callback,
            )

        mock_process_callback.assert_called_once()


class TestMessageBufferServiceRedis:
    """Test buffering behavior with Redis."""

    @pytest.mark.asyncio
    async def test_buffers_message_to_redis(
        self,
        mock_redis_client,
        mock_process_callback,
    ):
        """Message should be buffered to Redis list."""
        service = MessageBufferService(redis_client=mock_redis_client)

        # Configure to return 1 message after wait
        msg_data = json.dumps({
            "text": "Olá",
            "timestamp": 1234567890,
            "message_id": "MSG_123",
            "push_name": "Cliente",
        })
        mock_redis_client.lrange = AsyncMock(
            return_value=MagicMock(is_success=lambda: True, value=[msg_data])
        )

        with patch.object(service, '_window_seconds', 0.01):
            with patch.object(service, '_lock_ttl', 5):
                await service.buffer_and_process(
                    instance_key="restaurante_teste",
                    phone="5565992540370",
                    text="Olá",
                    timestamp=1234567890,
                    message_id="MSG_123",
                    push_name="Cliente",
                    process_callback=mock_process_callback,
                )

        # Message should be pushed to Redis
        mock_redis_client.rpush.assert_called_once()
        # Process callback should be called
        mock_process_callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_processing_when_newer_messages_exist(
        self,
        mock_redis_client,
        mock_process_callback,
    ):
        """Should skip processing if newer messages arrived in buffer."""
        service = MessageBufferService(redis_client=mock_redis_client)

        # First message gets position 1
        mock_redis_client.rpush = AsyncMock(
            return_value=MagicMock(is_success=lambda: True, value=1)
        )
        # But buffer now has 2 messages (newer one arrived)
        mock_redis_client.lrange = AsyncMock(
            return_value=MagicMock(is_success=lambda: True, value=["msg1", "msg2"])
        )

        with patch.object(service, '_window_seconds', 0.01):
            await service.buffer_and_process(
                instance_key="restaurante_teste",
                phone="5565992540370",
                text="Primeira mensagem",
                timestamp=1234567890,
                message_id="MSG_1",
                push_name="Cliente",
                process_callback=mock_process_callback,
            )

        # Process callback should NOT be called (newer messages exist)
        mock_process_callback.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_processing_when_lock_not_acquired(
        self,
        mock_redis_client,
        mock_process_callback,
    ):
        """Should skip processing if lock cannot be acquired."""
        service = MessageBufferService(redis_client=mock_redis_client)

        msg_data = json.dumps({
            "text": "Olá",
            "timestamp": 1234567890,
            "message_id": "MSG_123",
            "push_name": "Cliente",
        })
        mock_redis_client.lrange = AsyncMock(
            return_value=MagicMock(is_success=lambda: True, value=[msg_data])
        )
        # Lock acquisition fails
        mock_redis_client.set = AsyncMock(
            return_value=MagicMock(is_success=lambda: True, value=False)
        )

        with patch.object(service, '_window_seconds', 0.01):
            await service.buffer_and_process(
                instance_key="restaurante_teste",
                phone="5565992540370",
                text="Olá",
                timestamp=1234567890,
                message_id="MSG_123",
                push_name="Cliente",
                process_callback=mock_process_callback,
            )

        # Process callback should NOT be called (lock not acquired)
        mock_process_callback.assert_not_called()


class TestMessageBufferServiceCombineMessages:
    """Test message combination logic."""

    def test_combines_multiple_messages(self):
        """Multiple messages should be combined with space separator."""
        messages = [
            json.dumps({"text": "Olá", "timestamp": 100, "push_name": "Cliente"}),
            json.dumps({"text": "Quero fazer um pedido", "timestamp": 101, "push_name": "Cliente"}),
            json.dumps({"text": "Por favor", "timestamp": 102, "push_name": "Cliente"}),
        ]

        combined, timestamp, push_name = MessageBufferService._combine_messages(
            messages, fallback_timestamp=99, fallback_push_name="Fallback"
        )

        assert combined == "Olá Quero fazer um pedido Por favor"
        assert timestamp == 102  # Latest timestamp
        assert push_name == "Cliente"

    def test_handles_single_message(self):
        """Single message should not be modified."""
        messages = [
            json.dumps({"text": "Olá", "timestamp": 100, "push_name": "Cliente"}),
        ]

        combined, timestamp, push_name = MessageBufferService._combine_messages(
            messages, fallback_timestamp=99, fallback_push_name="Fallback"
        )

        assert combined == "Olá"
        assert timestamp == 100

    def test_handles_empty_buffer(self):
        """Empty buffer should return empty string."""
        combined, timestamp, push_name = MessageBufferService._combine_messages(
            [], fallback_timestamp=99, fallback_push_name="Fallback"
        )

        assert combined == ""
        assert timestamp == 99
        assert push_name == "Fallback"

    def test_handles_invalid_json(self):
        """Invalid JSON in buffer should be skipped."""
        messages = [
            json.dumps({"text": "Válido", "timestamp": 100, "push_name": "Cliente"}),
            "invalid json",
            json.dumps({"text": "Também válido", "timestamp": 102, "push_name": "Cliente"}),
        ]

        combined, timestamp, push_name = MessageBufferService._combine_messages(
            messages, fallback_timestamp=99, fallback_push_name="Fallback"
        )

        assert combined == "Válido Também válido"
        assert timestamp == 102


class TestMessageBufferServiceBurstHandling:
    """Test burst message handling scenarios."""

    @pytest.mark.asyncio
    async def test_burst_messages_combined(
        self,
        mock_redis_client,
        mock_process_callback,
    ):
        """Multiple rapid messages should be combined into one."""
        service = MessageBufferService(redis_client=mock_redis_client)

        # Simulate 3 messages in buffer
        messages = [
            json.dumps({"text": "Oi", "timestamp": 100, "message_id": "1", "push_name": "Cliente"}),
            json.dumps({"text": "Quero pizza", "timestamp": 101, "message_id": "2", "push_name": "Cliente"}),
            json.dumps({"text": "Margherita", "timestamp": 102, "message_id": "3", "push_name": "Cliente"}),
        ]

        # Third message gets position 3
        mock_redis_client.rpush = AsyncMock(
            return_value=MagicMock(is_success=lambda: True, value=3)
        )
        # Buffer has all 3 messages
        mock_redis_client.lrange = AsyncMock(
            return_value=MagicMock(is_success=lambda: True, value=messages)
        )

        with patch.object(service, '_window_seconds', 0.01):
            with patch.object(service, '_lock_ttl', 5):
                await service.buffer_and_process(
                    instance_key="restaurante_teste",
                    phone="5565992540370",
                    text="Margherita",
                    timestamp=102,
                    message_id="3",
                    push_name="Cliente",
                    process_callback=mock_process_callback,
                )

        # Process callback should be called with combined message
        mock_process_callback.assert_called_once()
        dto = mock_process_callback.call_args[0][0]
        assert dto.body == "Oi Quero pizza Margherita"

    @pytest.mark.asyncio
    async def test_lock_released_on_callback_exception(
        self,
        mock_redis_client,
    ):
        """Lock should be released even if callback raises exception."""
        service = MessageBufferService(redis_client=mock_redis_client)

        failing_callback = AsyncMock(side_effect=Exception("Callback failed"))

        msg_data = json.dumps({
            "text": "Olá",
            "timestamp": 1234567890,
            "message_id": "MSG_123",
            "push_name": "Cliente",
        })
        mock_redis_client.lrange = AsyncMock(
            return_value=MagicMock(is_success=lambda: True, value=[msg_data])
        )

        with patch.object(service, '_window_seconds', 0.01):
            with patch.object(service, '_lock_ttl', 5):
                with pytest.raises(Exception, match="Callback failed"):
                    await service.buffer_and_process(
                        instance_key="restaurante_teste",
                        phone="5565992540370",
                        text="Olá",
                        timestamp=1234567890,
                        message_id="MSG_123",
                        push_name="Cliente",
                        process_callback=failing_callback,
                    )

        # Lock should be released (delete called)
        assert mock_redis_client.delete.call_count >= 1
