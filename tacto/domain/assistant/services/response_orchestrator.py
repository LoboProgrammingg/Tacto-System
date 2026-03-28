"""
Response Orchestrator - Domain Service.

Orchestrates the complete flow of generating AI responses.
This is the main entry point for message processing.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from tacto.domain.assistant.ports.ai_client import AIClient, AIResponse
from tacto.domain.assistant.ports.menu_provider import MenuProvider
from tacto.domain.assistant.strategies.base import AutomationStrategy, StrategyContext
from tacto.domain.assistant.strategies.basic_strategy import BasicStrategy
from tacto.domain.messaging.entities.conversation import Conversation
from tacto.domain.restaurant.entities.restaurant import Restaurant
from tacto.domain.restaurant.value_objects.automation_type import AutomationType
from tacto.domain.shared.exceptions import BusinessRuleViolationError
from tacto.domain.shared.result import Err, Failure, Ok, Success


@dataclass(frozen=True, slots=True)
class OrchestratorResult:
    """Result from orchestrator execution."""

    response_text: str
    strategy_used: str
    tokens_used: int
    response_time_ms: int
    was_filtered: bool = False


CLOSED_RESTAURANT_TEMPLATE = """Olá! 😊

No momento estamos fechados.

🕐 Nosso horário de funcionamento hoje: {today_hours}

Aguardamos você! 🍽️"""


class ResponseOrchestrator:
    """
    Domain Service that orchestrates AI response generation.

    Responsibilities:
    1. Check if restaurant is open
    2. Check if AI can respond (not disabled)
    3. Select appropriate strategy based on automation level
    4. Build context for AI
    5. Generate and validate response
    """

    def __init__(
        self,
        ai_client: AIClient,
        menu_provider: MenuProvider,
    ) -> None:
        """
        Initialize orchestrator with dependencies.

        Args:
            ai_client: AI client for generating responses
            menu_provider: Provider for menu and institutional data
        """
        self._ai_client = ai_client
        self._menu_provider = menu_provider
        self._strategies: dict[AutomationType, AutomationStrategy] = {
            AutomationType.BASIC: BasicStrategy(),
        }

    async def generate_response(
        self,
        restaurant: Restaurant,
        conversation: Conversation,
        user_message: str,
        conversation_history: list[dict[str, str]],
    ) -> Success[OrchestratorResult] | Failure[Exception]:
        """
        Generate AI response for user message.

        Args:
            restaurant: The restaurant handling the message
            conversation: The conversation context
            user_message: The user's message
            conversation_history: Recent conversation history

        Returns:
            Success with OrchestratorResult or Failure with error
        """
        if not restaurant.can_process_ai_response():
            return Err(
                BusinessRuleViolationError(
                    rule="BR-REST-003",
                    message="Restaurant is not active or has been deleted",
                )
            )

        if not conversation.can_ai_respond():
            return Err(
                BusinessRuleViolationError(
                    rule="BR-CONV-001",
                    message="AI is disabled for this conversation",
                )
            )

        if not restaurant.is_open_now():
            return Ok(
                OrchestratorResult(
                    response_text=CLOSED_RESTAURANT_TEMPLATE.format(
                        today_hours=restaurant.get_today_hours()
                    ),
                    strategy_used="closed_hours",
                    tokens_used=0,
                    response_time_ms=0,
                )
            )

        strategy = self._get_strategy(restaurant.automation_type)
        if strategy is None:
            return Err(
                BusinessRuleViolationError(
                    rule="BR-STRAT-001",
                    message=f"No strategy available for automation type: {restaurant.automation_type}",
                )
            )

        institutional_data = await self._get_institutional_data(restaurant)

        context = StrategyContext(
            restaurant=restaurant,
            user_message=user_message,
            conversation_history=conversation_history,
            institutional_data=institutional_data,
            menu_data=None,
            detected_intent=None,
        )

        request_result = strategy.build_request(context)
        if isinstance(request_result, Failure):
            return request_result

        strategy_result = request_result.value

        start_time = datetime.utcnow()
        ai_result = await self._ai_client.generate(strategy_result.ai_request)

        if isinstance(ai_result, Failure):
            return ai_result

        ai_response: AIResponse = ai_result.value
        response_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        validation_result = strategy.validate_response(ai_response.content)

        was_filtered = False
        final_response = ai_response.content

        if isinstance(validation_result, Failure):
            was_filtered = True
            final_response = self._get_fallback_response(restaurant)

        return Ok(
            OrchestratorResult(
                response_text=final_response,
                strategy_used=strategy_result.strategy_name,
                tokens_used=ai_response.tokens_used,
                response_time_ms=response_time,
                was_filtered=was_filtered,
            )
        )

    def _get_strategy(self, automation_type: AutomationType) -> Optional[AutomationStrategy]:
        """Get strategy for automation type."""
        return self._strategies.get(automation_type)

    async def _get_institutional_data(self, restaurant: Restaurant) -> Optional[str]:
        """Fetch institutional data for restaurant."""
        result = await self._menu_provider.get_institutional_data(restaurant.id)
        if isinstance(result, Success):
            return result.value.raw_text
        return None

    def _get_fallback_response(self, restaurant: Restaurant) -> str:
        """Get fallback response when AI response is filtered."""
        return (
            f"Olá! Obrigado por entrar em contato com {restaurant.name}. "
            f"Para mais informações, acesse nosso cardápio em: {restaurant.menu_url}"
        )
