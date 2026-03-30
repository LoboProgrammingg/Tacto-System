"""Add timezone field to restaurants table.

Revision ID: 004_restaurant_timezone
Revises: 003_menu_embeddings
Create Date: 2026-03-28

Adds timezone column to restaurants table to support restaurant-specific
timezone handling for open/close checks instead of server UTC time.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_restaurant_timezone"
down_revision: Union[str, None] = "003_menu_embeddings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add timezone column to restaurants table."""
    op.add_column(
        "restaurants",
        sa.Column(
            "timezone",
            sa.String(63),
            nullable=False,
            server_default="America/Cuiaba",
        ),
    )


def downgrade() -> None:
    """Remove timezone column from restaurants table."""
    op.drop_column("restaurants", "timezone")
