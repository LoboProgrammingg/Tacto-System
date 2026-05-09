from datetime import datetime
from zoneinfo import ZoneInfo

from tacto.domain.restaurant.value_objects.opening_hours import DayOfWeek, OpeningHours


class TestOpeningHoursTimezone:
    """Ensure 'today' helpers respect the restaurant timezone."""

    def test_get_today_hours_uses_requested_timezone(self, monkeypatch):
        opening_hours = OpeningHours.from_dict(
            {
                "monday": {"opens_at": "08:00", "closes_at": "18:00"},
                "tuesday": {"opens_at": "09:00", "closes_at": "19:00"},
                "wednesday": {"opens_at": "10:00", "closes_at": "20:00"},
                "thursday": {"opens_at": "11:00", "closes_at": "21:00"},
                "friday": {"opens_at": "12:00", "closes_at": "22:00"},
                "saturday": {"opens_at": "13:00", "closes_at": "23:00"},
                "sunday": {"is_closed": True},
            }
        )

        class FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 5, 2, 9, 30, tzinfo=tz or ZoneInfo("America/Cuiaba"))

        monkeypatch.setattr(
            "tacto.domain.restaurant.value_objects.opening_hours.datetime",
            FixedDateTime,
        )

        assert DayOfWeek.today("America/Cuiaba") == DayOfWeek.SATURDAY
        assert opening_hours.get_today_hours("America/Cuiaba") == "13:00 às 23:00"
