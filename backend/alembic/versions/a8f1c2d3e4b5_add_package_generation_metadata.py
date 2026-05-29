"""add package generation error metadata

Revision ID: a8f1c2d3e4b5
Revises: 7e84f9a21c30
Create Date: 2026-05-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a8f1c2d3e4b5"
down_revision: Union[str, None] = "7e84f9a21c30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "project_packages",
        sa.Column("generation_error", sa.Text(), nullable=True),
    )
    op.add_column(
        "project_packages",
        sa.Column("generation_attempts", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("project_packages", "generation_attempts")
    op.drop_column("project_packages", "generation_error")
