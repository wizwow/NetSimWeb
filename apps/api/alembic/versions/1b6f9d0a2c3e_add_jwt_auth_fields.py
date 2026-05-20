"""Add JWT auth fields

Revision ID: 1b6f9d0a2c3e
Revises: 835c9c5917f0
Create Date: 2026-05-20 13:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "1b6f9d0a2c3e"
down_revision: Union[str, Sequence[str], None] = "835c9c5917f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(), nullable=True))
    op.add_column(
        "users",
        sa.Column("account_tier", sa.String(), nullable=False, server_default="free"),
    )
    op.add_column(
        "users",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
    )
    op.alter_column("users", "account_tier", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "updated_at")
    op.drop_column("users", "account_tier")
    op.drop_column("users", "password_hash")
