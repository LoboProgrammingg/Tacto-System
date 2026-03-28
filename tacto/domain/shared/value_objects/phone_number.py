"""
Phone Number Value Object.

Represents a validated phone number in international format.
"""

from __future__ import annotations

import re
from typing import Any

from tacto.domain.shared.exceptions import ValidationError
from tacto.domain.shared.value_objects.base import ValueObject


class PhoneNumber(ValueObject):
    """
    Value Object representing a phone number.

    Stores phone numbers in normalized format (digits only).
    Validates Brazilian phone numbers (10-11 digits) by default.
    """

    __slots__ = ("_value", "_country_code")

    PHONE_PATTERN = re.compile(r"^\d{10,15}$")
    BRAZIL_PATTERN = re.compile(r"^55\d{10,11}$")

    def __init__(
        self,
        value: str,
        country_code: str = "55",
    ) -> None:
        """
        Initialize phone number.

        Args:
            value: Phone number (can include formatting characters)
            country_code: Country code (default: 55 for Brazil)
        """
        normalized = self._normalize(value)

        if not normalized.startswith(country_code):
            normalized = country_code + normalized

        self._value = normalized
        self._country_code = country_code
        super().__init__()

    @staticmethod
    def _normalize(value: str) -> str:
        """Remove all non-digit characters from phone number."""
        return re.sub(r"\D", "", value)

    def _validate(self) -> None:
        """Validate phone number format."""
        if not self.PHONE_PATTERN.match(self._value):
            raise ValidationError(
                message=f"Invalid phone number format: {self._value}",
                field="phone_number",
                value=self._value,
            )

        if self._country_code == "55" and not self.BRAZIL_PATTERN.match(self._value):
            raise ValidationError(
                message=f"Invalid Brazilian phone number: {self._value}",
                field="phone_number",
                value=self._value,
            )

    def _get_equality_components(self) -> tuple[Any, ...]:
        """Return normalized value for equality comparison."""
        return (self._value,)

    @property
    def value(self) -> str:
        """Get normalized phone number (digits only)."""
        return self._value

    @property
    def country_code(self) -> str:
        """Get country code."""
        return self._country_code

    @property
    def local_number(self) -> str:
        """Get phone number without country code."""
        if self._value.startswith(self._country_code):
            return self._value[len(self._country_code) :]
        return self._value

    @property
    def formatted(self) -> str:
        """Get formatted phone number for display."""
        local = self.local_number
        if len(local) == 11:
            return f"+{self._country_code} ({local[:2]}) {local[2:7]}-{local[7:]}"
        elif len(local) == 10:
            return f"+{self._country_code} ({local[:2]}) {local[2:6]}-{local[6:]}"
        return f"+{self._country_code} {local}"

    @property
    def whatsapp_format(self) -> str:
        """Get phone number in WhatsApp format (with @c.us suffix)."""
        return f"{self._value}@c.us"

    def __str__(self) -> str:
        """Return normalized phone number."""
        return self._value

    def __repr__(self) -> str:
        """Return detailed representation."""
        return f"PhoneNumber('{self._value}')"

    @classmethod
    def from_whatsapp(cls, whatsapp_id: str) -> "PhoneNumber":
        """
        Create PhoneNumber from WhatsApp ID format.

        Args:
            whatsapp_id: Phone in format "5511999999999@c.us"
        """
        phone = whatsapp_id.replace("@c.us", "").replace("@s.whatsapp.net", "")
        return cls(phone)
