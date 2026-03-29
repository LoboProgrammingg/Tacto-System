"""
Application Ports — Interfaces for Infrastructure Layer.

Following Clean Architecture (Uncle Bob) and Hexagonal Architecture:
- Ports are interfaces defined in the Application layer
- Adapters implement these interfaces in the Infrastructure layer
- Domain/Application layers depend ONLY on these interfaces

This enables:
- Dependency Inversion (DIP from SOLID)
- Easy testing with mocks
- Swappable implementations (e.g., switch from Gemini to OpenAI)
"""

from tacto.application.ports.agent_port import BaseAgent
from tacto.application.ports.ai_client import AIClient, AIRequest, AIResponse
from tacto.application.ports.embedding_client import EmbeddingClient
from tacto.application.ports.menu_provider import (
    InstitutionalData,
    MenuData,
    MenuItem,
    MenuProvider,
)
from tacto.application.ports.messaging_client import MessagingClient, SendMessageResult
from tacto.application.ports.vector_store import VectorStore

__all__ = [
    # Agent
    "BaseAgent",
    # AI
    "AIClient",
    "AIRequest",
    "AIResponse",
    "EmbeddingClient",
    # Menu
    "InstitutionalData",
    "MenuData",
    "MenuItem",
    "MenuProvider",
    # Messaging
    "MessagingClient",
    "SendMessageResult",
    # Vector Store
    "VectorStore",
]
