"""
Base Agent Interface.

Defines the contract for all AI agents across automation levels.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from tacto.domain.shared.result import Failure, Success


@dataclass
class AgentContext:
    """Context for agent execution."""

    restaurant_id: UUID
    restaurant_name: str
    customer_phone: str
    customer_name: Optional[str]
    conversation_id: UUID
    menu_url: str
    prompt_default: str
    opening_hours: dict[str, Any]
    automation_level: int = 1
    is_open: bool = True
    next_opening_text: str = ""
    rag_context: str = ""        # semantic search results (no price)
    tacto_address: str = ""      # address from Tacto rag-full
    tacto_hours: str = ""        # opening hours from Tacto rag-full


@dataclass
class AgentResponse:
    """Response from AI agent."""

    message: str
    should_send: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)
    tokens_used: int = 0
    processing_time_ms: int = 0
    triggered_actions: list[str] = field(default_factory=list)

    @property
    def is_menu_request(self) -> bool:
        """Check if response triggered menu URL send."""
        return "menu_url_sent" in self.triggered_actions


class BaseAgent(ABC):
    """
    Abstract base class for all AI agents.

    Each automation level implements this interface with
    different capabilities and behaviors.
    """

    @property
    @abstractmethod
    def level(self) -> int:
        """Return automation level (1-4)."""
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
        """Initialize agent resources."""
        ...

    @abstractmethod
    async def shutdown(self) -> Success[bool] | Failure[Exception]:
        """Cleanup agent resources."""
        ...
