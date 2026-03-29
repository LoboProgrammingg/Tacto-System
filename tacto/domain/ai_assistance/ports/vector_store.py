"""
Vector Store Port (Interface).

Defines the contract for vector similarity search and storage.
Implementation is in infrastructure layer (PgvectorStore, etc.).
"""

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from tacto.domain.shared.result import Failure, Success


class VectorStore(ABC):
    """
    Abstract interface for vector similarity search and storage.

    This port allows the application layer to perform RAG (Retrieval-Augmented
    Generation) searches without coupling to a specific vector DB implementation.
    """

    @abstractmethod
    async def upsert_menu_embeddings(
        self,
        restaurant_id: UUID,
        items: list[dict[str, Any]],
    ) -> Success[bool] | Failure[Exception]:
        """Upsert menu items with their pre-computed embeddings."""
        ...

    @abstractmethod
    async def search_menu(
        self,
        restaurant_id: UUID,
        embedding: list[float],
        limit: int = 6,
    ) -> Success[list[dict[str, Any]]] | Failure[Exception]:
        """Search menu items by vector similarity (cosine distance)."""
        ...

    @abstractmethod
    async def count(
        self,
        restaurant_id: UUID,
    ) -> Success[int] | Failure[Exception]:
        """Count embeddings stored for a given restaurant."""
        ...

    @abstractmethod
    async def delete_all(
        self,
        restaurant_id: UUID,
    ) -> Success[bool] | Failure[Exception]:
        """Delete all embeddings for a given restaurant."""
        ...
