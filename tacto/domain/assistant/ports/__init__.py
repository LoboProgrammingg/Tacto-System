"""Ports (interfaces) for Assistant context."""

from tacto.domain.assistant.ports.ai_client import AIClient
from tacto.domain.assistant.ports.embedding_client import EmbeddingClient
from tacto.domain.assistant.ports.menu_provider import MenuProvider
from tacto.domain.assistant.ports.messaging_client import MessagingClient, SendMessageResult
from tacto.domain.assistant.ports.vector_store import VectorStore

__all__ = [
    "AIClient",
    "EmbeddingClient",
    "MenuProvider",
    "MessagingClient",
    "SendMessageResult",
    "VectorStore",
]
