"""Add agent_config column to restaurants table.

Revision ID: 006_agent_persona_config
Revises: 005_hnsw_index
Create Date: 2026-04-01

Adds agent_config JSONB column to store per-restaurant AI persona overrides
(attendant_name, attendant_gender, persona_style, max_emojis_per_message).

Empty dict ({}) means "use platform defaults from env vars".
This enables each restaurant to have a different AI attendant identity
without requiring a new deployment.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from alembic import op

revision: str = "006_agent_persona_config"
down_revision: Union[str, None] = "005_hnsw_index"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add agent_config column to restaurants table."""
    op.add_column(
        "restaurants",
        sa.Column(
            "agent_config",
            JSONB,
            nullable=False,
            server_default="'{}'::jsonb",
        ),
    )


def downgrade() -> None:
    """Remove agent_config column from restaurants table."""
    op.drop_column("restaurants", "agent_config")
