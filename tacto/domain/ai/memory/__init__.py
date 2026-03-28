"""AI Memory — re-exports from new locations for backward compatibility.

DEPRECATED: Import directly from:
- tacto.domain.customer_memory (VOs and Ports)
- tacto.application.services.memory_orchestration_service (MemoryManager)
"""

from tacto.domain.customer_memory.value_objects.memory_entry import (
    ConversationMemory,
    MemoryEntry,
    MemoryType,
)
from tacto.domain.customer_memory.ports.memory_port import MemoryPort
from tacto.application.services.memory_orchestration_service import MemoryManager

__all__ = [
    "MemoryManager",
    "MemoryEntry",
    "ConversationMemory",
    "MemoryType",
    "MemoryPort",
]
