"""
MessageReceived — Evento emitido quando uma mensagem é recebida numa conversa.

Emitido por: Conversation.record_message()
Consumidores potenciais: analytics, notificações, auditoria.
"""

from dataclasses import dataclass
from uuid import UUID

from tacto.shared.domain.events.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class MessageReceived(DomainEvent):
    """Fato: uma mensagem chegou numa conversa ativa."""

    conversation_id: UUID
    restaurant_id: UUID
    customer_phone: str
