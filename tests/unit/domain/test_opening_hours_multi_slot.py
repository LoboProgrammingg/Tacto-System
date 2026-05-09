"""Tests for OpeningHours multi-slot support (Atos Peixaria scenario).

Atos Peixaria stores hours as:
    {"friday": {"periods": [["11:00", "15:00"], ["18:00", "22:00"]]}, ...}

Without multi-slot support, from_dict raised ValidationError and the AI
stopped responding for that restaurant.
"""

from datetime import time

import pytest

from tacto.domain.restaurant.value_objects.opening_hours import (
    DaySchedule,
    OpeningHours,
)
from tacto.shared.domain.exceptions import ValidationError


class TestDayScheduleMultiSlot:
    def test_from_dict_reads_periods_format(self):
        """Multi-slot dict format must produce a schedule with primary + extras."""
        schedule = DaySchedule.from_dict(
            {"periods": [["11:00", "15:00"], ["18:00", "22:00"]]}
        )

        assert schedule.opens_at == time(11, 0)
        assert schedule.closes_at == time(15, 0)
        assert len(schedule.extra_periods) == 1
        assert schedule.extra_periods[0] == (time(18, 0), time(22, 0))

    def test_from_dict_legacy_single_slot_still_works(self):
        """Legacy single-slot format must keep working unchanged."""
        schedule = DaySchedule.from_dict({"opens_at": "09:00", "closes_at": "18:00"})

        assert schedule.opens_at == time(9, 0)
        assert schedule.closes_at == time(18, 0)
        assert schedule.extra_periods == ()

    def test_from_dict_empty_periods_returns_closed(self):
        schedule = DaySchedule.from_dict({"periods": []})
        assert schedule.is_closed is True

    def test_is_open_at_checks_all_slots(self):
        """is_open_at must return True if any slot covers the time."""
        schedule = DaySchedule.from_dict(
            {"periods": [["11:00", "15:00"], ["18:00", "22:00"]]}
        )

        assert schedule.is_open_at(time(12, 0)) is True   # in lunch slot
        assert schedule.is_open_at(time(16, 0)) is False  # between slots
        assert schedule.is_open_at(time(20, 0)) is True   # in dinner slot
        assert schedule.is_open_at(time(23, 0)) is False  # after both

    def test_is_open_at_exclusive_upper_bound(self):
        """Closing time itself is NOT open (exclusive)."""
        schedule = DaySchedule.from_dict(
            {"periods": [["11:00", "15:00"], ["18:00", "22:00"]]}
        )
        assert schedule.is_open_at(time(15, 0)) is False
        assert schedule.is_open_at(time(14, 59)) is True

    def test_to_dict_emits_periods_when_multi_slot(self):
        schedule = DaySchedule.from_dict(
            {"periods": [["11:00", "15:00"], ["18:00", "22:00"]]}
        )
        assert schedule.to_dict() == {
            "periods": [["11:00", "15:00"], ["18:00", "22:00"]]
        }

    def test_to_dict_emits_legacy_when_single_slot(self):
        """Backward-compat: single slot stays in old shape so existing JSONB rows are preserved."""
        schedule = DaySchedule.from_dict({"opens_at": "09:00", "closes_at": "18:00"})
        assert schedule.to_dict() == {"opens_at": "09:00", "closes_at": "18:00"}

    def test_closed_day_with_extra_periods_raises(self):
        with pytest.raises(ValidationError):
            DaySchedule(is_closed=True, extra_periods=((time(11, 0), time(15, 0)),))

    def test_formatted_hours_joins_all_slots(self):
        schedule = DaySchedule.from_dict(
            {"periods": [["11:00", "15:00"], ["18:00", "22:00"]]}
        )
        assert schedule.formatted_hours == "11:00 às 15:00 / 18:00 às 22:00"


class TestOpeningHoursAtosPeixariaScenario:
    """Reproduce the exact JSONB shape stored for Atos Peixaria in production."""

    ATOS_HOURS = {
        "friday": {"periods": [["11:00", "15:00"], ["11:00", "14:00"], ["18:00", "22:00"]]},
        "sunday": {"periods": [["11:00", "14:00"], ["11:00", "15:00"], ["18:00", "22:00"]]},
        "tuesday": {"periods": [["11:00", "15:00"], ["18:00", "22:00"]]},
        "saturday": {"periods": [["11:00", "15:00"], ["18:00", "22:00"]]},
        "thursday": {"periods": [["11:00", "15:00"], ["14:00", "22:00"]]},
        "wednesday": {"periods": [["11:00", "15:00"], ["18:00", "22:00"]]},
        # monday absent → defaults to closed
    }

    def test_atos_peixaria_loads_without_validation_error(self):
        """The exact production payload must round-trip through from_dict."""
        hours = OpeningHours.from_dict(self.ATOS_HOURS)
        assert hours.monday.is_closed is True

        # Tuesday: lunch + dinner
        assert hours.tuesday.opens_at == time(11, 0)
        assert hours.tuesday.closes_at == time(15, 0)
        assert hours.tuesday.extra_periods == ((time(18, 0), time(22, 0)),)

        # Friday: 3 slots (production has duplicates — must not crash)
        assert len(hours.friday.extra_periods) == 2

    def test_atos_peixaria_is_open_at_lunch_and_dinner(self):
        """Verify the multi-slot evaluation matches business reality."""
        hours = OpeningHours.from_dict(self.ATOS_HOURS)

        assert hours.tuesday.is_open_at(time(12, 30)) is True  # lunch
        assert hours.tuesday.is_open_at(time(16, 0)) is False  # gap
        assert hours.tuesday.is_open_at(time(20, 0)) is True   # dinner

    def test_atos_peixaria_round_trip_to_dict(self):
        """to_dict for multi-slot day must produce the periods key for re-storage."""
        hours = OpeningHours.from_dict(self.ATOS_HOURS)
        round_trip = hours.tuesday.to_dict()
        assert "periods" in round_trip
        assert round_trip["periods"][0] == ["11:00", "15:00"]
