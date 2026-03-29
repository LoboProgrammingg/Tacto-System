"""Agent Port — pure interface for all AI agents.

Defines the contract that infrastructure-level agent implementations must satisfy.
The domain/application layer depends only on this interface, never on concrete agents.
"""

from abc import ABC, abstractmethod

from tacto.domain.ai_assistance.value_objects.agent_context import AgentContext
from tacto.domain.ai_assistance.value_objects.agent_response import AgentResponse
from tacto.shared.application import Failure, Success


class BaseAgent(ABC):
    """
    Abstract interface for all AI agents across automation levels.

    Concrete implementations (Level1Agent, Level2Agent, …) live in
    infrastructure/agents/ — they perform actual LLM calls.
    """

    @property
    @abstractmethod
    def level(self) -> int:
        """Return automation level (1–4)."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Return agent name for logging."""
        ...

    @abstractmethod
    async def process(
        self,
        message: str,
        context: AgentContext,
        conversation_history: list[dict[str, str]],
    ) -> Success[AgentResponse] | Failure[Exception]:
        """
        Process incoming message and generate response.

        Args:
            message: Customer message text
            context: Agent execution context with restaurant info
            conversation_history: Recent conversation messages

        Returns:
            Success with AgentResponse or Failure with error
        """
        ...

    @abstractmethod
    async def initialize(self) -> Success[bool] | Failure[Exception]:
        """Initialize agent resources (LLM client, chains, etc.)."""
        ...

    @abstractmethod
    async def shutdown(self) -> Success[bool] | Failure[Exception]:
        """Cleanup agent resources."""
        ...
