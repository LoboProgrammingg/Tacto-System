"""
Integration Tests for RestaurantRepository.

Tests repository operations against real PostgreSQL database.
"""

from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from tacto.infrastructure.database.models.restaurant import RestaurantModel
from tacto.infrastructure.persistence.restaurant_repository import PostgresRestaurantRepository
from tacto.domain.restaurant.entities.restaurant import Restaurant
from tacto.domain.restaurant.value_objects.opening_hours import OpeningHours
from tacto.domain.restaurant.value_objects.integration_type import IntegrationType
from tacto.domain.restaurant.value_objects.automation_type import AutomationType
from tacto.shared.domain.value_objects import RestaurantId


class TestRestaurantRepositoryIntegration:
    """Integration tests for RestaurantRepository."""

    @pytest.mark.asyncio
    async def test_find_by_canal_master_id(
        self,
        db_session: AsyncSession,
        sample_restaurant: RestaurantModel,
    ):
        """Should find restaurant by canal_master_id."""
        repo = PostgresRestaurantRepository(db_session)

        result = await repo.find_by_canal_master_id(sample_restaurant.canal_master_id)

        assert result is not None
        assert result.name == sample_restaurant.name
        assert result.canal_master_id == sample_restaurant.canal_master_id

    @pytest.mark.asyncio
    async def test_find_by_canal_master_id_not_found(
        self,
        db_session: AsyncSession,
    ):
        """Should return None when restaurant not found."""
        repo = PostgresRestaurantRepository(db_session)

        result = await repo.find_by_canal_master_id("non_existent_id")

        assert result is None

    @pytest.mark.asyncio
    async def test_find_by_id(
        self,
        db_session: AsyncSession,
        sample_restaurant: RestaurantModel,
    ):
        """Should find restaurant by ID."""
        repo = PostgresRestaurantRepository(db_session)

        result = await repo.find_by_id(RestaurantId(sample_restaurant.id))

        assert result is not None
        assert result.id.value == sample_restaurant.id

    @pytest.mark.asyncio
    async def test_find_active_restaurants(
        self,
        db_session: AsyncSession,
        sample_restaurant: RestaurantModel,
    ):
        """Should return list of active restaurants."""
        repo = PostgresRestaurantRepository(db_session)

        results = await repo.find_active(limit=10)

        assert len(results) >= 1
        assert any(r.id.value == sample_restaurant.id for r in results)

    @pytest.mark.asyncio
    async def test_save_new_restaurant(
        self,
        db_session: AsyncSession,
    ):
        """Should save new restaurant to database."""
        repo = PostgresRestaurantRepository(db_session)

        restaurant = Restaurant(
            id=RestaurantId(uuid4()),
            name="Novo Restaurante Teste",
            prompt_default="Você é a atendente do Novo Restaurante.",
            menu_url="https://novo.cardapio.com",
            opening_hours=OpeningHours.from_dict({
                "monday": {"opens_at": "10:00", "closes_at": "22:00"},
                "tuesday": {"opens_at": "10:00", "closes_at": "22:00"},
            }),
            integration_type=IntegrationType.JOIN,
            automation_type=AutomationType.BASIC,
            chave_grupo_empresarial=uuid4(),
            canal_master_id="novo_restaurante_teste",
            empresa_base_id="2",
            timezone="America/Sao_Paulo",
        )

        saved = await repo.save(restaurant)

        assert saved.id == restaurant.id
        # Verify it's actually in database
        found = await repo.find_by_id(restaurant.id)
        assert found is not None
        assert found.name == "Novo Restaurante Teste"

    @pytest.mark.asyncio
    async def test_update_existing_restaurant(
        self,
        db_session: AsyncSession,
        sample_restaurant: RestaurantModel,
    ):
        """Should update existing restaurant."""
        repo = PostgresRestaurantRepository(db_session)

        # Load restaurant
        restaurant = await repo.find_by_id(RestaurantId(sample_restaurant.id))
        assert restaurant is not None

        # Update name
        restaurant.name = "Restaurante Atualizado"

        # Save
        saved = await repo.save(restaurant)

        # Verify update
        found = await repo.find_by_id(restaurant.id)
        assert found.name == "Restaurante Atualizado"


class TestRestaurantRepositoryEdgeCases:
    """Edge case tests for RestaurantRepository."""

    @pytest.mark.asyncio
    async def test_find_inactive_restaurant(
        self,
        db_session: AsyncSession,
    ):
        """Inactive restaurants should not be found by find_active."""
        # Create inactive restaurant
        inactive = RestaurantModel(
            id=uuid4(),
            name="Restaurante Inativo",
            prompt_default="Prompt",
            menu_url="https://cardapio.com",
            opening_hours={},
            integration_type=2,
            automation_type=1,
            chave_grupo_empresarial=uuid4(),
            canal_master_id="restaurante_inativo",
            empresa_base_id="1",
            timezone="America/Sao_Paulo",
            is_active=False,
        )
        db_session.add(inactive)
        await db_session.flush()

        repo = PostgresRestaurantRepository(db_session)
        results = await repo.find_active(limit=100)

        assert not any(r.id.value == inactive.id for r in results)

    @pytest.mark.asyncio
    async def test_opening_hours_mapping(
        self,
        db_session: AsyncSession,
        sample_restaurant: RestaurantModel,
    ):
        """Opening hours should be correctly mapped to domain object."""
        repo = PostgresRestaurantRepository(db_session)

        restaurant = await repo.find_by_id(RestaurantId(sample_restaurant.id))

        assert restaurant is not None
        hours = restaurant.opening_hours
        assert hours.monday is not None
        assert not hours.monday.is_closed
        assert hours.sunday.is_closed
