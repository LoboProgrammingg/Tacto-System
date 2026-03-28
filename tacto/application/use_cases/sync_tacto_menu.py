"""
SyncTactoMenu Use Case.

Fetches restaurant data from Tacto External API, generates Gemini embeddings
for each menu item (name + description, NO price) and saves them to pgvector.

This enables semantic search at message time:
  customer asks "tem pizza de calabresa?" →
  embed query → cosine search → return matching items (no price) to AI context.
"""

from dataclasses import dataclass
from uuid import UUID

import structlog

from tacto.domain.assistant.ports.menu_provider import MenuProvider
from tacto.domain.restaurant.repository import RestaurantRepository
from tacto.domain.shared.result import Err, Failure, Ok, Success
from tacto.domain.shared.value_objects import RestaurantId
from tacto.infrastructure.ai.gemini_client import GeminiClient
from tacto.infrastructure.vector_store.pgvector_store import PgvectorStore


logger = structlog.get_logger()


@dataclass
class SyncResultDTO:
    restaurant_id: UUID
    restaurant_name: str
    items_synced: int
    categories: list[str]
    address: str | None
    hours_text: str


class SyncTactoMenuUseCase:
    """
    Syncs Tacto menu data to pgvector embeddings.

    Flow:
    1. Load restaurant from DB (gets empresa_base_id + grupo_empresarial)
    2. Fetch full menu from Tacto rag-full endpoint
    3. For each available item: generate Gemini embedding of content (no price)
    4. Bulk-save to menu_embeddings table (replaces previous data)
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

        # 3. Generate embeddings for each item (content = name + category + description, NO price)
        embedding_items: list[dict] = []
        failed = 0

        for item in available_items:
            content = item.to_embed_content()
            embedding_result = await self._gemini_client.generate_embedding(content)

            if isinstance(embedding_result, Failure):
                log.warning("embedding_failed", item=item.name, error=str(embedding_result.error))
                failed += 1
                continue

            embedding_items.append({
                "content": item.to_context_text(),   # what AI will read (no price)
                "embedding": embedding_result.value,
                "metadata": {
                    "name": item.name,
                    "category": item.category,
                    "has_description": item.description is not None,
                },
            })

        log.info("embeddings_generated", success=len(embedding_items), failed=failed)

        # 4. Save to pgvector (replaces previous embeddings for this restaurant)
        save_result = await self._pgvector_store.upsert_menu_embeddings(
            restaurant_id, embedding_items
        )
        if isinstance(save_result, Failure):
            log.error("pgvector_save_failed", error=str(save_result.error))
            return save_result

        log.info("sync_complete", items_saved=save_result.value)

        return Ok(SyncResultDTO(
            restaurant_id=restaurant.id.value,
            restaurant_name=restaurant.name,
            items_synced=save_result.value,
            categories=menu.categories,
            address=menu.address,
            hours_text=menu.hours_text,
        ))
