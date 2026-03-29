"""
PostgreSQL Restaurant Repository Implementation.

Implements the RestaurantRepository interface from the domain layer.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from tacto.domain.restaurant.entities.restaurant import Restaurant
from tacto.domain.restaurant.repository import RestaurantRepository
from tacto.domain.restaurant.value_objects.automation_type import AutomationType
from tacto.domain.restaurant.value_objects.integration_type import IntegrationType
from tacto.domain.restaurant.value_objects.opening_hours import OpeningHours
from tacto.shared.domain.exceptions import EntityNotFoundError
from tacto.shared.application import Err, Failure, Ok, Success
from tacto.shared.domain.value_objects import RestaurantId
from tacto.infrastructure.database.models.restaurant import RestaurantModel


class PostgresRestaurantRepository(RestaurantRepository):
    """
    PostgreSQL implementation of RestaurantRepository.

    Handles persistence of Restaurant aggregates using SQLAlchemy.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self._session = session

    async def save(
        self, restaurant: Restaurant
    ) -> Success[Restaurant] | Failure[Exception]:
        """Persist a restaurant aggregate."""
        try:
            model = self._to_model(restaurant)

            existing = await self._session.get(RestaurantModel, restaurant.id.value)

            if existing:
                for key, value in model.__dict__.items():
                    if not key.startswith("_"):
                        setattr(existing, key, value)
            else:
                self._session.add(model)

            await self._session.flush()
            return Ok(restaurant)

        except Exception as e:
            return Err(e)

    async def find_by_id(
        self, restaurant_id: RestaurantId
    ) -> Success[Optional[Restaurant]] | Failure[Exception]:
        """Find restaurant by ID."""
        try:
            model = await self._session.get(RestaurantModel, restaurant_id.value)

            if model is None:
                return Ok(None)

            return Ok(self._to_entity(model))

        except Exception as e:
            return Err(e)

    async def find_by_canal_master_id(
        self, canal_master_id: str
    ) -> Success[Optional[Restaurant]] | Failure[Exception]:
        """Find restaurant by canal_master_id (WhatsApp instance key)."""
        try:
            stmt = select(RestaurantModel).where(
                RestaurantModel.canal_master_id == canal_master_id,
                RestaurantModel.deleted_at.is_(None),
            )
            result = await self._session.execute(stmt)
            model = result.scalar_one_or_none()

            if model is None:
                return Ok(None)

            return Ok(self._to_entity(model))

        except Exception as e:
            return Err(e)

    async def find_all_active(
        self, limit: int = 100, offset: int = 0
    ) -> Success[list[Restaurant]] | Failure[Exception]:
        """Find all active restaurants."""
        try:
            stmt = (
                select(RestaurantModel)
                .where(
                    RestaurantModel.is_active == True,
                    RestaurantModel.deleted_at.is_(None),
                )
                .order_by(RestaurantModel.name)
                .limit(limit)
                .offset(offset)
            )
            result = await self._session.execute(stmt)
            models = result.scalars().all()

            return Ok([self._to_entity(m) for m in models])

        except Exception as e:
            return Err(e)

    async def find_by_grupo_empresarial(
        self, chave_grupo: UUID
    ) -> Success[list[Restaurant]] | Failure[Exception]:
        """Find all restaurants in a business group."""
        try:
            stmt = (
                select(RestaurantModel)
                .where(
                    RestaurantModel.chave_grupo_empresarial == chave_grupo,
                    RestaurantModel.deleted_at.is_(None),
                )
                .order_by(RestaurantModel.name)
            )
            result = await self._session.execute(stmt)
            models = result.scalars().all()

            return Ok([self._to_entity(m) for m in models])

        except Exception as e:
            return Err(e)

    async def update_canal_master_id(
        self, restaurant_id: RestaurantId, canal_master_id: str
    ) -> Success[bool] | Failure[Exception]:
        """
        Update the canal_master_id (Join instance key) for a restaurant.

        Uses a direct SQL UPDATE to avoid loading the full aggregate.
        """
        try:
            stmt = (
                update(RestaurantModel)
                .where(RestaurantModel.id == restaurant_id.value)
                .values(canal_master_id=canal_master_id)
            )
            await self._session.execute(stmt)
            await self._session.flush()
            return Ok(True)
        except Exception as e:
            return Err(e)

    async def delete(
        self, restaurant_id: RestaurantId
    ) -> Success[bool] | Failure[Exception]:
        """Soft delete a restaurant."""
        try:
            result = await self.find_by_id(restaurant_id)

            if isinstance(result, Failure):
                return result

            restaurant = result.value
            if restaurant is None:
                return Err(
                    EntityNotFoundError(
                        entity_type="Restaurant",
                        entity_id=str(restaurant_id.value),
                    )
                )

            restaurant.soft_delete()
            return await self.save(restaurant)

        except Exception as e:
            return Err(e)

    async def exists_by_name(self, name: str) -> Success[bool] | Failure[Exception]:
        """Check if a restaurant with this name already exists."""
        try:
            stmt = select(RestaurantModel).where(
                RestaurantModel.name == name,
                RestaurantModel.deleted_at.is_(None),
            )
            result = await self._session.execute(stmt)
            return Ok(result.scalar_one_or_none() is not None)
        except Exception as e:
            return Err(e)

    async def exists(
        self, restaurant_id: RestaurantId
    ) -> Success[bool] | Failure[Exception]:
        """Check if restaurant exists."""
        try:
            model = await self._session.get(RestaurantModel, restaurant_id.value)
            return Ok(model is not None and model.deleted_at is None)

        except Exception as e:
            return Err(e)

    def _to_model(self, entity: Restaurant) -> RestaurantModel:
        """Convert domain entity to SQLAlchemy model."""
        return RestaurantModel(
            id=entity.id.value,
            name=entity.name,
            prompt_default=entity.prompt_default,
            menu_url=entity.menu_url,
            opening_hours=entity.opening_hours.to_dict(),
            integration_type=entity.integration_type.value,
            automation_type=entity.automation_type.value,
            chave_grupo_empresarial=entity.chave_grupo_empresarial,
            canal_master_id=entity.canal_master_id,
            empresa_base_id=entity.empresa_base_id,
            timezone=entity.timezone,
            is_active=entity.is_active,
            deleted_at=entity.deleted_at,
        )

    def _to_entity(self, model: RestaurantModel) -> Restaurant:
        """Convert SQLAlchemy model to domain entity."""
        return Restaurant(
            id=RestaurantId(model.id),
            name=model.name,
            prompt_default=model.prompt_default,
            menu_url=model.menu_url,
            opening_hours=OpeningHours.from_dict(model.opening_hours),
            integration_type=IntegrationType(model.integration_type),
            automation_type=AutomationType(model.automation_type),
            chave_grupo_empresarial=model.chave_grupo_empresarial,
            canal_master_id=model.canal_master_id,
            empresa_base_id=model.empresa_base_id,
            timezone=model.timezone,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
        )
