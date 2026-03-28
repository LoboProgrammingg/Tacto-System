"""
AI Domain Layer.

Contains AI agents, memory systems, and prompts for different automation levels.

Automation Levels:
- Level 1 (BASIC): Informational responses, menu URL, humanized conversation
- Level 2 (INTERMEDIATE): Order taking, cart management (future)
- Level 3 (ADVANCED): Full order processing with Tacto API (future)
- Level 4 (ENTERPRISE): Multi-channel, analytics, custom flows (future)
"""

from tacto.domain.ai.agents.base_agent import BaseAgent, AgentResponse
from tacto.domain.ai.agents.level1_agent import Level1Agent
from tacto.domain.ai.memory.memory_manager import MemoryManager, ConversationMemory

__all__ = [
    "BaseAgent",
    "AgentResponse",
    "Level1Agent",
    "MemoryManager",
    "ConversationMemory",
]
