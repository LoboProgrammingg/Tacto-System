"""
005 - HNSW Index for menu_embeddings.

Replaces IVFFlat with HNSW for better recall and no training requirement.
HNSW (Hierarchical Navigable Small World) provides:
- Better accuracy than IVFFlat
- No need for VACUUM before creating
- Automatic index updates on INSERT

Requires: pgvector >= 0.5.0

Revision ID: 005_hnsw_index
Revises: 004_restaurant_timezone
Create Date: 2026-03-29
"""

from alembic import op


revision = "005_hnsw_index"
down_revision = "004_restaurant_timezone"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Replace IVFFlat index with HNSW for better performance."""
    # Drop existing IVFFlat index
    op.execute("DROP INDEX IF EXISTS idx_menu_embeddings_vector")

    # Create HNSW index with cosine similarity
    # m=16: connections per layer (default, good balance)
    # ef_construction=64: quality of index construction
    op.execute("""
        CREATE INDEX idx_menu_embeddings_vector
            ON menu_embeddings USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64)
    """)


def downgrade() -> None:
    """Revert to IVFFlat index."""
    op.execute("DROP INDEX IF EXISTS idx_menu_embeddings_vector")

    # Recreate IVFFlat index
    op.execute("""
        CREATE INDEX idx_menu_embeddings_vector
            ON menu_embeddings USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
    """)
