"""Tests for OpeningHours.is_defined() — the fail-open data-presence check."""

from tacto.domain.restaurant.value_objects.opening_hours import (
    DaySchedule,
    OpeningHours,
)


def _all_closed() -> OpeningHours:
    return OpeningHours.from_dict({})


def _one_open_day() -> OpeningHours:
    return OpeningHours(
        monday=DaySchedule.open("11:00", "23:00"),
        tuesday=DaySchedule.closed(),
        wednesday=DaySchedule.closed(),
        thursday=DaySchedule.closed(),
        friday=DaySchedule.closed(),
        saturday=DaySchedule.closed(),
        sunday=DaySchedule.closed(),
    )


class TestOpeningHoursIsDefined:
    """is_defined() distinguishes "we have hours data" from "no data at all"."""

    def test_all_days_closed_is_not_defined(self):
        """An all-closed schedule means no reliable data → not defined (fail-open)."""
        assert _all_closed().is_defined() is False

    def test_at_least_one_open_day_is_defined(self):
        """Any open day means we have real hours data → defined."""
        assert _one_open_day().is_defined() is True

    def test_full_week_open_is_defined(self):
        assert OpeningHours.all_day_every_day().is_defined() is True


class TestNextOpeningIncludesDate:
    """get_next_opening must show the explicit date next to the weekday."""

    def test_tomorrow_includes_weekday_and_date(self):
        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo

        tz = "America/Cuiaba"
        now = datetime.now(ZoneInfo(tz))
        tomorrow = now + timedelta(days=1)
        # Only tomorrow's weekday is open, at a time already past for today.
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        schedule = {d: {"is_closed": True} for d in days}
        schedule[days[tomorrow.weekday()]] = {"opens_at": "00:01", "closes_at": "23:59"}
        oh = OpeningHours.from_dict(schedule)

        text = oh.get_next_opening(tz)
        assert "amanhã" in text
        assert f"({tomorrow.strftime('%d/%m')})" in text

    def test_later_day_includes_date(self):
        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo

        tz = "America/Cuiaba"
        now = datetime.now(ZoneInfo(tz))
        target = now + timedelta(days=3)
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        schedule = {d: {"is_closed": True} for d in days}
        schedule[days[target.weekday()]] = {"opens_at": "00:01", "closes_at": "23:59"}
        oh = OpeningHours.from_dict(schedule)

        text = oh.get_next_opening(tz)
        assert f"({target.strftime('%d/%m')})" in text
        assert "amanhã" not in text
