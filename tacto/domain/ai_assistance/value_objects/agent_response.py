"""Agent response Value Object.

Pure VO — no I/O, no framework dependencies.
Carries the agent's response along with metadata and triggered actions.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentResponse:
    """Response from AI agent — pure Value Object, no I/O."""

    message: str
    should_send: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)
    tokens_used: int = 0
    processing_time_ms: int = 0
    triggered_actions: list[str] = field(default_factory=list)

    @property
    def is_menu_request(self) -> bool:
        """Check if response triggered menu URL send."""
        return "menu_url_sent" in self.triggered_actions
