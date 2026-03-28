"""Automation strategies for AI responses."""

from tacto.domain.assistant.strategies.base import AutomationStrategy, StrategyContext
from tacto.domain.assistant.strategies.basic_strategy import BasicStrategy

__all__ = [
    "AutomationStrategy",
    "StrategyContext",
    "BasicStrategy",
]
