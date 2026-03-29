"""
Embedding Client Port (Interface).

Defines the contract for text embedding generation.
Follows Interface Segregation Principle — separated from the full AIClient.
Implementation is in infrastructure layer (GeminiClient, etc.).
"""

from abc import ABC, abstractmethod

from tacto.domain.shared.result import Failure, Success


class EmbeddingClient(ABC):
    """
    Abstract interface for text embedding generation.

    This port allows the domain/application layer to generate embeddings
    without coupling to any specific provider (Gemini, OpenAI, etc.).
    """

    @abstractmethod
    async def generate_embedding(
        self,
        text: str,
    ) -> Success[list[float]] | Failure[Exception]:
        """
        Generate embedding vector for the given text.

        Args:
            text: Input text to embed.

        Returns:
            Success containing a list of floats (embedding vector), or Failure.
        """
        ...
