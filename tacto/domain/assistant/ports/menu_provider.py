"""
Menu Provider Port (Interface).

Defines the contract for fetching menu data.
Implementation fetches from Tacto API or cache.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

from tacto.domain.shared.result import Failure, Success
from tacto.domain.shared.value_objects import RestaurantId


@dataclass(frozen=True, slots=True)
class MenuItem:
    """A single menu item."""

    name: str
    description: Optional[str]
    price: float
    category: str
    is_available: bool = True

    def to_embed_content(self) -> str:
        """Text to embed — name + description only, NO price."""
        parts = [self.name]
        if self.category:
            parts.append(f"Categoria: {self.category}")
        if self.description:
            parts.append(self.description)
        return " | ".join(parts)

    def to_context_text(self) -> str:
        """Text to pass as AI context — name + description, NO price."""
        if self.description:
            return f"{self.name}: {self.description}"
        return self.name


@dataclass(frozen=True, slots=True)
class MenuData:
    """Complete menu data for a restaurant."""

    restaurant_id: RestaurantId
    items: list[MenuItem]
    categories: list[str]
    raw_text: str
    last_updated: str
    address: Optional[str] = None
    hours_text: str = ""
    restaurant_description: str = ""


@dataclass(frozen=True, slots=True)
class InstitutionalData:
    """Institutional data for a restaurant."""

    restaurant_id: RestaurantId
    name: str
    address: Optional[str]
    phone: Optional[str]
    payment_methods: list[str]
    delivery_info: Optional[str]
    raw_text: str


class MenuProvider(ABC):
    """
    Abstract interface for menu and institutional data provider.

    This port allows the domain to fetch restaurant data
    without knowing the specific source (Tacto API, cache, etc.).
    """

    @abstractmethod
    async def get_menu(
        self,
        restaurant_id: RestaurantId,
        empresa_base_id: Optional[str] = None,
        grupo_empresarial: Optional[str] = None,
    ) -> Success[MenuData] | Failure[Exception]:
        """
        Get menu data for a restaurant.

        Args:
            restaurant_id: The restaurant to get menu for
            empresa_base_id: Tacto company ID (avoids extra DB lookup if known)
            grupo_empresarial: Tacto group key (avoids extra DB lookup if known)

        Returns:
            Success with MenuData or Failure with error
        """
        pass

    @abstractmethod
    async def get_institutional_data(
        self,
        restaurant_id: RestaurantId,
        empresa_base_id: Optional[str] = None,
        grupo_empresarial: Optional[str] = None,
    ) -> Success[InstitutionalData] | Failure[Exception]:
        """
        Get institutional data for a restaurant.

        Args:
            restaurant_id: The restaurant to get data for
            empresa_base_id: Tacto company ID (avoids extra DB lookup if known)
            grupo_empresarial: Tacto group key (avoids extra DB lookup if known)

        Returns:
            Success with InstitutionalData or Failure with error
        """
        pass

    @abstractmethod
    async def search_menu(
        self,
        restaurant_id: RestaurantId,
        query: str,
        limit: int = 5,
    ) -> Success[list[MenuItem]] | Failure[Exception]:
        """
        Search menu items by query.

        Args:
            restaurant_id: The restaurant to search in
            query: Search query
            limit: Maximum results

        Returns:
            Success with matching items or Failure with error
        """
        pass
