"""
PgvectorStore — Menu embeddings persistence and semantic search.

Uses pgvector extension for cosine similarity search over menu items.
Each item is stored as: content (text) + embedding (vector) + metadata (JSON).
"""

import json
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tacto.application.ports.vector_store import VectorStore
from tacto.shared.application import Err, Failure, Ok, Success


logger = structlog.get_logger()


class PgvectorStore(VectorStore):
    """
    Async pgvector store for menu item embeddings.

    Supports:
    - Upsert (clear + bulk insert) on sync
    - Cosine similarity search for semantic retrieval
    - Per-restaurant isolation via restaurant_id
    - Content hash caching for incremental sync
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ──────────────────────────────────────────────────────────────────────────
    # Core Operations
    # ──────────────────────────────────────────────────────────────────────────

    async def upsert_menu_embeddings(
        self,
        restaurant_id: UUID,
        items: list[dict[str, Any]],
    ) -> Success[int] | Failure[Exception]:
        """
        Replace all menu embeddings for a restaurant.

        Each item must have:
          - content: str           (text shown to AI)
          - embedding: list[float] (vector from Gemini)
          - metadata: dict         (name, category, content_hash — optional)

        Returns:
            Success with number of items saved or Failure
        """
        try:
            await self._clear(restaurant_id)

            if not items:
                return Ok(0)

            for item in items:
                vector_str = _vector_to_pg(item["embedding"])
                metadata_json = json.dumps(item.get("metadata", {}))

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
            return Ok(len(items))

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
        """
        try:
            vector_str = _vector_to_pg(embedding)

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

    # ──────────────────────────────────────────────────────────────────────────
    # Cache Support (for incremental sync)
    # ──────────────────────────────────────────────────────────────────────────

    async def get_content_hashes(
        self, restaurant_id: UUID
    ) -> Success[dict[str, str]] | Failure[Exception]:
        """
        Return {item_name: content_hash} for all embeddings.

        Used by sync_tacto_menu to skip unchanged items.
        """
        try:
            result = await self._session.execute(
                text("""
                    SELECT 
                        metadata->>'name' AS name,
                        metadata->>'content_hash' AS content_hash
                    FROM menu_embeddings
                    WHERE restaurant_id = :rid
                      AND metadata->>'name' IS NOT NULL
                      AND metadata->>'content_hash' IS NOT NULL
                """),
                {"rid": str(restaurant_id)},
            )

            rows = result.fetchall()
            return Ok({row.name: row.content_hash for row in rows})

        except Exception as e:
            logger.error("get_content_hashes_failed", error=str(e))
            return Err(e)

    async def get_embeddings_by_names(
        self,
        restaurant_id: UUID,
        names: list[str],
    ) -> Success[dict[str, list[float]]] | Failure[Exception]:
        """
        Return {item_name: embedding_vector} for given names.

        Used to reuse cached embeddings for unchanged items.
        """
        if not names:
            return Ok({})

        try:
            result = await self._session.execute(
                text("""
                    SELECT 
                        metadata->>'name' AS name,
                        embedding::text AS embedding_text
                    FROM menu_embeddings
                    WHERE restaurant_id = :rid
                      AND metadata->>'name' = ANY(:names)
                """),
                {"rid": str(restaurant_id), "names": names},
            )

            rows = result.fetchall()
            embeddings = {}
            for row in rows:
                embeddings[row.name] = _pg_to_vector(row.embedding_text)

            return Ok(embeddings)

        except Exception as e:
            logger.error("get_embeddings_by_names_failed", error=str(e))
            return Err(e)

    # ──────────────────────────────────────────────────────────────────────────
    # Utility Methods
    # ──────────────────────────────────────────────────────────────────────────

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
        """Clear all embeddings for a restaurant."""
        await self._session.execute(
            text("DELETE FROM menu_embeddings WHERE restaurant_id = :rid"),
            {"rid": str(restaurant_id)},
        )


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _vector_to_pg(embedding: list[float]) -> str:
    """Convert Python list to pgvector literal string."""
    return "[" + ",".join(str(v) for v in embedding) + "]"


def _pg_to_vector(pg_text: str) -> list[float]:
    """Convert pgvector text representation to Python list."""
    clean = pg_text.strip("[]")
    if not clean:
        return []
    return [float(v) for v in clean.split(",")]
