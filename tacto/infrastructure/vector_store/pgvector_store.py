"""
PgvectorStore — Menu embeddings persistence and semantic search.

Uses pgvector extension for cosine similarity search over menu items.
Each item is stored as: content (text) + embedding (vector) + metadata (JSON).
"""

from typing import Any, Optional
from uuid import UUID

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tacto.domain.assistant.ports.vector_store import VectorStore
from tacto.domain.shared.result import Err, Failure, Ok, Success


logger = structlog.get_logger()


class PgvectorStore(VectorStore):
    """
    Async pgvector store for menu item embeddings.

    Supports:
    - Upsert (clear + bulk insert) on sync
    - Cosine similarity search for semantic retrieval
    - Per-restaurant isolation via restaurant_id
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_menu_embeddings(
        self,
        restaurant_id: UUID,
        items: list[dict[str, Any]],
    ) -> Success[bool] | Failure[Exception]:
        """
        Replace all menu embeddings for a restaurant.

        Each item must have:
          - content: str          (text shown to AI — name + description, NO price)
          - embedding: list[float] (vector from Gemini)
          - metadata: dict        (name, category — optional)

        Returns:
            Success with number of items saved or Failure
        """
        import json

        try:
            await self._clear(restaurant_id)

            if not items:
                return Ok(0)

            for item in items:
                vector_str = _vector_to_pg(item["embedding"])
                metadata_json = json.dumps(item.get("metadata", {}))

                # asyncpg doesn't support :param::type casts — inline vector literal
                # (safe: _vector_to_pg produces only [float,...] format)
                await self._session.execute(
                    text(f"""
                        INSERT INTO menu_embeddings (restaurant_id, content, embedding, metadata)
                        VALUES (:rid, :content, '{vector_str}'::vector, CAST(:metadata AS jsonb))
                    """),
                    {
                        "rid": str(restaurant_id),
                        "content": item["content"],
                        "metadata": metadata_json,
                    },
                )

            logger.info(
                "menu_embeddings_saved",
                restaurant_id=str(restaurant_id),
                count=len(items),
            )
            return Ok(True)

        except Exception as e:
            logger.error("menu_embeddings_upsert_failed", error=str(e))
            return Err(e)

    async def search_menu(
        self,
        restaurant_id: UUID,
        embedding: list[float],
        limit: int = 5,
    ) -> Success[list[dict[str, Any]]] | Failure[Exception]:
        """
        Find the most semantically similar menu items to the query.

        Uses cosine similarity (<=> operator in pgvector).
        Returns items ordered by relevance (most similar first).

        Args:
            restaurant_id: Restaurant UUID
            query_embedding: Embedding of the customer's message
            limit: Max number of items to return

        Returns:
            Success with list of {content, metadata, similarity} or Failure
        """
        try:
            vector_str = _vector_to_pg(embedding)

            # asyncpg doesn't support :param::type casts — inline vector literal
            result = await self._session.execute(
                text(f"""
                    SELECT
                        content,
                        metadata,
                        1 - (embedding <=> '{vector_str}'::vector) AS similarity
                    FROM menu_embeddings
                    WHERE restaurant_id = :restaurant_id
                    ORDER BY embedding <=> '{vector_str}'::vector
                    LIMIT :limit
                """),
                {
                    "restaurant_id": str(restaurant_id),
                    "limit": limit,
                },
            )

            rows = result.fetchall()
            return Ok([
                {
                    "content": row.content,
                    "metadata": row.metadata or {},
                    "similarity": float(row.similarity),
                }
                for row in rows
            ])

        except Exception as e:
            logger.error("menu_embeddings_search_failed", error=str(e))
            return Err(e)

    async def count(self, restaurant_id: UUID) -> Success[int] | Failure[Exception]:
        """Return number of embeddings stored for a restaurant."""
        try:
            result = await self._session.execute(
                text("SELECT COUNT(*) FROM menu_embeddings WHERE restaurant_id = :rid"),
                {"rid": str(restaurant_id)},
            )
            return Ok(result.scalar() or 0)
        except Exception as e:
            return Err(e)

    async def delete_all(self, restaurant_id: UUID) -> Success[bool] | Failure[Exception]:
        """Delete all embeddings for a restaurant."""
        try:
            await self._session.execute(
                text("DELETE FROM menu_embeddings WHERE restaurant_id = :rid"),
                {"rid": str(restaurant_id)},
            )
            return Ok(True)
        except Exception as e:
            return Err(e)

    async def _clear(self, restaurant_id: UUID) -> None:
        await self._session.execute(
            text("DELETE FROM menu_embeddings WHERE restaurant_id = :rid"),
            {"rid": str(restaurant_id)},
        )


# ── Helpers ────────────────────────────────────────────────────────────────────

def _vector_to_pg(embedding: list[float]) -> str:
    """Convert Python list to pgvector literal string."""
    return "[" + ",".join(str(v) for v in embedding) + "]"


def _serialize_items(items: list[dict[str, Any]]) -> str:
    """Serialize items list to JSON string for bulk INSERT."""
    import json

    serialized = []
    for item in items:
        serialized.append({
            "content": item["content"],
            "embedding": _vector_to_pg(item["embedding"]),
            "metadata": json.dumps(item.get("metadata", {})),
        })
    return json.dumps(serialized)
