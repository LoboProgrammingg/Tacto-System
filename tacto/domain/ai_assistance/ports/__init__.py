"""
AI Assistance Ports.

SHIM: Re-exports from tacto.application.ports for backward compatibility.
New code should import directly from tacto.application.ports.
"""

from tacto.application.ports import (
    AIClient,
    AIRequest,
    AIResponse,
    BaseAgent,
    EmbeddingClient,
    InstitutionalData,
    MenuData,
    MenuItem,
    MenuProvider,
    MessagingClient,
    SendMessageResult,
    VectorStore,
)

__all__ = [
    "BaseAgent",
    "AIClient",
    "AIRequest",
    "AIResponse",
    "EmbeddingClient",
    "InstitutionalData",
    "MenuData",
    "MenuItem",
    "MenuProvider",
    "MessagingClient",
    "SendMessageResult",
    "VectorStore",
]
