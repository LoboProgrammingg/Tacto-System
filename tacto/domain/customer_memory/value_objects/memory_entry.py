"""
Customer Memory Value Objects.

Pure domain objects with no I/O dependencies.
These represent the core concepts of the memory system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID


class MemoryType(Enum):
    """Types of memory storage."""

    SHORT_TERM = "short"  # Current conversation (Redis, 30min)
    MEDIUM_TERM = "medium"  # Recent summary (Redis, 24h)
    LONG_TERM = "long"  # Persistent preferences (PostgreSQL)


@dataclass
class MemoryEntry:
    """A single memory entry."""

    key: str
    content: str
    memory_type: MemoryType
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)
    relevance_score: float = 1.0


@dataclass
class ConversationMemory:
    """Complete memory context for a conversation."""

    restaurant_id: UUID
    customer_phone: str
    customer_name: Optional[str] = None

    short_term: list[MemoryEntry] = field(default_factory=list)
    medium_term: list[MemoryEntry] = field(default_factory=list)
    long_term: list[MemoryEntry] = field(default_factory=list)

    @property
    def has_history(self) -> bool:
        """Check if customer has any history."""
        return bool(self.medium_term or self.long_term)

    @property
    def display_name(self) -> str:
        """Get customer display name."""
        return self.customer_name or "Cliente"

    def get_context_summary(self) -> str:
        """
        Build legacy single-block context summary.

        Kept for backward compatibility. Prefer the three dedicated
        methods below for new prompt integrations.
        """
        parts = [
            self.get_long_term_summary(),
            self.get_medium_term_summary(),
            self.get_short_term_summary(),
        ]
        return "\n\n".join(p for p in parts if p)

    def get_long_term_summary(self) -> str:
        """
        Return long-term memory block for prompt injection.

        Contains persistent customer preferences, known allergies,
        favorite items, and behavioral patterns.
        """
        if not self.long_term:
            return ""
        lines = []
        for entry in self.long_term[:8]:
            lines.append(f"- {entry.content}")
        return "\n".join(lines)

    def get_medium_term_summary(self) -> str:
        """
        Return medium-term memory block for prompt injection.

        Contains recent session summaries and last known orders
        from the past 24 hours.
        """
        if not self.medium_term:
            return ""
        lines = []
        for entry in self.medium_term[:4]:
            lines.append(f"- {entry.content}")
        return "\n".join(lines)

    def get_short_term_summary(self) -> str:
        """
        Return short-term memory block for prompt injection.

        Contains the current active conversation messages
        (last ~30 minutes).
        """
        if not self.short_term:
            return ""
        lines = []
        for entry in self.short_term[-6:]:
            role = entry.metadata.get("role", "user")
            prefix = "Cliente" if role == "user" else "Atendente"
            lines.append(f"{prefix}: {entry.content}")
        return "\n".join(lines)
