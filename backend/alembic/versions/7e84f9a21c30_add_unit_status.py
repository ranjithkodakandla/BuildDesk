"""Add unit status for bulk operations

Revision ID: 7e84f9a21c30
Revises: 6d73ee7338cb
Create Date: 2026-05-29 18:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7e84f9a21c30"
down_revision: Union[str, Sequence[str], None] = "6d73ee7338cb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "units",
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
    )


def downgrade() -> None:
    op.drop_column("units", "status")
