"""Tests for the Brazilian state (UF) → IANA timezone mapping."""

from zoneinfo import ZoneInfo

import pytest

from tacto.domain.restaurant.value_objects.timezone_br import (
    BR_UF_TIMEZONES,
    timezone_for_uf,
)


class TestTimezoneForUf:
    """timezone_for_uf resolves a Brazilian state code to an IANA timezone."""

    def test_all_27_states_are_mapped(self):
        """Every Brazilian state + DF must have a timezone."""
        expected = {
            "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
            "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
            "RS", "RO", "RR", "SC", "SP", "SE", "TO",
        }
        assert set(BR_UF_TIMEZONES) == expected

    def test_every_mapped_zone_is_a_valid_iana_zone(self):
        """Each mapped value must load as a real IANA timezone."""
        for uf, tz in BR_UF_TIMEZONES.items():
            assert ZoneInfo(tz) is not None, f"invalid zone for {uf}: {tz}"

    @pytest.mark.parametrize(
        "uf,expected",
        [
            ("SP", "America/Sao_Paulo"),
            ("RJ", "America/Sao_Paulo"),
            ("MT", "America/Cuiaba"),
            ("MS", "America/Campo_Grande"),
            ("AM", "America/Manaus"),
            ("AC", "America/Rio_Branco"),
            ("PE", "America/Recife"),
            ("BA", "America/Bahia"),
        ],
    )
    def test_known_states(self, uf: str, expected: str):
        assert timezone_for_uf(uf) == expected

    def test_is_case_insensitive_and_trims(self):
        assert timezone_for_uf(" sp ") == "America/Sao_Paulo"
        assert timezone_for_uf("Rj") == "America/Sao_Paulo"

    def test_unknown_uf_returns_none(self):
        assert timezone_for_uf("XX") is None

    def test_empty_or_none_returns_none(self):
        assert timezone_for_uf("") is None
        assert timezone_for_uf(None) is None
