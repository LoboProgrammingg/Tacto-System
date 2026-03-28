"""Restaurant entities."""

from tacto.domain.restaurant.entities.integration import (
    Integration,
    IntegrationCredentials,
)
from tacto.domain.restaurant.entities.restaurant import Restaurant

__all__ = [
    "Restaurant",
    "Integration",
    "IntegrationCredentials",
]
