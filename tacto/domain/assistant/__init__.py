"""Assistant bounded context — ports only (services/strategies removed as dead code)."""

from tacto.domain.assistant.ports.ai_client import AIClient, AIRequest, AIResponse
from tacto.domain.assistant.ports.menu_provider import (
    InstitutionalData,
    MenuData,
    MenuItem,
    MenuProvider,
)

__all__ = [
    "AIClient",
    "AIRequest",
    "AIResponse",
    "MenuProvider",
    "MenuData",
    "MenuItem",
    "InstitutionalData",
]
