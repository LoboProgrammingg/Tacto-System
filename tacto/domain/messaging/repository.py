"""
Repository Interfaces for Messaging Context.

Defines contracts for Conversation and Message persistence.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from tacto.domain.messaging.entities.conversation import Conversation
from tacto.domain.messaging.entities.message import Message
from tacto.shared.application import Failure, Success
from tacto.shared.domain.value_objects import (
    ConversationId,
    MessageId,
    PhoneNumber,
    RestaurantId,
)


class ConversationRepository(ABC):
    """
    Abstract repository for Conversation aggregate.

    Handles persistence of conversations and their state.
    """

    @abstractmethod
    async def save(
        self, conversation: Conversation
    ) -> Success[Conversation] | Failure[Exception]:
        """Persist a conversation."""
        pass

    @abstractmethod
    async def find_by_id(
        self, conversation_id: ConversationId
    ) -> Success[Optional[Conversation]] | Failure[Exception]:
        """Find conversation by ID."""
        pass

    @abstractmethod
    async def find_by_restaurant_and_phone(
        self,
        restaurant_id: RestaurantId,
        customer_phone: PhoneNumber,
    ) -> Success[Optional[Conversation]] | Failure[Exception]:
        """
        Find conversation by restaurant and customer phone.

        This is the primary lookup method for incoming messages.
        """
        pass

    @abstractmethod
    async def find_active_by_restaurant(
        self,
        restaurant_id: RestaurantId,
        limit: int = 50,
        offset: int = 0,
    ) -> Success[list[Conversation]] | Failure[Exception]:
        """Find active conversations for a restaurant."""
        pass

    @abstractmethod
    async def find_with_disabled_ai(
        self,
        restaurant_id: RestaurantId,
    ) -> Success[list[Conversation]] | Failure[Exception]:
        """Find conversations where AI is currently disabled."""
        pass


class MessageRepository(ABC):
    """
    Abstract repository for Message entities.

    Messages belong to Conversations but have their own repository
    for performance reasons (high volume).
    """

    @abstractmethod
    async def save(self, message: Message) -> Success[Message] | Failure[Exception]:
        """Persist a message."""
        pass

    @abstractmethod
    async def save_batch(
        self, messages: list[Message]
    ) -> Success[list[Message]] | Failure[Exception]:
        """Persist multiple messages in a batch."""
        pass

    @abstractmethod
    async def find_by_id(
        self, message_id: MessageId
    ) -> Success[Optional[Message]] | Failure[Exception]:
        """Find message by ID."""
        pass

    @abstractmethod
    async def find_by_conversation(
        self,
        conversation_id: ConversationId,
        limit: int = 50,
        before: Optional[datetime] = None,
    ) -> Success[list[Message]] | Failure[Exception]:
        """
        Find messages for a conversation.

        Args:
            conversation_id: The conversation to get messages for
            limit: Maximum number of messages to return
            before: Only return messages before this timestamp (for pagination)

        Returns:
            Messages ordered by timestamp descending (newest first)
        """
        pass

    @abstractmethod
    async def find_recent_by_conversation(
        self,
        conversation_id: ConversationId,
        limit: int = 10,
    ) -> Success[list[Message]] | Failure[Exception]:
        """
        Find most recent messages for context building.

        Returns messages ordered by timestamp ascending (oldest first)
        for proper context building.
        """
        pass

    @abstractmethod
    async def count_by_conversation(
        self, conversation_id: ConversationId
    ) -> Success[int] | Failure[Exception]:
        """Count total messages in a conversation."""
        pass
