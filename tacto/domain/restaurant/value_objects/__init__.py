"""Value Objects for Restaurant context."""

from tacto.domain.restaurant.value_objects.automation_type import AutomationType
from tacto.domain.restaurant.value_objects.integration_type import IntegrationType
from tacto.domain.restaurant.value_objects.opening_hours import DaySchedule, OpeningHours

__all__ = [
    "IntegrationType",
    "AutomationType",
    "OpeningHours",
    "DaySchedule",
]
