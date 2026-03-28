"""
AI Client Port (Interface).

Defines the contract for AI/LLM interactions.
Implementation is in infrastructure layer (Gemini, OpenAI, etc.).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from tacto.domain.shared.result import Failure, Success


@dataclass(frozen=True, slots=True)
class AIResponse:
    """Response from AI client."""

    content: str
    model: str
    tokens_used: int
    response_time_ms: int
    finish_reason: Optional[str] = None


@dataclass(frozen=True, slots=True)
class AIRequest:
    """Request to AI client."""

    system_prompt: str
    user_message: str
    context: Optional[str] = None
    max_tokens: int = 2048
    temperature: float = 0.7


class AIClient(ABC):
    """
    Abstract interface for AI/LLM client.

    This port allows the domain to interact with AI services
    without knowing the specific implementation (Gemini, OpenAI, etc.).
    """

    @abstractmethod
    async def generate(
        self, request: AIRequest
    ) -> Success[AIResponse] | Failure[Exception]:
        """
        Generate AI response.

        Args:
            request: The AI request with prompt and context

        Returns:
            Success with AIResponse or Failure with error
        """
        pass

    @abstractmethod
    async def generate_embedding(
        self, text: str
    ) -> Success[list[float]] | Failure[Exception]:
        """
        Generate embedding vector for text.

        Args:
            text: Text to embed

        Returns:
            Success with embedding vector or Failure with error
        """
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if AI service is available."""
        pass
