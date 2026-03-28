"""Add customer_memories table for long-term AI memory.

Revision ID: 002_memories
Revises: 001_initial
Create Date: 2026-03-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "002_memories"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "customer_memories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("restaurant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("customer_phone", sa.String(20), nullable=False, index=True),
        sa.Column("memory_key", sa.String(100), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("extra_data", postgresql.JSONB, nullable=True),
        sa.Column("relevance_score", sa.Float, default=1.0),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_index(
        "idx_customer_memories_restaurant_phone",
        "customer_memories",
        ["restaurant_id", "customer_phone"],
    )

    op.execute("""
        CREATE TRIGGER update_customer_memories_updated_at
            BEFORE UPDATE ON customer_memories
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS update_customer_memories_updated_at ON customer_memories")
    op.drop_table("customer_memories")
