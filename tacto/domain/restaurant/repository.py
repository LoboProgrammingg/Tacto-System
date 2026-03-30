"""
Repository Interface for Restaurant Aggregate.

Defines the contract for Restaurant persistence operations.
Implementation is in infrastructure layer.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional

from tacto.domain.restaurant.entities.restaurant import Restaurant
from tacto.shared.application import Failure, Success
from tacto.shared.domain.value_objects import RestaurantId


class RestaurantRepository(ABC):
    """
    Abstract repository for Restaurant aggregate.

    This interface defines the contract for persistence operations.
    Concrete implementations are in the infrastructure layer.

    Following DDD principles:
    - Repository operates on aggregate roots only
    - Returns Result types for explicit error handling
    - No infrastructure concerns leak into domain
    """

    @abstractmethod
    async def save(self, restaurant: Restaurant) -> Success[Restaurant] | Failure[Exception]:
        """
        Persist a restaurant (create or update).

        Args:
            restaurant: The restaurant aggregate to persist

        Returns:
            Success with saved restaurant or Failure with error
        """
        pass

    @abstractmethod
    async def find_by_id(
        self, restaurant_id: RestaurantId
    ) -> Success[Optional[Restaurant]] | Failure[Exception]:
        """
        Find restaurant by its ID.

        Args:
            restaurant_id: The restaurant's unique identifier

        Returns:
            Success with restaurant (or None if not found) or Failure with error
        """
        pass

    @abstractmethod
    async def find_by_canal_master_id(
        self, canal_master_id: str
    ) -> Success[Optional[Restaurant]] | Failure[Exception]:
        """
        Find restaurant by canal master ID (Join/WhatsApp integration ID).

        This is used to identify the tenant from incoming webhooks.

        Args:
            canal_master_id: The integration channel ID

        Returns:
            Success with restaurant (or None if not found) or Failure with error
        """
        pass

    @abstractmethod
    async def find_all_active(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> Success[list[Restaurant]] | Failure[Exception]:
        """
        Find all active restaurants with pagination.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            Success with list of restaurants or Failure with error
        """
        pass

    @abstractmethod
    async def exists_by_name(self, name: str) -> Success[bool] | Failure[Exception]:
        """
        Check if a restaurant with given name exists.

        Args:
            name: Restaurant name to check

        Returns:
            Success with boolean or Failure with error
        """
        pass

    @abstractmethod
    async def update_canal_master_id(
        self, restaurant_id: RestaurantId, canal_master_id: str
    ) -> Success[bool] | Failure[Exception]:
        """
        Update the canal_master_id (Join instance key) for a restaurant.

        Used to associate a WhatsApp instance with a restaurant for
        multi-tenant webhook routing.

        Args:
            restaurant_id: The restaurant's unique identifier
            canal_master_id: The Join instance key (e.g. 'wp-empresa-7')

        Returns:
            Success with True if updated or Failure with error
        """
        pass

    @abstractmethod
    async def update_opening_hours(
        self, restaurant_id: RestaurantId, opening_hours: dict[str, Any]
    ) -> Success[bool] | Failure[Exception]:
        """
        Update the opening_hours for a restaurant.

        Used by tacto-sync to persist hours fetched from Tacto API.
        """
        pass

    @abstractmethod
    async def delete(
        self, restaurant_id: RestaurantId
    ) -> Success[bool] | Failure[Exception]:
        """
        Soft delete a restaurant.

        Args:
            restaurant_id: The restaurant's unique identifier

        Returns:
            Success with True if deleted or Failure with error
        """
        pass
