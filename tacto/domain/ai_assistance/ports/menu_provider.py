"""
Menu Provider Port.

SHIM: Re-exports from tacto.application.ports.menu_provider for backward compatibility.
"""

from tacto.application.ports.menu_provider import (
    InstitutionalData,
    MenuData,
    MenuItem,
    MenuProvider,
)

__all__ = ["InstitutionalData", "MenuData", "MenuItem", "MenuProvider"]
