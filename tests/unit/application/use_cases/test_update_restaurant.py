"""Unit tests for UpdateRestaurantUseCase."""

from uuid import uuid4

import pytest

from tacto.application.dto.restaurant_dto import UpdateRestaurantDTO
from tacto.application.use_cases.update_restaurant import UpdateRestaurantUseCase
from tacto.domain.restaurant.entities.restaurant import Restaurant
from tacto.domain.restaurant.value_objects.agent_persona import AgentPersonaConfig
from tacto.domain.restaurant.value_objects.automation_type import AutomationType
from tacto.domain.restaurant.value_objects.integration_type import IntegrationType
from tacto.domain.restaurant.value_objects.opening_hours import OpeningHours
from tacto.shared.application import Err, Failure, Ok, Success
from tacto.shared.domain.value_objects import RestaurantId


def _make_restaurant() -> Restaurant:
    return Restaurant.create(
        name="Original Name",
        prompt_default="",
        menu_url="https://example.com/menu",
        opening_hours=OpeningHours.from_dict({}),
        integration_type=IntegrationType(2),
        automation_type=AutomationType(1),
        chave_grupo_empresarial=uuid4(),
        canal_master_id="wp-empresa-test",
        empresa_base_id="base-1",
    )


class _InMemoryRepo:
    def __init__(self, restaurant: Restaurant | None) -> None:
        self._r = restaurant
        self.save_called_with: Restaurant | None = None

    async def find_by_id(self, restaurant_id: RestaurantId):
        if self._r is None:
            return Ok(None)
        if self._r.id.value != restaurant_id.value:
            return Ok(None)
        return Ok(self._r)

    async def save(self, restaurant: Restaurant):
        self.save_called_with = restaurant
        self._r = restaurant
        return Ok(restaurant)


@pytest.mark.asyncio
async def test_update_name_only():
    r = _make_restaurant()
    repo = _InMemoryRepo(r)
    uc = UpdateRestaurantUseCase(repo)  # type: ignore[arg-type]

    result = await uc.execute(r.id.value, UpdateRestaurantDTO(name="New Name"))

    assert isinstance(result, Success)
    assert result.value.name == "New Name"
    assert result.value.menu_url == "https://example.com/menu"
    assert repo.save_called_with is r


@pytest.mark.asyncio
async def test_update_multiple_fields():
    r = _make_restaurant()
    repo = _InMemoryRepo(r)
    uc = UpdateRestaurantUseCase(repo)  # type: ignore[arg-type]

    result = await uc.execute(
        r.id.value,
        UpdateRestaurantDTO(
            menu_url="https://novo.com/menu",
            automation_type=3,
            integration_type=1,
            is_active=False,
        ),
    )

    assert isinstance(result, Success)
    assert result.value.menu_url == "https://novo.com/menu"
    assert result.value.automation_type == 3
    assert result.value.integration_type == 1
    assert result.value.is_active is False


@pytest.mark.asyncio
async def test_update_agent_config_clears_when_empty_dict():
    r = _make_restaurant()
    r.update_agent_config(AgentPersonaConfig(attendant_name="Pedro"))
    repo = _InMemoryRepo(r)
    uc = UpdateRestaurantUseCase(repo)  # type: ignore[arg-type]

    result = await uc.execute(r.id.value, UpdateRestaurantDTO(agent_config={}))

    assert isinstance(result, Success)
    assert result.value.agent_config == {}


@pytest.mark.asyncio
async def test_update_agent_config_partial():
    r = _make_restaurant()
    repo = _InMemoryRepo(r)
    uc = UpdateRestaurantUseCase(repo)  # type: ignore[arg-type]

    result = await uc.execute(
        r.id.value,
        UpdateRestaurantDTO(agent_config={"attendant_name": "Ana", "persona_style": "informal"}),
    )

    assert isinstance(result, Success)
    assert result.value.agent_config == {
        "attendant_name": "Ana",
        "persona_style": "informal",
    }


@pytest.mark.asyncio
async def test_update_not_found():
    repo = _InMemoryRepo(None)
    uc = UpdateRestaurantUseCase(repo)  # type: ignore[arg-type]

    result = await uc.execute(uuid4(), UpdateRestaurantDTO(name="X"))

    assert isinstance(result, Failure)
    assert "not found" in str(result.error).lower()


@pytest.mark.asyncio
async def test_update_rejects_invalid_name():
    r = _make_restaurant()
    repo = _InMemoryRepo(r)
    uc = UpdateRestaurantUseCase(repo)  # type: ignore[arg-type]

    result = await uc.execute(r.id.value, UpdateRestaurantDTO(name="AB"))

    assert isinstance(result, Failure)


@pytest.mark.asyncio
async def test_update_rejects_invalid_url():
    r = _make_restaurant()
    repo = _InMemoryRepo(r)
    uc = UpdateRestaurantUseCase(repo)  # type: ignore[arg-type]

    result = await uc.execute(r.id.value, UpdateRestaurantDTO(menu_url="ftp://x.com"))

    assert isinstance(result, Failure)


@pytest.mark.asyncio
async def test_update_no_fields_is_noop():
    r = _make_restaurant()
    repo = _InMemoryRepo(r)
    uc = UpdateRestaurantUseCase(repo)  # type: ignore[arg-type]

    result = await uc.execute(r.id.value, UpdateRestaurantDTO())

    assert isinstance(result, Success)
    assert result.value.name == "Original Name"
