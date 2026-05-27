"""Settings for the Streamlit onboarding UI.

All configuration comes from environment variables (optionally loaded from
a local `.env` file). No secrets are hardcoded here.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).parent / ".env")


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _optional(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


@dataclass(frozen=True)
class Settings:
    api_base_url: str
    api_key: str
    join_api_base_url: str
    join_token_cliente: str
    webhook_url: str
    auth_email: str
    auth_password: str


def get_settings() -> Settings:
    return Settings(
        api_base_url=_optional("API_BASE_URL", "http://localhost:8000").rstrip("/"),
        api_key=_require("API_KEY"),
        join_api_base_url=_optional(
            "JOIN_API_BASE_URL", "https://api-prd.joindeveloper.com.br"
        ).rstrip("/"),
        join_token_cliente=_require("JOIN_TOKEN_CLIENTE"),
        webhook_url=_optional(
            "WEBHOOK_URL", "http://65.21.240.57:8000/api/v1/webhook/join/"
        ),
        auth_email=_require("AUTH_EMAIL"),
        auth_password=_require("AUTH_PASSWORD"),
    )
