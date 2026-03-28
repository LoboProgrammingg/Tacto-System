"""Initial schema with restaurants, conversations, and messages.

Revision ID: 001_initial
Revises: 
Create Date: 2026-03-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    op.create_table(
        "restaurants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("prompt_default", sa.Text, nullable=False),
        sa.Column("menu_url", sa.String(512), nullable=False),
        sa.Column("opening_hours", postgresql.JSONB, nullable=False),
        sa.Column("integration_type", sa.Integer, nullable=False, server_default="2"),
        sa.Column("automation_type", sa.Integer, nullable=False, server_default="1"),
        sa.Column("chave_grupo_empresarial", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("canal_master_id", sa.String(255), nullable=False, unique=True),
        sa.Column("empresa_base_id", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index("idx_restaurants_canal_master_id", "restaurants", ["canal_master_id"])
    op.create_index("idx_restaurants_is_active", "restaurants", ["is_active"])
    op.create_index("idx_restaurants_chave_grupo", "restaurants", ["chave_grupo_empresarial"])

    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("restaurant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("customer_phone", sa.String(20), nullable=False),
        sa.Column("customer_name", sa.String(255), nullable=True),
        sa.Column("is_ai_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("ai_disabled_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ai_disabled_reason", sa.String(100), nullable=True),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_index("idx_conversations_restaurant_id", "conversations", ["restaurant_id"])
    op.create_index("idx_conversations_customer_phone", "conversations", ["customer_phone"])
    op.create_index("idx_conversations_last_message", "conversations", ["last_message_at"])
    op.create_unique_constraint("uq_conversations_restaurant_phone", "conversations", ["restaurant_id", "customer_phone"])

    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("direction", sa.String(20), nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("from_me", sa.Boolean, nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("media_url", sa.String(512), nullable=True),
        sa.Column("media_type", sa.String(50), nullable=True),
        sa.Column("metadata_", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_index("idx_messages_conversation_id", "messages", ["conversation_id"])
    op.create_index("idx_messages_timestamp", "messages", ["timestamp"])
    op.create_index("idx_messages_external_id", "messages", ["external_id"])

    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)

    op.execute("""
        CREATE TRIGGER update_restaurants_updated_at
            BEFORE UPDATE ON restaurants
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)

    op.execute("""
        CREATE TRIGGER update_conversations_updated_at
            BEFORE UPDATE ON conversations
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS update_conversations_updated_at ON conversations")
    op.execute("DROP TRIGGER IF EXISTS update_restaurants_updated_at ON restaurants")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")

    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("restaurants")
