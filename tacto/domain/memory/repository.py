"""
Repository interface for memory domain.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from domain.shared.result import Result


class MemoryRepository(ABC):
    """
    Abstract repository for memory operations.
    """
    
    @abstractmethod
    async def save(self, entity) -> Result[Any, Exception]:
        """Save an entity."""
        pass
    
    @abstractmethod
    async def find_by_id(self, entity_id: str) -> Result[Optional[Any], Exception]:
        """Find entity by ID."""
        pass
    
    @abstractmethod
    async def find_all(self) -> Result[List[Any], Exception]:
        """Find all entities."""
        pass
    
    @abstractmethod
    async def delete(self, entity_id: str) -> Result[bool, Exception]:
        """Delete an entity."""
        pass
