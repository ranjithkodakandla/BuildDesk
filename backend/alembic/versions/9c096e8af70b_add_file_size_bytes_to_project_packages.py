"""add file_size_bytes to project_packages

Revision ID: 9c096e8af70b
Revises: c3d4e5f6g7h8
Create Date: 2026-05-29 14:55:01.723547

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c096e8af70b'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6g7h8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('project_packages', sa.Column('file_size_bytes', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('project_packages', 'file_size_bytes')
