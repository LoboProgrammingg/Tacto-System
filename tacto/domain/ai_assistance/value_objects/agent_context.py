"""Agent execution context Value Object.

Pure VO — no I/O, no framework dependencies.
Carries all runtime data needed by an AI agent to generate a response.
"""

from dataclasses import dataclass
from typing import Any, Optional
from uuid import UUID


@dataclass
class AgentContext:
    """Context for agent execution — pure Value Object, no I/O."""

    restaurant_id: UUID
    restaurant_name: str
    customer_phone: str
    customer_name: Optional[str]
    conversation_id: UUID
    menu_url: str
    prompt_default: str
    opening_hours: dict[str, Any]
    automation_level: int = 1
    is_open: bool = True
    next_opening_text: str = ""
    rag_context: str = ""               # semantic search results (no price)
    tacto_address: str = ""             # address from Tacto rag-full
    tacto_hours: str = ""               # opening hours from Tacto rag-full
    attendant_name: str = ""            # effective attendant name (restaurant override or platform default)
    attendant_gender: str = "feminino"  # "feminino" | "masculino" | "neutro"
    persona_style: str = "formal"       # "formal" | "informal"
    max_emojis_per_message: int = 1     # 0–5 emojis per message
