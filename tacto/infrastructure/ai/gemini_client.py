"""
Gemini AI Client - Infrastructure Implementation.

Implements the AIClient port using Google Gemini API.
"""

import time
from typing import Optional

from google import genai
from google.genai import types as genai_types

from tacto.config import GeminiSettings, get_settings
from tacto.domain.ai_assistance.ports.ai_client import AIClient, AIRequest, AIResponse
from tacto.domain.ai_assistance.ports.embedding_client import EmbeddingClient
from tacto.domain.shared.result import Err, Failure, Ok, Success


class GeminiClient(AIClient, EmbeddingClient):
    """
    Google Gemini AI client implementation.

    Implements the AIClient port for generating AI responses
    and embeddings using Google's Gemini models.
    """

    def __init__(self, settings: Optional[GeminiSettings] = None) -> None:
        """
        Initialize Gemini client.

        Args:
            settings: Gemini settings. If None, loads from environment.
        """
        self._settings = settings or get_settings().gemini
        self._client: Optional[genai.Client] = None
        self._configured = False

    def _ensure_configured(self) -> None:
        """Ensure API client is initialised."""
        if not self._configured:
            self._client = genai.Client(api_key=self._settings.api_key)
            self._configured = True

    async def generate(
        self, request: AIRequest
    ) -> Success[AIResponse] | Failure[Exception]:
        """
        Generate AI response using Gemini.

        Args:
            request: The AI request with prompt and context

        Returns:
            Success with AIResponse or Failure with error
        """
        try:
            self._ensure_configured()

            full_prompt = self._build_prompt(request)
            start_time = time.time()

            response = await self._client.aio.models.generate_content(
                model=self._settings.llm_model,
                contents=full_prompt,
                config=genai_types.GenerateContentConfig(
                    max_output_tokens=request.max_tokens,
                    temperature=request.temperature,
                ),
            )

            elapsed_ms = int((time.time() - start_time) * 1000)

            text = response.text
            if not text:
                return Err(RuntimeError("Empty response from Gemini"))

            tokens_used = 0
            if response.usage_metadata:
                tokens_used = response.usage_metadata.total_token_count or 0

            return Ok(
                AIResponse(
                    content=text,
                    model=self._settings.llm_model,
                    tokens_used=tokens_used,
                    response_time_ms=elapsed_ms,
                )
            )

        except Exception as e:
            return Err(e)

    async def generate_embedding(
        self, text: str
    ) -> Success[list[float]] | Failure[Exception]:
        """Generate embedding vector for text using Gemini embedding model."""
        try:
            self._ensure_configured()

            response = await self._client.aio.models.embed_content(
                model=self._settings.embedding_model,
                contents=text,
                config=genai_types.EmbedContentConfig(
                    task_type="RETRIEVAL_DOCUMENT",
                    output_dimensionality=self._settings.embedding_dimension,
                ),
            )

            embedding = response.embeddings[0].values if response.embeddings else []
            if not embedding:
                return Err(RuntimeError("Empty embedding from Gemini"))

            return Ok(list(embedding))

        except Exception as e:
            return Err(e)

    async def is_available(self) -> bool:
        """Check if Gemini service is available."""
        try:
            self._ensure_configured()
            async for _ in self._client.aio.models.list():
                return True
            return False
        except Exception:
            return False

    def _build_prompt(self, request: AIRequest) -> str:
        """Build full prompt from request components."""
        parts = [request.system_prompt]

        if request.context:
            parts.append(f"\n\nCONTEXTO:\n{request.context}")

        parts.append(f"\n\nMENSAGEM DO CLIENTE:\n{request.user_message}")

        return "\n".join(parts)
