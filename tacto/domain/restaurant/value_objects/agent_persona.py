"""
AgentPersonaConfig Value Object.

Holds per-restaurant AI attendant persona configuration.
Each field is Optional — None means "use the platform default from env vars".

This enables a two-layer config system:
  Layer 1 (platform): env vars (ATTENDANT_NAME, ATTENDANT_GENDER, ...)
  Layer 2 (per-restaurant): this VO stored as JSONB in the restaurants table

Merge rule: restaurant_override if set, else platform_default.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


_VALID_GENDERS = frozenset({"feminino", "masculino", "neutro"})
_VALID_STYLES = frozenset({"formal", "informal"})


@dataclass(frozen=True)
class AgentPersonaConfig:
    """
    Per-restaurant AI persona configuration.

    All fields are Optional. None = defer to platform default (env var).
    Only set a field when the restaurant needs to override the platform default.

    Invariants:
    - attendant_name, when set, must be at least 2 characters
    - attendant_gender must be "feminino", "masculino", or "neutro"
    - persona_style must be "formal" or "informal"
    - max_emojis_per_message must be between 0 and 5
    """

    attendant_name: Optional[str] = None
    attendant_gender: Optional[str] = None
    persona_style: Optional[str] = None
    max_emojis_per_message: Optional[int] = None

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if self.attendant_name is not None and len(self.attendant_name.strip()) < 2:
            raise ValueError("attendant_name must have at least 2 characters")
        if self.attendant_gender is not None and self.attendant_gender not in _VALID_GENDERS:
            raise ValueError(f"attendant_gender must be one of: {sorted(_VALID_GENDERS)}")
        if self.persona_style is not None and self.persona_style not in _VALID_STYLES:
            raise ValueError(f"persona_style must be one of: {sorted(_VALID_STYLES)}")
        if self.max_emojis_per_message is not None and not (0 <= self.max_emojis_per_message <= 5):
            raise ValueError("max_emojis_per_message must be between 0 and 5")

    # -------------------------------------------------------------------------
    # Effective value resolvers — apply platform default when field is None
    # -------------------------------------------------------------------------

    def effective_attendant_name(self, platform_default: str) -> str:
        """Return restaurant-specific name, or platform default."""
        return self.attendant_name or platform_default

    def effective_gender(self, platform_default: str = "feminino") -> str:
        """Return restaurant-specific gender, or platform default."""
        return self.attendant_gender or platform_default

    def effective_persona_style(self, platform_default: str = "formal") -> str:
        """Return restaurant-specific style, or platform default."""
        return self.persona_style or platform_default

    def effective_max_emojis(self, platform_default: int = 1) -> int:
        """Return restaurant-specific emoji limit, or platform default."""
        if self.max_emojis_per_message is not None:
            return self.max_emojis_per_message
        return platform_default

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialize to dict for JSONB storage. Omits None values."""
        result: dict = {}
        if self.attendant_name is not None:
            result["attendant_name"] = self.attendant_name
        if self.attendant_gender is not None:
            result["attendant_gender"] = self.attendant_gender
        if self.persona_style is not None:
            result["persona_style"] = self.persona_style
        if self.max_emojis_per_message is not None:
            result["max_emojis_per_message"] = self.max_emojis_per_message
        return result

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> "AgentPersonaConfig":
        """Deserialize from JSONB dict. None or empty dict = all platform defaults."""
        if not data:
            return cls()
        return cls(
            attendant_name=data.get("attendant_name"),
            attendant_gender=data.get("attendant_gender"),
            persona_style=data.get("persona_style"),
            max_emojis_per_message=data.get("max_emojis_per_message"),
        )

    @classmethod
    def empty(cls) -> "AgentPersonaConfig":
        """Config with no overrides — all fields defer to platform defaults."""
        return cls()
