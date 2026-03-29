"""
SyncTactoMenu Use Case.

Fetches restaurant data from Tacto External API, generates Gemini embeddings
for each menu item (name + description, NO price) and saves them to pgvector.

Implements **incremental sync** — skips embedding generation for unchanged items
by comparing content hashes. This dramatically reduces Gemini API calls.

This enables semantic search at message time:
  customer asks "tem pizza de calabresa?" →
  embed query → cosine search → return matching items (no price) to AI context.
"""

import hashlib
from dataclasses import dataclass
from uuid import UUID

import structlog

from tacto.domain.ai_assistance.ports.menu_provider import MenuProvider, MenuItem
from tacto.domain.restaurant.repository import RestaurantRepository
from tacto.domain.shared.result import Err, Failure, Ok, Success
from tacto.domain.shared.value_objects import RestaurantId
from tacto.infrastructure.ai.gemini_client import GeminiClient
from tacto.infrastructure.database.pgvector_store import PgvectorStore


logger = structlog.get_logger()


@dataclass
class SyncResultDTO:
    """Result of menu sync operation."""

    restaurant_id: UUID
    restaurant_name: str
    items_synced: int
    items_cached: int
    items_new: int
    categories: list[str]
    address: str | None
    hours_text: str


class SyncTactoMenuUseCase:
    """
    Syncs Tacto menu data to pgvector embeddings.

    Flow:
    1. Load restaurant from DB (gets empresa_base_id + grupo_empresarial)
    2. Fetch full menu from Tacto rag-full endpoint
    3. Compare content hashes with existing embeddings
    4. Generate embeddings ONLY for new/changed items
    5. Reuse cached embeddings for unchanged items
    6. Bulk-save to menu_embeddings table
    """

    def __init__(
        self,
        restaurant_repository: RestaurantRepository,
        menu_provider: MenuProvider,
        pgvector_store: PgvectorStore,
        gemini_client: GeminiClient,
    ) -> None:
        self._restaurant_repo = restaurant_repository
        self._menu_provider = menu_provider
        self._pgvector_store = pgvector_store
        self._gemini_client = gemini_client

    async def execute(self, restaurant_id: UUID) -> Success[SyncResultDTO] | Failure[Exception]:
        log = logger.bind(restaurant_id=str(restaurant_id))

        # 1. Load restaurant
        restaurant_result = await self._restaurant_repo.find_by_id(RestaurantId(restaurant_id))
        if isinstance(restaurant_result, Failure):
            return restaurant_result
        restaurant = restaurant_result.value
        if restaurant is None:
            return Err(ValueError(f"Restaurant {restaurant_id} not found"))

        # 2. Fetch from Tacto (bypass Redis cache — always fresh on sync)
        menu_result = await self._menu_provider.get_menu(
            restaurant.id,
            empresa_base_id=restaurant.empresa_base_id,
            grupo_empresarial=str(restaurant.chave_grupo_empresarial),
        )
        if isinstance(menu_result, Failure):
            log.error("tacto_fetch_failed", error=str(menu_result.error))
            return menu_result

        menu = menu_result.value
        available_items = [item for item in menu.items if item.is_available]

        log.info("tacto_menu_fetched", total=len(menu.items), available=len(available_items))

        # 3. Get existing content hashes for incremental sync
        hashes_result = await self._pgvector_store.get_content_hashes(restaurant_id)
        existing_hashes: dict[str, str] = {}
        if isinstance(hashes_result, Success):
            existing_hashes = hashes_result.value

        # 4. Classify items: cached (unchanged) vs to_embed (new/changed)
        to_embed: list[tuple[MenuItem, str, str]] = []  # (item, content, hash)
        cached_names: list[str] = []

        for item in available_items:
            content = item.to_embed_content()
            content_hash = _compute_hash(content)

            if existing_hashes.get(item.name) == content_hash:
                cached_names.append(item.name)
            else:
                to_embed.append((item, content, content_hash))

        log.info(
            "incremental_sync_analysis",
            cached=len(cached_names),
            to_embed=len(to_embed),
        )

        # 5. Fetch cached embeddings (no Gemini call needed)
        cached_embeddings: dict[str, list[float]] = {}
        if cached_names:
            cached_result = await self._pgvector_store.get_embeddings_by_names(
                restaurant_id, cached_names
            )
            if isinstance(cached_result, Success):
                cached_embeddings = cached_result.value

        # 6. Generate embeddings ONLY for new/changed items
        embedding_items: list[dict] = []
        failed = 0

        for item, content, content_hash in to_embed:
            embedding_result = await self._gemini_client.generate_embedding(content)

            if isinstance(embedding_result, Failure):
                log.warning("embedding_failed", item=item.name, error=str(embedding_result.error))
                failed += 1
                continue

            embedding_items.append(
                _build_embedding_item(item, embedding_result.value, content_hash)
            )

        # 7. Add cached embeddings (reuse existing vectors)
        for item in available_items:
            if item.name in cached_embeddings:
                content_hash = _compute_hash(item.to_embed_content())
                embedding_items.append(
                    _build_embedding_item(item, cached_embeddings[item.name], content_hash)
                )

        log.info(
            "embeddings_prepared",
            new_generated=len(to_embed) - failed,
            reused_from_cache=len(cached_embeddings),
            failed=failed,
        )

        # 8. Save to pgvector (replaces previous embeddings for this restaurant)
        save_result = await self._pgvector_store.upsert_menu_embeddings(
            restaurant_id, embedding_items
        )
        if isinstance(save_result, Failure):
            log.error("pgvector_save_failed", error=str(save_result.error))
            return save_result

        items_saved = save_result.value
        log.info("sync_complete", items_saved=items_saved)

        return Ok(SyncResultDTO(
            restaurant_id=restaurant.id.value,
            restaurant_name=restaurant.name,
            items_synced=items_saved,
            items_cached=len(cached_embeddings),
            items_new=len(to_embed) - failed,
            categories=menu.categories,
            address=menu.address,
            hours_text=menu.hours_text,
        ))


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _compute_hash(content: str) -> str:
    """Compute MD5 hash of content for change detection."""
    return hashlib.md5(content.encode()).hexdigest()


def _build_embedding_item(item: MenuItem, embedding: list[float], content_hash: str) -> dict:
    """Build embedding item dict for pgvector storage."""
    return {
        "content": item.to_context_text(),
        "embedding": embedding,
        "metadata": {
            "name": item.name,
            "category": item.category,
            "has_description": item.description is not None,
            "content_hash": content_hash,
        },
    }
