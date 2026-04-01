"""
Restaurant HTTP Routes.

CRUD operations for restaurant management.
"""

from typing import Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from tacto.application.dto.restaurant_dto import CreateRestaurantDTO, RestaurantResponseDTO
from tacto.interfaces.http.dependencies import get_create_restaurant_use_case
from tacto.interfaces.http.schemas.restaurant import (
    CreateRestaurantRequest,
    RestaurantListResponse,
    RestaurantResponse,
    TactoMenuItemResponse,
    TactoRestaurantDataResponse,
    TactoSyncResponse,
)


logger = structlog.get_logger()
router = APIRouter()


@router.post(
    "/",
    response_model=RestaurantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Restaurant",
    description="Create a new restaurant with automation configuration",
)
async def create_restaurant(
    request: CreateRestaurantRequest,
    use_case=Depends(get_create_restaurant_use_case),
) -> RestaurantResponse:
    """Create a new restaurant."""
    dto = CreateRestaurantDTO(
        name=request.name,
        prompt_default="",
        menu_url=request.menu_url,
        opening_hours=request.opening_hours,
        chave_grupo_empresarial=request.chave_grupo_empresarial,
        canal_master_id=request.canal_master_id,
        empresa_base_id=request.empresa_base_id,
        integration_type=request.integration_type,
        automation_type=request.automation_type,
        agent_config=request.agent_config.model_dump(exclude_none=True) if request.agent_config else None,
    )

    result = await use_case.execute(dto)

    if result.is_failure():
        logger.error("Failed to create restaurant", error=str(result.error))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(result.error),
        )

    response_dto = result.value

    return RestaurantResponse(
        id=response_dto.id,
        name=response_dto.name,
        prompt_default=response_dto.prompt_default,
        menu_url=response_dto.menu_url,
        opening_hours=response_dto.opening_hours,
        integration_type=response_dto.integration_type,
        automation_type=response_dto.automation_type,
        chave_grupo_empresarial=response_dto.chave_grupo_empresarial,
        canal_master_id=response_dto.canal_master_id,
        empresa_base_id=response_dto.empresa_base_id,
        is_active=response_dto.is_active,
        agent_config=response_dto.agent_config or {},
    )


@router.get(
    "/",
    response_model=RestaurantListResponse,
    summary="List Restaurants",
    description="Get all active restaurants",
)
async def list_restaurants() -> RestaurantListResponse:
    """List all active restaurants."""
    from tacto.shared.application import Failure
    from tacto.infrastructure.database.connection import get_async_session
    from tacto.infrastructure.persistence.restaurant_repository import (
        PostgresRestaurantRepository,
    )

    async with get_async_session() as session:
        repo = PostgresRestaurantRepository(session)
        result = await repo.find_all_active()

    if isinstance(result, Failure):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(result.error),
        )

    items = [
        RestaurantResponse(
            id=r.id.value,
            name=r.name,
            prompt_default=r.prompt_default,
            menu_url=r.menu_url,
            opening_hours=r.opening_hours.to_dict(),
            integration_type=r.integration_type.value,
            automation_type=r.automation_type.value,
            chave_grupo_empresarial=r.chave_grupo_empresarial,
            canal_master_id=r.canal_master_id,
            empresa_base_id=r.empresa_base_id,
            is_active=r.is_active,
        )
        for r in result.value
    ]
    return RestaurantListResponse(items=items, total=len(items))


@router.get(
    "/{restaurant_id}",
    response_model=RestaurantResponse,
    summary="Get Restaurant",
    description="Get restaurant by ID",
)
async def get_restaurant(restaurant_id: UUID) -> RestaurantResponse:
    """Get restaurant by ID."""
    from tacto.shared.application import Failure
    from tacto.shared.domain.value_objects import RestaurantId
    from tacto.infrastructure.database.connection import get_async_session
    from tacto.infrastructure.persistence.restaurant_repository import (
        PostgresRestaurantRepository,
    )

    async with get_async_session() as session:
        repo = PostgresRestaurantRepository(session)
        result = await repo.find_by_id(RestaurantId(restaurant_id))

    if isinstance(result, Failure) or result.value is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Restaurant {restaurant_id} not found",
        )

    r = result.value
    return RestaurantResponse(
        id=r.id.value,
        name=r.name,
        prompt_default=r.prompt_default,
        menu_url=r.menu_url,
        opening_hours=r.opening_hours.to_dict(),
        integration_type=r.integration_type.value,
        automation_type=r.automation_type.value,
        chave_grupo_empresarial=r.chave_grupo_empresarial,
        canal_master_id=r.canal_master_id,
        empresa_base_id=r.empresa_base_id,
        is_active=r.is_active,
    )


