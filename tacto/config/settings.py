"""
Backward-compatibility shim.

The authoritative settings implementation lives in:
    tacto/infrastructure/config/config.py

This module re-exports everything so existing imports continue to work
without any changes across the 14 files that reference tacto.config.settings.
"""

from tacto.infrastructure.config.config import (  # noqa: F401
    AppSettings,
    DatabaseSettings,
    GeminiSettings,
    JoinAPISettings,
    LangSmithSettings,
    Level2Settings,
    RedisSettings,
    Settings,
    TactoAPISettings,
    get_settings,
)

__all__ = [
    "Settings",
    "AppSettings",
    "DatabaseSettings",
    "RedisSettings",
    "TactoAPISettings",
    "JoinAPISettings",
    "GeminiSettings",
    "LangSmithSettings",
    "Level2Settings",
    "get_settings",
]
