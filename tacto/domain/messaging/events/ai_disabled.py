"""
AIDisabled — Evento emitido quando a IA é desativada numa conversa.

Emitido por: Conversation.disable_ai(), Conversation.disable_ai_until_opening()
Causas possíveis: human_intervention, restaurant_closed, customer_requested_human_handoff.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from tacto.shared.domain.events.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class AIDisabled(DomainEvent):
    """Fato: a IA foi desativada para esta conversa."""

    conversation_id: UUID
    restaurant_id: UUID
    customer_phone: str
    reason: str
    disabled_until: Optional[datetime] = None
