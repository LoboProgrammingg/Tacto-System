"""Assistant bounded context."""

from tacto.domain.assistant.ports.ai_client import AIClient, AIRequest, AIResponse
from tacto.domain.assistant.ports.menu_provider import (
    InstitutionalData,
    MenuData,
    MenuItem,
    MenuProvider,
)
from tacto.domain.assistant.services.response_orchestrator import (
    OrchestratorResult,
    ResponseOrchestrator,
)
from tacto.domain.assistant.strategies.base import (
    AutomationStrategy,
    StrategyContext,
    StrategyResult,
)
from tacto.domain.assistant.strategies.basic_strategy import BasicStrategy

__all__ = [
    "AIClient",
    "AIRequest",
    "AIResponse",
    "MenuProvider",
    "MenuData",
    "MenuItem",
    "InstitutionalData",
    "ResponseOrchestrator",
    "OrchestratorResult",
    "AutomationStrategy",
    "StrategyContext",
    "StrategyResult",
    "BasicStrategy",
]
