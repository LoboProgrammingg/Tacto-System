"""
Agent Factory.

Factory for creating and managing AI agents based on automation level.
Follows the Factory pattern for clean dependency injection.
"""

from typing import Optional

import structlog

from tacto.application.ports.agent_port import BaseAgent
from tacto.application.services.memory_orchestration_service import MemoryManager
from tacto.application.services.order_state_service import OrderStateService
from tacto.domain.restaurant.value_objects.automation_type import AutomationType
from tacto.shared.application import Err, Failure, Ok, Success


logger = structlog.get_logger()


class AgentFactory:
    """
    Factory for creating AI agents based on automation level.

    Manages the lifecycle of agents and provides the correct agent
    based on restaurant configuration.

    Usage:
        factory = AgentFactory(memory_manager, order_service)
        agent = factory.get_agent(AutomationType.ADVANCED)
    """

    def __init__(
        self,
        memory_manager: Optional[MemoryManager] = None,
        order_service: Optional[OrderStateService] = None,
    ) -> None:
        """
        Initialize factory with shared dependencies.

        Args:
            memory_manager: Shared memory manager for all agents
            order_service: Order service for Level 2 agent
        """
        self._memory_manager = memory_manager
        self._order_service = order_service
        self._agents: dict[AutomationType, BaseAgent] = {}
        self._initialized = False

    async def initialize(self) -> Success[bool] | Failure[Exception]:
        """
        Initialize all agents.

        Should be called once at application startup.
        """
        if self._initialized:
            return Ok(True)

        try:
            from tacto.infrastructure.agents.level1_agent import Level1Agent
            from tacto.infrastructure.agents.level2_agent import Level2Agent

            level1 = Level1Agent(memory_manager=self._memory_manager)
            init_result = await level1.initialize()
            if isinstance(init_result, Failure):
                return init_result
            self._agents[AutomationType.BASIC] = level1
            self._agents[AutomationType.INTERMEDIATE] = level1

            level2 = Level2Agent(
                order_service=self._order_service,
                memory_manager=self._memory_manager,
            )
            init_result = await level2.initialize()
            if isinstance(init_result, Failure):
                return init_result
            self._agents[AutomationType.ADVANCED] = level2

            self._initialized = True
            logger.info(
                "AgentFactory initialized",
                agents=list(self._agents.keys()),
            )
            return Ok(True)

        except Exception as e:
            logger.error("Failed to initialize AgentFactory", error=str(e))
            return Err(e)

    def get_agent(self, automation_type: AutomationType) -> Optional[BaseAgent]:
        """
        Get the appropriate agent for the given automation type.

        Args:
            automation_type: Restaurant's automation level

        Returns:
            The appropriate agent or None if not initialized
        """
        if not self._initialized:
            logger.warning("AgentFactory not initialized")
            return None

        agent = self._agents.get(automation_type)
        if agent is None:
            logger.warning(
                "No agent found for automation type, falling back to BASIC",
                automation_type=automation_type,
            )
            return self._agents.get(AutomationType.BASIC)

        return agent

    def get_agent_for_level(self, level: int) -> Optional[BaseAgent]:
        """
        Get agent by numeric level.

        Args:
            level: 1 for BASIC/INTERMEDIATE, 2 for ADVANCED

        Returns:
            The appropriate agent
        """
        if level >= 3:
            return self.get_agent(AutomationType.ADVANCED)
        return self.get_agent(AutomationType.BASIC)

    async def shutdown(self) -> Success[bool] | Failure[Exception]:
        """Shutdown all agents and release resources."""
        for agent in self._agents.values():
            try:
                await agent.shutdown()
            except Exception as e:
                logger.warning("Error shutting down agent", error=str(e))

        self._agents.clear()
        self._initialized = False
        return Ok(True)

    @property
    def is_initialized(self) -> bool:
        """Check if factory is initialized."""
        return self._initialized
