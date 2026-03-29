"""
RestaurantCreated — Evento emitido quando um novo restaurante é criado.

Emitido por: Restaurant.create()
Consumidores potenciais: provisionamento inicial (sync menu, embeddings), analytics.
"""

from dataclasses import dataclass
from uuid import UUID

from tacto.shared.domain.events.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class RestaurantCreated(DomainEvent):
    """Fato: um novo restaurante foi criado no sistema."""

    restaurant_id: UUID
    name: str
    canal_master_id: str
