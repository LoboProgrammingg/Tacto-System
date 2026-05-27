"""
UpdateRestaurant Use Case.

Partial update of an existing restaurant. Only fields set on the DTO are applied.
Goes through aggregate methods to keep invariants enforced.
"""

from uuid import UUID

from tacto.application.dto.restaurant_dto import (
    RestaurantResponseDTO,
    UpdateRestaurantDTO,
)
from tacto.domain.restaurant.repository import RestaurantRepository
from tacto.domain.restaurant.value_objects.agent_persona import AgentPersonaConfig
from tacto.domain.restaurant.value_objects.automation_type import AutomationType
from tacto.domain.restaurant.value_objects.integration_type import IntegrationType
from tacto.shared.application import Err, Failure, Ok, Success
from tacto.shared.domain.value_objects import RestaurantId


class UpdateRestaurantUseCase:
    """Apply a partial update to a restaurant aggregate."""

    def __init__(self, restaurant_repository: RestaurantRepository) -> None:
        self._restaurant_repository = restaurant_repository

    async def execute(
        self, restaurant_id: UUID, dto: UpdateRestaurantDTO
    ) -> Success[RestaurantResponseDTO] | Failure[Exception]:
        try:
            find_result = await self._restaurant_repository.find_by_id(
                RestaurantId(restaurant_id)
            )
            if isinstance(find_result, Failure):
                return find_result
            restaurant = find_result.value
            if restaurant is None:
                return Err(ValueError(f"Restaurant {restaurant_id} not found"))

            if dto.name is not None:
                restaurant.rename(dto.name)

            if dto.menu_url is not None:
                restaurant.update_menu_url(dto.menu_url)

            if dto.prompt_default is not None:
                restaurant.update_prompt(dto.prompt_default)

            if dto.automation_type is not None:
                restaurant.change_automation_type(AutomationType(dto.automation_type))

            if dto.integration_type is not None:
                restaurant.change_integration_type(IntegrationType(dto.integration_type))

            if dto.timezone is not None:
                restaurant.timezone = dto.timezone

            if dto.is_active is not None:
                if dto.is_active:
                    restaurant.activate()
                else:
                    restaurant.deactivate()

            if dto.agent_config is not None:
                restaurant.update_agent_config(AgentPersonaConfig.from_dict(dto.agent_config))

            save_result = await self._restaurant_repository.save(restaurant)
            if isinstance(save_result, Failure):
                return save_result

            return Ok(RestaurantResponseDTO.from_entity(restaurant))

        except Exception as e:
            return Err(e)
