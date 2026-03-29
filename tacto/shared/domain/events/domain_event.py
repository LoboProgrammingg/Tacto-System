"""
DomainEvent — Base imutável para todos os eventos de domínio.

Eventos são fatos imutáveis que já aconteceram. Eles expressam
mudanças de estado significativas nas entidades de domínio.

Padrão adotado: Pending Events (Event Collector)
  1. A entidade acumula eventos em `pending_events`
  2. Após o save, o repositório (ou use case) lê e despacha os eventos
  3. Não há acoplamento entre domínio e infraestrutura de mensageria
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass(frozen=True)
class DomainEvent:
    """
    Base imutável para todos os eventos de domínio.

    Subclasses devem usar `@dataclass(frozen=True, kw_only=True)` para
    adicionar campos específicos sem conflito de ordering com os campos base.
    """

    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def event_type(self) -> str:
        """Nome do evento — usado para roteamento e logging."""
        return self.__class__.__name__
