"""
Basic Automation Strategy.

Level 1 automation - institutional information only.
NO menu details, NO product recommendations, NO order creation.
"""

import re
from typing import Optional

from tacto.domain.assistant.ports.ai_client import AIRequest
from tacto.domain.assistant.strategies.base import (
    AutomationStrategy,
    StrategyContext,
    StrategyResult,
)
from tacto.domain.shared.exceptions import ValidationError
from tacto.domain.shared.result import Err, Failure, Ok, Success


BASIC_SYSTEM_PROMPT_TEMPLATE = """Você é um assistente virtual cordial e profissional do restaurante {restaurant_name}.

INFORMAÇÕES INSTITUCIONAIS:
{institutional_data}

HORÁRIO DE FUNCIONAMENTO HOJE:
{today_hours}

URL DO CARDÁPIO:
{menu_url}

REGRAS OBRIGATÓRIAS:
1. Seja sempre educado e profissional
2. NÃO mencione preços específicos de produtos
3. NÃO faça recomendações de produtos específicos
4. NÃO crie ou gerencie pedidos
5. Para perguntas sobre cardápio, direcione o cliente para: {menu_url}
6. Responda APENAS sobre informações institucionais (horário, endereço, formas de pagamento, etc.)
7. Se perguntarem sobre produtos específicos, diga que podem consultar o cardápio no link
8. NUNCA use palavrões ou linguagem inadequada
9. NUNCA mencione concorrentes
10. Mantenha respostas concisas e objetivas

CONTEXTO DA CONVERSA:
{conversation_context}
"""

FORBIDDEN_WORDS = [
    "porra", "caralho", "merda", "foda", "puta", "viado", "buceta",
    "cu", "cacete", "desgraça", "fdp", "pqp", "vsf", "tnc",
]

COMPETITOR_PATTERNS = [
    r"\bifood\b", r"\bubereats\b", r"\brappi\b", r"\b99food\b",
    r"\bmcdonalds\b", r"\bburger king\b", r"\bsubway\b",
]


class BasicStrategy(AutomationStrategy):
    """
    Basic automation strategy (Level 1).

    Capabilities:
    - Answer institutional questions (hours, address, payment)
    - Provide menu URL
    - Basic greetings and farewells

    Restrictions:
    - Cannot discuss specific products/prices
    - Cannot make recommendations
    - Cannot create orders
    """

    @property
    def name(self) -> str:
        return "basic"

    def build_request(
        self, context: StrategyContext
    ) -> Success[StrategyResult] | Failure[Exception]:
        """Build AI request with BASIC level restrictions."""
        try:
            conversation_context = self._format_conversation_history(
                context.conversation_history
            )

            system_prompt = BASIC_SYSTEM_PROMPT_TEMPLATE.format(
                restaurant_name=context.restaurant.name,
                institutional_data=context.institutional_data or "Não disponível",
                today_hours=context.restaurant.get_today_hours(),
                menu_url=context.restaurant.menu_url,
                conversation_context=conversation_context,
            )

            ai_request = AIRequest(
                system_prompt=system_prompt,
                user_message=context.user_message,
                context=conversation_context,
                max_tokens=512,
                temperature=0.7,
            )

            return Ok(
                StrategyResult(
                    ai_request=ai_request,
                    strategy_name=self.name,
                    restrictions=self.get_restrictions(),
                )
            )
        except Exception as e:
            return Err(e)

    def validate_response(self, response: str) -> Success[str] | Failure[Exception]:
        """Validate response doesn't violate BASIC level rules."""
        lower_response = response.lower()

        for word in FORBIDDEN_WORDS:
            if word in lower_response:
                return Err(
                    ValidationError(
                        message=f"Response contains forbidden word: {word}",
                        field="response",
                    )
                )

        for pattern in COMPETITOR_PATTERNS:
            if re.search(pattern, lower_response, re.IGNORECASE):
                return Err(
                    ValidationError(
                        message="Response mentions competitor",
                        field="response",
                    )
                )

        return Ok(response)

    def get_restrictions(self) -> list[str]:
        """Get BASIC level restrictions."""
        return [
            "NO_PRODUCT_DETAILS",
            "NO_PRICES",
            "NO_RECOMMENDATIONS",
            "NO_ORDER_CREATION",
            "INSTITUTIONAL_ONLY",
        ]

    def _format_conversation_history(
        self, history: list[dict[str, str]], max_messages: int = 5
    ) -> str:
        """Format conversation history for context."""
        if not history:
            return "Início da conversa."

        recent = history[-max_messages:]
        formatted = []

        for msg in recent:
            role = "Cliente" if msg.get("role") == "user" else "Assistente"
            content = msg.get("content", "")
            formatted.append(f"{role}: {content}")

        return "\n".join(formatted)
