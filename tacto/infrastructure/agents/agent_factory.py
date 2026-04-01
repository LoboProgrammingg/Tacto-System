"""
AgentFactory — selects the correct AI agent based on restaurant automation_type.

AutomationType mapping:
  1 (BASIC)        → Level1Agent — informativo, horários, endereço, menu básico
  2 (INTERMEDIATE) → Level2Agent — coleta pedidos mas NÃO finaliza, faz handoff para atendente
  3 (ADVANCED)     → Level3Agent — automação completa (FUTURO, não implementado)

Level 2 monta o carrinho completo mas SEMPRE pede para o cliente aguardar
um atendente humano para confirmar taxa de entrega e finalizar o pedido.
"""

from typing import Optional

import structlog

from tacto.application.ports.agent_port import BaseAgent
from tacto.application.services.memory_orchestration_service import MemoryManager
from tacto.application.services.order_state_service import OrderStateService
from tacto.domain.restaurant.value_objects.automation_type import AutomationType
from tacto.infrastructure.agents.level1_agent import Level1Agent
from tacto.infrastructure.agents.level2_agent import Level2Agent


logger = structlog.get_logger()


def create_agent(
    automation_type: int | AutomationType,
    memory_manager: Optional[MemoryManager] = None,
    order_service: Optional[OrderStateService] = None,
) -> BaseAgent:
    """
    Return the appropriate agent for the given automation level.

    Args:
        automation_type: int (1–3) or AutomationType enum value.
        memory_manager: Optional memory manager for 3-level conversation memory.
        order_service: Optional order service for Level 2 agent.

    Returns:
        Concrete BaseAgent implementation.
    """
    level = int(automation_type)

    if level == AutomationType.BASIC:
        logger.debug("Creating Level1Agent", automation_type=level)
        return Level1Agent(memory_manager=memory_manager)

    if level == AutomationType.INTERMEDIATE:
        # Level 2: Coleta pedidos mas faz handoff para atendente
        logger.info("Creating Level2Agent for INTERMEDIATE (handoff mode)", automation_type=level)
        return Level2Agent(
            order_service=order_service,
            memory_manager=memory_manager,
        )

    if level == AutomationType.ADVANCED:
        # Level 3: Automação completa (FUTURO - por enquanto usa Level2 com handoff)
        logger.warning(
            "Level3Agent not implemented yet, using Level2Agent with handoff",
            automation_type=level,
        )
        return Level2Agent(
            order_service=order_service,
            memory_manager=memory_manager,
        )

    # Unknown level — fall back to Level1
    logger.warning(
        "unknown_automation_level",
        requested_level=level,
        fallback_level=1,
    )
    return Level1Agent(memory_manager=memory_manager)
