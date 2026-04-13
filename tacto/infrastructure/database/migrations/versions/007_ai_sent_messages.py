"""Add ai_sent_messages outbox table.

Revision ID: 007_ai_sent_messages
Revises: 006_agent_persona_config
Create Date: 2026-04-13

Persistent outbox for tracking AI-sent messages.
Enables robust echo detection with DB fallback when Redis is down.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "007_ai_sent_messages"
down_revision: Union[str, None] = "006_agent_persona_config"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_sent_messages",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("instance_key", sa.String(100), nullable=False),
        sa.Column("phone", sa.String(50), nullable=False),
        sa.Column("message_id", sa.String(255), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("message_text", sa.Text, nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ai_sent_messages_instance_key", "ai_sent_messages", ["instance_key"])
    op.create_index("ix_ai_sent_messages_message_id", "ai_sent_messages", ["message_id"])
    op.create_index(
        "ix_ai_sent_messages_instance_phone_sent",
        "ai_sent_messages", ["instance_key", "phone", "sent_at"],
    )
    op.create_index(
        "ix_ai_sent_messages_instance_msg_id",
        "ai_sent_messages", ["instance_key", "message_id"],
    )
    # Cleanup function for old records (>24h) — call via cron or scheduled task
    op.execute("""
        CREATE OR REPLACE FUNCTION cleanup_ai_sent_messages()
        RETURNS void AS $$
        BEGIN
            DELETE FROM ai_sent_messages WHERE sent_at < NOW() - INTERVAL '24 hours';
        END;
        $$ LANGUAGE plpgsql;
    """)


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS cleanup_ai_sent_messages();")
    op.drop_table("ai_sent_messages")
