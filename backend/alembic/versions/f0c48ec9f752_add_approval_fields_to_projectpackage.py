"""Add approval fields to ProjectPackage

Revision ID: f0c48ec9f752
Revises: 32db6b454627
Create Date: 2026-05-29 17:24:41.593991

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f0c48ec9f752'
down_revision: Union[str, Sequence[str], None] = '32db6b454627'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('project_packages', sa.Column('approved_by', sa.String(length=200), nullable=True))
    op.add_column('project_packages', sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('project_packages', sa.Column('review_notes', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('project_packages', 'review_notes')
    op.drop_column('project_packages', 'approved_at')
    op.drop_column('project_packages', 'approved_by')
