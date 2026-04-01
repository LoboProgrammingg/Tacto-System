"""
CreateRestaurant Use Case.

Application layer use case for creating new restaurants.
"""

from tacto.application.dto.restaurant_dto import (
    CreateRestaurantDTO,
    RestaurantResponseDTO,
)
from tacto.domain.restaurant.entities.restaurant import Restaurant
from tacto.domain.restaurant.repository import RestaurantRepository
from tacto.domain.restaurant.value_objects.agent_persona import AgentPersonaConfig
from tacto.domain.restaurant.value_objects.automation_type import AutomationType
from tacto.domain.restaurant.value_objects.integration_type import IntegrationType
from tacto.domain.restaurant.value_objects.opening_hours import OpeningHours
from tacto.shared.application import Err, Failure, Ok, Success
from tacto.shared.domain.value_objects import RestaurantId


class CreateRestaurantUseCase:
    """
    Use case for creating a new restaurant.

    Validates input, creates domain entity, and persists it.
    """

    def __init__(self, restaurant_repository: RestaurantRepository) -> None:
        """
        Initialize use case with dependencies.

        Args:
            restaurant_repository: Repository for restaurant persistence
        """
        self._restaurant_repository = restaurant_repository

    async def execute(
        self, dto: CreateRestaurantDTO
    ) -> Success[RestaurantResponseDTO] | Failure[Exception]:
        """
        Execute the create restaurant use case.

        Args:
            dto: Data for creating the restaurant

        Returns:
            Success with RestaurantResponseDTO or Failure with error
        """
        try:
            existing_result = await self._restaurant_repository.find_by_canal_master_id(
                dto.canal_master_id
            )

            if isinstance(existing_result, Failure):
                return existing_result

            if existing_result.value is not None:
                return Err(
                    ValueError(
                        f"Restaurant with canal_master_id '{dto.canal_master_id}' already exists"
                    )
                )

            opening_hours = OpeningHours.from_dict(dto.opening_hours or {})

            restaurant = Restaurant.create(
                name=dto.name,
                prompt_default=dto.prompt_default,
                menu_url=dto.menu_url,
                opening_hours=opening_hours,
                integration_type=IntegrationType(dto.integration_type),
                automation_type=AutomationType(dto.automation_type),
                chave_grupo_empresarial=dto.chave_grupo_empresarial,
                canal_master_id=dto.canal_master_id,
                empresa_base_id=dto.empresa_base_id,
                timezone=dto.timezone,
                agent_config=AgentPersonaConfig.from_dict(dto.agent_config),
            )

            save_result = await self._restaurant_repository.save(restaurant)

            if isinstance(save_result, Failure):
                return save_result

            return Ok(RestaurantResponseDTO.from_entity(restaurant))

        except Exception as e:
            return Err(e)
