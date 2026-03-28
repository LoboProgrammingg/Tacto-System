"""
Message DTOs for Application Layer.

Data Transfer Objects for message-related operations.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


@dataclass(frozen=True, slots=True)
class IncomingMessageDTO:
    """
    DTO for incoming WhatsApp messages from Join webhook.

    Maps directly from Join webhook payload.
    """

    instance_key: str
    from_phone: str
    body: str
    from_me: bool
    source: str
    timestamp: int
    message_id: Optional[str] = None
    push_name: Optional[str] = None
    media_url: Optional[str] = None
    media_type: Optional[str] = None

    @property
    def timestamp_datetime(self) -> datetime:
        """Convert Unix timestamp to datetime.
        
        Join API sends timestamps in milliseconds, so we normalize to seconds.
        """
        ts = self.timestamp
        if ts > 10_000_000_000:
            ts = ts // 1000
        return datetime.fromtimestamp(ts)

    @property
    def clean_phone(self) -> str:
        """Extract clean phone number (remove @c.us suffix)."""
        return self.from_phone.replace("@c.us", "").replace("@s.whatsapp.net", "")


@dataclass(frozen=True, slots=True)
class OutgoingMessageDTO:
    """DTO for outgoing messages to be sent via WhatsApp."""

    instance_key: str
    to_phone: str
    body: str
    simulate_typing: bool = True


@dataclass(frozen=True, slots=True)
class MessageResponseDTO:
    """DTO for message processing response."""

    success: bool
    message_id: Optional[str] = None
    response_sent: bool = False
    response_text: Optional[str] = None
    ai_disabled: bool = False
    ai_disabled_reason: Optional[str] = None
    error: Optional[str] = None


@dataclass(frozen=True, slots=True)
class ConversationContextDTO:
    """DTO for conversation context used in AI response generation."""

    conversation_id: str
    restaurant_id: str
    customer_phone: str
    customer_name: Optional[str]
    recent_messages: list[dict[str, Any]]
    is_ai_active: bool
    automation_type: str
