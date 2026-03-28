"""Add menu_embeddings table for RAG vector search.

Revision ID: 003_menu_embeddings
Revises: 002_memories
Create Date: 2026-03-28

Creates the pgvector table that stores Gemini embeddings per menu item,
isolated by restaurant_id. Used for semantic search during message processing.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003_menu_embeddings"
down_revision: Union[str, None] = "002_memories"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ensure extensions exist (idempotent — safe on existing DBs)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    op.execute("""
        CREATE TABLE IF NOT EXISTS menu_embeddings (
            id            UUID         NOT NULL DEFAULT uuid_generate_v4(),
            restaurant_id UUID         NOT NULL,
            content       TEXT         NOT NULL,
            embedding     vector(768)  NOT NULL,
            metadata      JSONB,
            created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

            CONSTRAINT menu_embeddings_pkey PRIMARY KEY (id),
            CONSTRAINT menu_embeddings_restaurant_id_fkey
                FOREIGN KEY (restaurant_id) REFERENCES restaurants(id) ON DELETE CASCADE
        )
    """)

    # IVFFlat index for fast approximate cosine similarity search
    # lists=100 is appropriate for up to ~1M rows (rule of thumb: sqrt(rows))
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_menu_embeddings_restaurant
            ON menu_embeddings (restaurant_id)
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_menu_embeddings_vector
            ON menu_embeddings USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
    """)

    # Auto-update updated_at on row changes
    op.execute("""
        CREATE OR REPLACE FUNCTION update_menu_embeddings_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)

    op.execute("""
        DROP TRIGGER IF EXISTS trg_menu_embeddings_updated_at ON menu_embeddings
    """)

    op.execute("""
        CREATE TRIGGER trg_menu_embeddings_updated_at
            BEFORE UPDATE ON menu_embeddings
            FOR EACH ROW EXECUTE FUNCTION update_menu_embeddings_updated_at()
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_menu_embeddings_updated_at ON menu_embeddings")
    op.execute("DROP FUNCTION IF EXISTS update_menu_embeddings_updated_at()")
    op.execute("DROP TABLE IF EXISTS menu_embeddings")
