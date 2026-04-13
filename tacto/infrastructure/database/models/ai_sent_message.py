"""
AiSentMessage SQLAlchemy Model.

Outbox persistente para rastrear mensagens enviadas pela IA.
Substitui o Redis como única fonte de verdade para detecção de echo.
Redis continua sendo usado como cache rápido (TTL curto).
Banco é a verdade absoluta (persiste entre restarts e quedas do Redis).
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from tacto.infrastructure.database.models.base import Base


class AiSentMessageModel(Base):
    """Outbox de mensagens enviadas pela IA."""

    __tablename__ = "ai_sent_messages"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    instance_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    phone: Mapped[str] = mapped_column(String(50), nullable=False)
    message_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    __table_args__ = (
        Index("ix_ai_sent_messages_instance_phone_sent", "instance_key", "phone", "sent_at"),
        Index("ix_ai_sent_messages_instance_msg_id", "instance_key", "message_id"),
    )
