"""
Restaurant SQLAlchemy Model.
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from tacto.infrastructure.database.models.base import Base, TimestampMixin


class RestaurantModel(Base, TimestampMixin):
    """SQLAlchemy model for restaurants table."""

    __tablename__ = "restaurants"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    prompt_default: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    menu_url: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )

    opening_hours: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )

    integration_type: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=2,
    )

    automation_type: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    chave_grupo_empresarial: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    canal_master_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )

    empresa_base_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    timezone: Mapped[str] = mapped_column(
        String(63),
        nullable=False,
        default="America/Cuiaba",
    )

    agent_config: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="'{}'::jsonb",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    def __repr__(self) -> str:
        return f"<Restaurant(id={self.id}, name='{self.name}')>"
