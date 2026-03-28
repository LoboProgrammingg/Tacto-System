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
        """
        Upsert menu items with their pre-computed embeddings.

        Args:
            restaurant_id: Tenant identifier — embeddings are scoped per restaurant.
            items: List of dicts, each containing 'content', 'embedding', and 'metadata'.

        Returns:
            Success(True) on success, or Failure with error.
        """
        ...

    @abstractmethod
    async def search_menu(
        self,
        restaurant_id: UUID,
        embedding: list[float],
        limit: int = 6,
    ) -> Success[list[dict[str, Any]]] | Failure[Exception]:
        """
        Search menu items by vector similarity (cosine distance).

        Args:
            restaurant_id: Tenant identifier — search is scoped per restaurant.
            embedding: Query embedding vector.
            limit: Maximum number of results to return.

        Returns:
            Success with list of matching menu item dicts, or Failure.
        """
        ...

    @abstractmethod
    async def count(
        self,
        restaurant_id: UUID,
    ) -> Success[int] | Failure[Exception]:
        """
        Count embeddings stored for a given restaurant.

        Args:
            restaurant_id: Tenant identifier.

        Returns:
            Success with count integer, or Failure.
        """
        ...

    @abstractmethod
    async def delete_all(
        self,
        restaurant_id: UUID,
    ) -> Success[bool] | Failure[Exception]:
        """
        Delete all embeddings for a given restaurant.

        Args:
            restaurant_id: Tenant identifier.

        Returns:
            Success(True) on success, or Failure.
        """
        ...
