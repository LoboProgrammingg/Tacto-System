"""
Message Buffer Service.

Implements intelligent message buffering to group messages
sent within a short time window (< 5 seconds).

Business Rule: Buffer agrupa mensagens < 5s para evitar múltiplas respostas.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from tacto.domain.shared.result import Failure, Success


@dataclass
class BufferedMessage:
    """Represents a buffered message waiting to be processed."""

    conversation_key: str
    body: str
    timestamp: datetime
    instance_key: str
    from_phone: str
    source: str
    message_id: Optional[str] = None
    push_name: Optional[str] = None


@dataclass
class BufferResult:
    """Result of buffer operation."""

    should_process: bool
    combined_message: str
    messages: list[BufferedMessage] = field(default_factory=list)
    wait_time_ms: int = 0


class MessageBufferPort(ABC):
    """
    Port for message buffer storage.

    Implemented by Redis in infrastructure layer.
    """

    @abstractmethod
    async def add_to_buffer(
        self, key: str, message: BufferedMessage, ttl_seconds: int
    ) -> Success[bool] | Failure[Exception]:
        """Add message to buffer."""
        ...

    @abstractmethod
    async def get_buffer(
        self, key: str
    ) -> Success[list[BufferedMessage]] | Failure[Exception]:
        """Get all messages in buffer."""
        ...

    @abstractmethod
    async def clear_buffer(self, key: str) -> Success[bool] | Failure[Exception]:
        """Clear buffer for key."""
        ...

    @abstractmethod
    async def get_last_message_time(
        self, key: str
    ) -> Success[Optional[datetime]] | Failure[Exception]:
        """Get timestamp of last message in buffer."""
        ...


class MessageBufferService:
    """
    Domain service for intelligent message buffering.

    Groups messages sent within BUFFER_WINDOW_SECONDS to avoid
    sending multiple AI responses for rapid consecutive messages.

    Flow:
    1. Message arrives
    2. Check if there are recent messages in buffer (< 5s)
    3. If yes, add to buffer and wait
    4. If no recent messages, process immediately or start new buffer
    5. After BUFFER_WINDOW_SECONDS, combine all buffered messages
    """

    BUFFER_WINDOW_SECONDS = 5
    BUFFER_TTL_SECONDS = 30

    def __init__(self, buffer_port: MessageBufferPort) -> None:
        """
        Initialize buffer service.

        Args:
            buffer_port: Port for buffer storage (Redis)
        """
        self._buffer = buffer_port

    def _make_buffer_key(self, instance_key: str, phone: str) -> str:
        """Create unique buffer key for conversation."""
        return f"msg_buffer:{instance_key}:{phone}"

    async def should_buffer(
        self, message: BufferedMessage
    ) -> Success[bool] | Failure[Exception]:
        """
        Check if message should be buffered.

        Returns True if there are recent messages in the buffer
        that this message should be grouped with.
        """
        key = self._make_buffer_key(message.instance_key, message.from_phone)

        last_time_result = await self._buffer.get_last_message_time(key)

        if isinstance(last_time_result, Failure):
            return last_time_result

        last_time = last_time_result.value

        if last_time is None:
            return Success(False)

        elapsed = (message.timestamp - last_time).total_seconds()
        should_buffer = elapsed < self.BUFFER_WINDOW_SECONDS

        return Success(should_buffer)

    async def add_message(
        self, message: BufferedMessage
    ) -> Success[bool] | Failure[Exception]:
        """
        Add message to buffer.

        Args:
            message: Message to buffer

        Returns:
            Success with True if added, Failure on error
        """
        key = self._make_buffer_key(message.instance_key, message.from_phone)

        return await self._buffer.add_to_buffer(
            key, message, self.BUFFER_TTL_SECONDS
        )

    async def get_and_clear_buffer(
        self, instance_key: str, phone: str
    ) -> Success[BufferResult] | Failure[Exception]:
        """
        Get all buffered messages and clear the buffer.

        Combines multiple messages into a single message for processing.

        Args:
            instance_key: WhatsApp instance key
            phone: Customer phone number

        Returns:
            Success with BufferResult containing combined message
        """
        key = self._make_buffer_key(instance_key, phone)

        messages_result = await self._buffer.get_buffer(key)

        if isinstance(messages_result, Failure):
            return messages_result

        messages = messages_result.value

        if not messages:
            return Success(
                BufferResult(
                    should_process=False,
                    combined_message="",
                    messages=[],
                )
            )

        clear_result = await self._buffer.clear_buffer(key)

        if isinstance(clear_result, Failure):
            return clear_result

        if len(messages) == 1:
            combined = messages[0].body
        else:
            combined = "\n".join(m.body for m in messages)

        return Success(
            BufferResult(
                should_process=True,
                combined_message=combined,
                messages=messages,
            )
        )
