"""
Unit tests for AgentFactory.

Tests the create_agent function and agent selection logic.

Níveis de Automação:
- Level 1 (BASIC): Informativo
- Level 2 (INTERMEDIATE): Coleta pedidos + handoff para atendente
- Level 3 (ADVANCED): Automação completa (futuro, não implementado)
"""

import pytest

from tacto.domain.restaurant.value_objects.automation_type import AutomationType
from tacto.infrastructure.agents.agent_factory import create_agent
from tacto.infrastructure.agents.level1_agent import Level1Agent
from tacto.infrastructure.agents.level2_agent import Level2Agent


class TestAgentFactory:
    """Tests for agent factory function."""

    def test_create_agent_basic_returns_level1(self):
        """BASIC (1) should return Level1Agent — informativo."""
        agent = create_agent(AutomationType.BASIC)
        assert isinstance(agent, Level1Agent)
        assert agent.level == 1
        assert agent.name == "Level1Agent"

    def test_create_agent_intermediate_returns_level2(self):
        """INTERMEDIATE (2) should return Level2Agent — coleta pedidos com handoff."""
        agent = create_agent(AutomationType.INTERMEDIATE)
        assert isinstance(agent, Level2Agent)
        assert agent.level == 2
        assert agent.name == "Level2Agent"

    def test_create_agent_advanced_returns_level2_with_warning(self):
        """ADVANCED (3) should return Level2Agent (Level3 not implemented yet)."""
        agent = create_agent(AutomationType.ADVANCED)
        # Level3Agent não existe ainda, usa Level2Agent como fallback
        assert isinstance(agent, Level2Agent)
        assert agent.level == 2
        assert agent.name == "Level2Agent"

    def test_create_agent_with_int_basic(self):
        """Should accept integer 1 for BASIC."""
        agent = create_agent(1)
        assert isinstance(agent, Level1Agent)

    def test_create_agent_with_int_intermediate(self):
        """Should accept integer 2 for INTERMEDIATE."""
        agent = create_agent(2)
        assert isinstance(agent, Level2Agent)

    def test_create_agent_with_int_advanced(self):
        """Should accept integer 3 for ADVANCED (uses Level2 as fallback)."""
        agent = create_agent(3)
        assert isinstance(agent, Level2Agent)

    def test_create_agent_unknown_level_fallback(self):
        """Unknown level should fallback to Level1Agent."""
        agent = create_agent(99)
        assert isinstance(agent, Level1Agent)

    def test_agent_names(self):
        """Each agent should have correct name property."""
        agent1 = create_agent(1)
        agent2 = create_agent(2)

        assert agent1.name == "Level1Agent"
        assert agent2.name == "Level2Agent"

    def test_level2_is_for_intermediate_not_advanced(self):
        """Level2Agent is used for INTERMEDIATE (2), not ADVANCED (3)."""
        intermediate = create_agent(AutomationType.INTERMEDIATE)
        advanced = create_agent(AutomationType.ADVANCED)

        # Ambos usam Level2Agent por enquanto
        assert isinstance(intermediate, Level2Agent)
        assert isinstance(advanced, Level2Agent)

        # Mas INTERMEDIATE é o nível correto para Level2
        assert AutomationType.INTERMEDIATE.requires_handoff is True
        assert AutomationType.ADVANCED.can_finalize_orders is True
