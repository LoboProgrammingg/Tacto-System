"""
FetchTactoRestaurantData Use Case.

Fetches menu and institutional data from Tacto External API for a given restaurant.
Supports force-refresh to bypass Redis cache.
"""

from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID

import structlog

from tacto.domain.assistant.ports.menu_provider import MenuProvider
from tacto.domain.restaurant.repository import RestaurantRepository
from tacto.domain.shared.result import Err, Failure, Ok, Success
from tacto.domain.shared.value_objects import RestaurantId


logger = structlog.get_logger()


@dataclass
class TactoMenuItemDTO:
    name: str
    category: str
    price: float
    description: Optional[str] = None
    is_available: bool = True


@dataclass
class TactoRestaurantDataDTO:
    restaurant_id: UUID
    restaurant_name: str
    tacto_name: str
    total_items: int
    categories: list[str]
    menu_items: list[TactoMenuItemDTO]
    raw_menu_text: str
    payment_methods: list[str]
    address: Optional[str]
    phone: Optional[str]
    delivery_info: Optional[str]
    cached: bool
    last_updated: str


class FetchTactoRestaurantDataUseCase:
    """
    Fetches full restaurant data (menu + institutional) from Tacto External API.

    Reads empresa_base_id and chave_grupo_empresarial from the Restaurant entity
    — no extra DB query needed, all data is already loaded.
    """

    def __init__(
        self,
        restaurant_repository: RestaurantRepository,
        menu_provider: MenuProvider,
    ) -> None:
        self._restaurant_repo = restaurant_repository
        self._menu_provider = menu_provider

    async def execute(
        self,
        restaurant_id: UUID,
        force_refresh: bool = False,
    ) -> Success[TactoRestaurantDataDTO] | Failure[Exception]:
        log = logger.bind(restaurant_id=str(restaurant_id))

        restaurant_result = await self._restaurant_repo.find_by_id(
            RestaurantId(restaurant_id)
        )
        if isinstance(restaurant_result, Failure):
            return restaurant_result

        restaurant = restaurant_result.value
        if restaurant is None:
            return Err(ValueError(f"Restaurant {restaurant_id} not found"))

        empresa_base_id = restaurant.empresa_base_id
        grupo_empresarial = str(restaurant.chave_grupo_empresarial)

        if force_refresh:
            await self._invalidate_cache(restaurant_id)

        menu_result = await self._menu_provider.get_menu(
            restaurant.id,
            empresa_base_id=empresa_base_id,
            grupo_empresarial=grupo_empresarial,
        )
        if isinstance(menu_result, Failure):
            log.error("Failed to fetch menu from Tacto", error=str(menu_result.error))
            return menu_result

        institutional_result = await self._menu_provider.get_institutional_data(
            restaurant.id,
            empresa_base_id=empresa_base_id,
            grupo_empresarial=grupo_empresarial,
        )

        menu = menu_result.value
        institutional = institutional_result.value if isinstance(institutional_result, Success) else None

        items = [
            TactoMenuItemDTO(
                name=item.name,
                category=item.category,
                price=item.price,
                description=item.description,
                is_available=item.is_available,
            )
            for item in menu.items
        ]

        log.info(
            "tacto_data_fetched",
            total_items=len(items),
            categories=len(menu.categories),
            force_refresh=force_refresh,
        )

        return Ok(
            TactoRestaurantDataDTO(
                restaurant_id=restaurant.id.value,
                restaurant_name=restaurant.name,
                tacto_name=institutional.name if institutional else restaurant.name,
                total_items=len(items),
                categories=menu.categories,
                menu_items=items,
                raw_menu_text=menu.raw_text,
                payment_methods=institutional.payment_methods if institutional else [],
                address=institutional.address if institutional else None,
                phone=institutional.phone if institutional else None,
                delivery_info=institutional.delivery_info if institutional else None,
                cached=not force_refresh,
                last_updated=menu.last_updated,
            )
        )

    async def _invalidate_cache(self, restaurant_id: UUID) -> None:
        """Clear Redis cache for this restaurant's Tacto data."""
        # TactoMenuProvider handles cache via redis — if menu_provider exposes
        # a clear method we call it; otherwise the next fetch will hit the API.
        if hasattr(self._menu_provider, "_redis") and self._menu_provider._redis:
            rid = RestaurantId(restaurant_id)
            for prefix in ("menu", "institutional"):
                key = f"tacto:{prefix}:{rid.value}"
                try:
                    await self._menu_provider._redis.delete(key)
                except Exception:
                    pass
