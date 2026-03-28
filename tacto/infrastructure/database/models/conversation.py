"""
Conversation SQLAlchemy Model.
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tacto.infrastructure.database.models.base import Base, TimestampMixin


class ConversationModel(Base, TimestampMixin):
    """SQLAlchemy model for conversations table."""

    __tablename__ = "conversations"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
    )

    restaurant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    customer_phone: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    customer_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    is_ai_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    ai_disabled_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    ai_disabled_reason: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    last_message_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    metadata_: Mapped[Optional[dict[str, Any]]] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, phone='{self.customer_phone}')>"
