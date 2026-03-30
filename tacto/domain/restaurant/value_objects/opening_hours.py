"""
OpeningHours Value Object.

Represents the operating hours for a restaurant across all days of the week.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from enum import Enum
from typing import Any, Optional
from zoneinfo import ZoneInfo

from tacto.shared.domain.exceptions import ValidationError


class DayOfWeek(str, Enum):
    """Days of the week."""

    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"

    @classmethod
    def from_datetime(cls, dt: datetime) -> "DayOfWeek":
        """Get day of week from datetime."""
        days = list(cls)
        return days[dt.weekday()]

    @classmethod
    def today(cls) -> "DayOfWeek":
        """Get current day of week."""
        return cls.from_datetime(datetime.now())


@dataclass(frozen=True, slots=True)
class DaySchedule:
    """
    Schedule for a single day.

    Can be either:
    - Open with specific hours (opens_at, closes_at)
    - Closed for the day (is_closed=True)
    """

    opens_at: Optional[time] = None
    closes_at: Optional[time] = None
    is_closed: bool = False

    def __post_init__(self) -> None:
        """Validate schedule invariants."""
        if self.is_closed:
            if self.opens_at is not None or self.closes_at is not None:
                raise ValidationError(
                    message="Closed day cannot have opening hours",
                    field="is_closed",
                )
        else:
            if self.opens_at is None or self.closes_at is None:
                raise ValidationError(
                    message="Open day must have both opens_at and closes_at",
                    field="opens_at",
                )

    def is_open_at(self, check_time: time) -> bool:
        """Check if restaurant is open at given time."""
        if self.is_closed:
            return False

        if self.opens_at is None or self.closes_at is None:
            return False

        if self.closes_at < self.opens_at:
            return check_time >= self.opens_at or check_time < self.closes_at
        return self.opens_at <= check_time < self.closes_at

    @property
    def formatted_hours(self) -> str:
        """Get formatted hours string."""
        if self.is_closed:
            return "Fechado"
        if self.opens_at and self.closes_at:
            return f"{self.opens_at.strftime('%H:%M')} às {self.closes_at.strftime('%H:%M')}"
        return "Horário não definido"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        if self.is_closed:
            return {"is_closed": True}
        return {
            "opens_at": self.opens_at.strftime("%H:%M") if self.opens_at else None,
            "closes_at": self.closes_at.strftime("%H:%M") if self.closes_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DaySchedule":
        """Create from dictionary."""
        if data.get("is_closed"):
            return cls(is_closed=True)

        opens_at = None
        closes_at = None

        if data.get("opens_at"):
            opens_at = datetime.strptime(data["opens_at"], "%H:%M").time()
        if data.get("closes_at"):
            closes_at = datetime.strptime(data["closes_at"], "%H:%M").time()

        return cls(opens_at=opens_at, closes_at=closes_at)

    @classmethod
    def closed(cls) -> "DaySchedule":
        """Create a closed day schedule."""
        return cls(is_closed=True)

    @classmethod
    def open(cls, opens_at: str, closes_at: str) -> "DaySchedule":
        """Create an open day schedule from time strings."""
        return cls(
            opens_at=datetime.strptime(opens_at, "%H:%M").time(),
            closes_at=datetime.strptime(closes_at, "%H:%M").time(),
        )


@dataclass(frozen=True, slots=True)
class OpeningHours:
    """
    Complete weekly schedule for a restaurant.

    Immutable value object containing schedule for all 7 days.
    """

    monday: DaySchedule
    tuesday: DaySchedule
    wednesday: DaySchedule
    thursday: DaySchedule
    friday: DaySchedule
    saturday: DaySchedule
    sunday: DaySchedule

    def get_schedule(self, day: DayOfWeek) -> DaySchedule:
        """Get schedule for specific day."""
        schedules = {
            DayOfWeek.MONDAY: self.monday,
            DayOfWeek.TUESDAY: self.tuesday,
            DayOfWeek.WEDNESDAY: self.wednesday,
            DayOfWeek.THURSDAY: self.thursday,
            DayOfWeek.FRIDAY: self.friday,
            DayOfWeek.SATURDAY: self.saturday,
            DayOfWeek.SUNDAY: self.sunday,
        }
        return schedules[day]

    def is_open_now(self, tz: str = "America/Cuiaba") -> bool:
        """Check if restaurant is currently open in the given timezone."""
        now = datetime.now(ZoneInfo(tz))
        today = DayOfWeek.from_datetime(now)
        schedule = self.get_schedule(today)
        return schedule.is_open_at(now.time())

    def get_today_hours(self) -> str:
        """Get formatted hours for today only."""
        today = DayOfWeek.today()
        schedule = self.get_schedule(today)
        return schedule.formatted_hours

    def get_next_opening(self, tz: str = "America/Cuiaba") -> str:
        """
        Get humanized string for next opening time.

        Returns strings like:
        - "Abrimos hoje às 18:00"
        - "Abrimos amanhã, segunda-feira, às 11:00"
        """
        from datetime import timedelta

        now = datetime.now(ZoneInfo(tz))
        day_name_pt = {
            DayOfWeek.MONDAY: "segunda-feira",
            DayOfWeek.TUESDAY: "terça-feira",
            DayOfWeek.WEDNESDAY: "quarta-feira",
            DayOfWeek.THURSDAY: "quinta-feira",
            DayOfWeek.FRIDAY: "sexta-feira",
            DayOfWeek.SATURDAY: "sábado",
            DayOfWeek.SUNDAY: "domingo",
        }

        # Check next 8 days
        for days_ahead in range(8):
            check_date = now + timedelta(days=days_ahead)
            day_of_week = DayOfWeek.from_datetime(check_date)
            schedule = self.get_schedule(day_of_week)

            if not schedule.is_closed and schedule.opens_at:
                time_str = schedule.opens_at.strftime("%H:%M")

                if days_ahead == 0:
                    return f"Abrimos hoje às {time_str}"
                elif days_ahead == 1:
                    return f"Abrimos amanhã, {day_name_pt[day_of_week]}, às {time_str}"
                else:
                    return f"Abrimos {day_name_pt[day_of_week]} às {time_str}"

        # Fallback if no opening found
        return "Consulte nossos horários de funcionamento"

    def get_next_opening_utc(self, tz: str = "America/Cuiaba") -> Optional[datetime]:
        """
        Return the UTC datetime of the next restaurant opening.

        Used to calculate when to re-enable AI after a restaurant_closed disable.
        Returns None if no opening is found within the next 8 days.
        """
        from datetime import timedelta, timezone as dt_timezone

        local_tz = ZoneInfo(tz)
        now = datetime.now(local_tz)

        for days_ahead in range(8):
            check_date = now + timedelta(days=days_ahead)
            day_of_week = DayOfWeek.from_datetime(check_date)
            schedule = self.get_schedule(day_of_week)

            if schedule.is_closed or not schedule.opens_at:
                continue

            # Build a timezone-aware datetime for the opening in the restaurant's local tz
            opening_local = check_date.replace(
                hour=schedule.opens_at.hour,
                minute=schedule.opens_at.minute,
                second=0,
                microsecond=0,
                tzinfo=local_tz,
            )

            # Skip openings that are already in the past
            if opening_local <= now:
                continue

            return opening_local.astimezone(dt_timezone.utc)

        return None

    def get_today_schedule(self) -> DaySchedule:
        """Get schedule for today."""
        today = DayOfWeek.today()
        return self.get_schedule(today)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON storage."""
        return {
            "monday": self.monday.to_dict(),
            "tuesday": self.tuesday.to_dict(),
            "wednesday": self.wednesday.to_dict(),
            "thursday": self.thursday.to_dict(),
            "friday": self.friday.to_dict(),
            "saturday": self.saturday.to_dict(),
            "sunday": self.sunday.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OpeningHours":
        """Create from dictionary."""
        return cls(
            monday=DaySchedule.from_dict(data.get("monday", {"is_closed": True})),
            tuesday=DaySchedule.from_dict(data.get("tuesday", {"is_closed": True})),
            wednesday=DaySchedule.from_dict(data.get("wednesday", {"is_closed": True})),
            thursday=DaySchedule.from_dict(data.get("thursday", {"is_closed": True})),
            friday=DaySchedule.from_dict(data.get("friday", {"is_closed": True})),
            saturday=DaySchedule.from_dict(data.get("saturday", {"is_closed": True})),
            sunday=DaySchedule.from_dict(data.get("sunday", {"is_closed": True})),
        )

    @classmethod
    def all_day_every_day(cls) -> "OpeningHours":
        """Create 24/7 schedule."""
        schedule = DaySchedule.open("00:00", "23:59")
        return cls(
            monday=schedule,
            tuesday=schedule,
            wednesday=schedule,
            thursday=schedule,
            friday=schedule,
            saturday=schedule,
            sunday=schedule,
        )
