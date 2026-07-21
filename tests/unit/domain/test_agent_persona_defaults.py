"""Tests for gender-aware attendant name defaults (never empty)."""

from tacto.domain.restaurant.value_objects.agent_persona import AgentPersonaConfig


class TestEffectiveAttendantName:
    def test_restaurant_override_wins(self):
        p = AgentPersonaConfig(attendant_name="Bell", attendant_gender="feminino")
        assert p.effective_attendant_name("Maria") == "Bell"

    def test_platform_default_when_no_override(self):
        p = AgentPersonaConfig()
        assert p.effective_attendant_name("Clara") == "Clara"

    def test_empty_everything_feminine_falls_back_to_maria(self):
        p = AgentPersonaConfig(attendant_gender="feminino")
        assert p.effective_attendant_name("") == "Maria"

    def test_empty_everything_masculine_falls_back_to_jose(self):
        p = AgentPersonaConfig(attendant_gender="masculino")
        assert p.effective_attendant_name("") == "José"

    def test_explicit_gender_beats_generic_platform_default(self):
        """Restaurant chose masculine (no name): José, not the platform's Maria."""
        p = AgentPersonaConfig(attendant_gender="masculino")
        assert p.effective_attendant_name("Maria") == "José"

    def test_no_gender_defaults_to_maria(self):
        p = AgentPersonaConfig()
        assert p.effective_attendant_name("") == "Maria"

    def test_whitespace_platform_default_is_treated_as_empty(self):
        p = AgentPersonaConfig(attendant_gender="masculino")
        assert p.effective_attendant_name("   ") == "José"

    def test_chosen_name_kept_even_with_masculine_gender(self):
        """Choosing a name always wins — gender only drives the fallback."""
        p = AgentPersonaConfig(attendant_name="Carlos", attendant_gender="masculino")
        assert p.effective_attendant_name("Maria") == "Carlos"
