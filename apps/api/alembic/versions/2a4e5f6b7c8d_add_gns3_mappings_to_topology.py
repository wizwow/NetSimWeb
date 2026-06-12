"""Add gns3_mappings to topologies

Revision ID: 2a4e5f6b7c8d
Revises: 1b6f9d0a2c3e
Create Date: 2026-06-12 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "2a4e5f6b7c8d"
down_revision: Union[str, Sequence[str], None] = "1b6f9d0a2c3e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add a nullable JSONB column for Octet <-> GNS3 id mappings.

    The column is nullable so existing rows survive without backfill; new
    topologies will populate it on the first ``POST /topology/{id}/start``
    call when the simulation engine returns id mappings.
    """
    op.add_column(
        "topologies",
        sa.Column(
            "gns3_mappings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Remove the gns3_mappings column from topologies."""
    op.drop_column("topologies", "gns3_mappings")
