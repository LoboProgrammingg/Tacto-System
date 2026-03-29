"""
DomainEvent — Base imutável para todos os eventos de domínio.

SHIM: Re-exports from tacto.shared.domain.events.domain_event for backward compatibility.
"""

from tacto.shared.domain.events.domain_event import DomainEvent

__all__ = ["DomainEvent"]
