"""Add tenant branding fields

Revision ID: 6d73ee7338cb
Revises: 6943694a3ec1
Create Date: 2026-05-29 17:34:01.667792

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6d73ee7338cb'
down_revision: Union[str, Sequence[str], None] = '6943694a3ec1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('tenants', sa.Column('company_name', sa.String(length=255), nullable=True))
    op.add_column('tenants', sa.Column('logo_url', sa.String(length=1000), nullable=True))
    op.add_column('tenants', sa.Column('default_footer', sa.String(length=500), nullable=True))
    op.add_column('tenants', sa.Column('standard_notes', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('tenants', 'standard_notes')
    op.drop_column('tenants', 'default_footer')
    op.drop_column('tenants', 'logo_url')
    op.drop_column('tenants', 'company_name')
