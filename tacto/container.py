"""
Dependency Injection Container.

Provides centralized dependency management following Clean Architecture.
"""

from dataclasses import dataclass
from typing import Optional

from tacto.config import Settings, get_settings
from tacto.domain.assistant.ports.ai_client import AIClient
from tacto.infrastructure.ai.gemini_client import GeminiClient
from tacto.infrastructure.external.tacto_client import TactoClient
from tacto.infrastructure.messaging.join_client import JoinClient
from tacto.infrastructure.messaging.sent_message_tracker import SentMessageTracker
from tacto.infrastructure.redis.redis_client import RedisClient


@dataclass
class Container:
    """
    Dependency Injection Container.

    Manages application dependencies and their lifecycle.
    Follows the Composition Root pattern.
    """

    settings: Settings
    redis_client: RedisClient
    gemini_client: GeminiClient
    join_client: JoinClient
    tacto_client: TactoClient

    @classmethod
    def create(cls, settings: Optional[Settings] = None) -> "Container":
        """
        Factory method to create container with all dependencies.

        Args:
            settings: Application settings. If None, loads from environment.

        Returns:
            Configured Container instance
        """
        settings = settings or get_settings()

        redis_client = RedisClient(settings.redis)
        gemini_client = GeminiClient(settings.gemini)
        message_tracker = SentMessageTracker(redis_client)
        join_client = JoinClient(settings.join, message_tracker=message_tracker)
        tacto_client = TactoClient(settings.tacto)

        return cls(
            settings=settings,
            redis_client=redis_client,
            gemini_client=gemini_client,
            join_client=join_client,
            tacto_client=tacto_client,
        )

    async def initialize(self) -> None:
        """Initialize all async dependencies."""
        await self.redis_client.connect()
        await self.join_client.connect()
        await self.tacto_client.connect()

    async def shutdown(self) -> None:
        """Shutdown all dependencies gracefully."""
        await self.redis_client.disconnect()
        await self.join_client.disconnect()
        await self.tacto_client.disconnect()

    def get_ai_client(self) -> AIClient:
        """Get AI client instance."""
        return self.gemini_client


_container: Optional[Container] = None


def get_container() -> Container:
    """Get or create the global container instance."""
    global _container
    if _container is None:
        _container = Container.create()
    return _container


async def initialize_container() -> Container:
    """Initialize and return the container."""
    container = get_container()
    await container.initialize()
    return container


async def shutdown_container() -> None:
    """Shutdown the global container."""
    global _container
    if _container is not None:
        await _container.shutdown()
        _container = None
