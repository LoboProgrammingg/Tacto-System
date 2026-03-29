"""
Messaging Client Port (Interface).

Defines the contract for sending messages via WhatsApp gateway.
Implementation is in infrastructure layer (JoinClient, etc.).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from tacto.domain.shared.result import Failure, Success


@dataclass(frozen=True, slots=True)
class SendMessageResult:
    """Result of a message send operation."""

    message_id: Optional[str]
    sent: bool


class MessagingClient(ABC):
    """
    Abstract interface for sending WhatsApp messages.

    This port allows the application layer to send messages without
    coupling to any specific gateway provider (Join, Twilio, etc.).
    """

    @abstractmethod
    async def send_message(
        self,
        instance_key: str,
        phone: str,
        message: str,
        simulate_typing: bool = True,
    ) -> Success[SendMessageResult] | Failure[Exception]:
        """
        Send a text message to a WhatsApp number.

        Args:
            instance_key: Restaurant/canal identifier in the gateway.
            phone: Destination phone number (E.164 or gateway format).
            message: Text content to send.
            simulate_typing: Whether to simulate a typing indicator before sending.

        Returns:
            Success with SendMessageResult, or Failure with error.
        """
        ...
