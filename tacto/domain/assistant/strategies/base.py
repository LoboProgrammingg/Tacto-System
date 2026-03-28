"""
Base Strategy Interface.

Defines the contract for automation strategies (BASIC, INTERMEDIATE, ADVANCED).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from tacto.domain.assistant.ports.ai_client import AIRequest
from tacto.domain.restaurant.entities.restaurant import Restaurant
from tacto.domain.shared.result import Failure, Success


@dataclass(frozen=True, slots=True)
class StrategyContext:
    """
    Context provided to automation strategies.

    Contains all information needed to generate a response.
    """

    restaurant: Restaurant
    user_message: str
    conversation_history: list[dict[str, str]]
    institutional_data: Optional[str] = None
    menu_data: Optional[str] = None
    detected_intent: Optional[str] = None


@dataclass(frozen=True, slots=True)
class StrategyResult:
    """Result from strategy execution."""

    ai_request: AIRequest
    strategy_name: str
    restrictions: list[str]


class AutomationStrategy(ABC):
    """
    Abstract base class for automation strategies.

    Each strategy level (BASIC, INTERMEDIATE, ADVANCED) implements
    this interface with different capabilities and restrictions.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Strategy name for logging and metrics."""
        pass

    @abstractmethod
    def build_request(
        self, context: StrategyContext
    ) -> Success[StrategyResult] | Failure[Exception]:
        """
        Build AI request based on strategy rules.

        Args:
            context: All context needed for response generation

        Returns:
            Success with StrategyResult or Failure with error
        """
        pass

    @abstractmethod
    def validate_response(self, response: str) -> Success[str] | Failure[Exception]:
        """
        Validate and potentially filter AI response.

        Args:
            response: Raw AI response

        Returns:
            Success with validated response or Failure if invalid
        """
        pass

    @abstractmethod
    def get_restrictions(self) -> list[str]:
        """Get list of restrictions for this strategy level."""
        pass
