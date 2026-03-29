"""
AIEnabled — Evento emitido quando a IA é reativada numa conversa.

Emitido por: Conversation.enable_ai()
"""

from dataclasses import dataclass
from uuid import UUID

from tacto.domain.shared.events.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class AIEnabled(DomainEvent):
    """Fato: a IA foi reativada para esta conversa."""

    conversation_id: UUID
    restaurant_id: UUID
    customer_phone: str