@router.post(
    "/{restaurant_id}/tacto-sync",
    response_model=TactoSyncResponse,
    status_code=status.HTTP_200_OK,
    summary="Sync Tacto Menu to Vector Store",
    description=(
        "Fetches menu from Tacto External API, generates Gemini embeddings for each item "
        "(name + description, never prices) and saves to pgvector. "
        "Run this once after creating a restaurant and whenever the menu changes."
    ),
)
async def sync_tacto_menu(
    restaurant_id: UUID,
    request: Request,
) -> TactoSyncResponse:
    """Generate embeddings from Tacto menu and save to pgvector."""
    from tacto.shared.application import Failure
    from tacto.infrastructure.database.connection import get_async_session
    from tacto.infrastructure.external.tacto_menu_provider import TactoMenuProvider
    from tacto.infrastructure.ai.gemini_client import GeminiClient
    from tacto.infrastructure.persistence.restaurant_repository import PostgresRestaurantRepository
    from tacto.infrastructure.database.pgvector_store import PgvectorStore
    from tacto.application.use_cases.sync_tacto_menu import SyncTactoMenuUseCase

    redis_client = getattr(request.app.state, "redis", None)
    tacto_client = getattr(request.app.state, "tacto_client", None)
    if tacto_client is None:
        from tacto.infrastructure.external.tacto_client import TactoClient
        tacto_client = TactoClient()

    async with get_async_session() as session:
        use_case = SyncTactoMenuUseCase(
            restaurant_repository=PostgresRestaurantRepository(session),
            menu_provider=TactoMenuProvider(
                tacto_client=tacto_client,
                redis_client=redis_client,
            ),
            pgvector_store=PgvectorStore(session),
            gemini_client=GeminiClient(),
        )
        result = await use_case.execute(restaurant_id)

    if isinstance(result, Failure):
        error_msg = str(result.error)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_msg)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Sync failed: {error_msg}")

    data = result.value
    return TactoSyncResponse(
        restaurant_id=data.restaurant_id,
        restaurant_name=data.restaurant_name,
        items_synced=data.items_synced,
        categories=data.categories,
        address=data.address,
        hours_text=data.hours_text,
    )


@router.get(
    "/{restaurant_id}/tacto-data",
    response_model=TactoRestaurantDataResponse,
    summary="Fetch Tacto Restaurant Data",
    description=(
        "Fetches menu and institutional data from Tacto External API for the restaurant. "
        "Results are cached in Redis for 1 hour. Use `force_refresh=true` to bypass cache."
    ),
)
async def fetch_tacto_restaurant_data(
    restaurant_id: UUID,
    request: Request,
    force_refresh: bool = Query(default=False, description="Bypass Redis cache and fetch fresh data from Tacto"),
) -> TactoRestaurantDataResponse:
    """Fetch full restaurant data from Tacto External API."""
    from tacto.shared.application import Failure
    from tacto.shared.domain.value_objects import RestaurantId
    from tacto.infrastructure.database.connection import get_async_session
    from tacto.infrastructure.external.tacto_menu_provider import TactoMenuProvider
    from tacto.infrastructure.persistence.restaurant_repository import PostgresRestaurantRepository
    from tacto.application.use_cases.fetch_tacto_restaurant_data import FetchTactoRestaurantDataUseCase

    redis_client = getattr(request.app.state, "redis", None)
    tacto_client = getattr(request.app.state, "tacto_client", None)
    if tacto_client is None:
        from tacto.infrastructure.external.tacto_client import TactoClient
        tacto_client = TactoClient()

    menu_provider = TactoMenuProvider(tacto_client=tacto_client, redis_client=redis_client)

    async with get_async_session() as session:
        use_case = FetchTactoRestaurantDataUseCase(
            restaurant_repository=PostgresRestaurantRepository(session),
            menu_provider=menu_provider,
        )
        result = await use_case.execute(restaurant_id, force_refresh=force_refresh)

    if isinstance(result, Failure):
        error_msg = str(result.error)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_msg)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Tacto API error: {error_msg}")

    data = result.value
    return TactoRestaurantDataResponse(
        restaurant_id=data.restaurant_id,
        restaurant_name=data.restaurant_name,
        tacto_name=data.tacto_name,
        total_items=data.total_items,
        categories=data.categories,
        menu_items=[
            TactoMenuItemResponse(
                name=item.name,
                category=item.category,
                price=item.price,
                description=item.description,
                is_available=item.is_available,
            )
            for item in data.menu_items
        ],
        raw_menu_text=data.raw_menu_text,
        payment_methods=data.payment_methods,
        address=data.address,
        phone=data.phone,
        delivery_info=data.delivery_info,
        cached=data.cached,
        last_updated=data.last_updated,
    )


@router.delete(
    "/{restaurant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Restaurant",
    description="Soft delete a restaurant",
)
async def delete_restaurant(restaurant_id: UUID) -> None:
    """Delete restaurant by ID."""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Restaurant {restaurant_id} not found",
    )
