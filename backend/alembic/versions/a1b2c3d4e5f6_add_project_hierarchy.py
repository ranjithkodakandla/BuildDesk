"""add_project_hierarchy

Phase 1 migration: Flexible Project Hierarchy

Revision ID: a1b2c3d4e5f6
Revises: d38eab03b1d1
Create Date: 2026-05-29

Changes:
    1. ALTER TABLE projects: add client_name, material, issue_date, description,
                                  address, status, hierarchy_config, updated_at
       (all new columns are nullable or have defaults — ZERO RISK to existing rows)

    2. CREATE TABLE buildings
    3. CREATE TABLE floors
    4. CREATE TABLE unit_types
    5. CREATE TABLE units

Downgrade: drops all new tables, drops new columns from projects.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# ---------------------------------------------------------------------------
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'd38eab03b1d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on:    Union[str, Sequence[str], None] = None
# ---------------------------------------------------------------------------


def upgrade() -> None:
    # ── 1. Extend projects table (additive only) ────────────────────────────
    with op.batch_alter_table('projects') as batch_op:
        batch_op.add_column(sa.Column('client_name',      sa.String(300),   nullable=True,  server_default=None))
        batch_op.add_column(sa.Column('material',         sa.String(500),   nullable=True,  server_default=None))
        batch_op.add_column(sa.Column('issue_date',       sa.Date(),        nullable=True,  server_default=None))
        batch_op.add_column(sa.Column('description',      sa.Text(),        nullable=True,  server_default=None))
        batch_op.add_column(sa.Column('address',          sa.String(500),   nullable=True,  server_default=None))
        batch_op.add_column(sa.Column('status',           sa.String(50),    nullable=False, server_default='draft'))
        batch_op.add_column(sa.Column('hierarchy_config', sa.JSON(),        nullable=True,  server_default=None))
        batch_op.add_column(sa.Column('updated_at',       sa.DateTime(timezone=True), nullable=True, server_default=None))

    # ── 2. Create buildings ─────────────────────────────────────────────────
    op.create_table(
        'buildings',
        sa.Column('id',         sa.String(36),              nullable=False),
        sa.Column('project_id', sa.String(36),              nullable=False),
        sa.Column('tenant_id',  sa.String(36),              nullable=False),
        sa.Column('name',       sa.String(200),             nullable=False),
        sa.Column('code',       sa.String(20),              nullable=True),
        sa.Column('sort_order', sa.Integer(),               nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
        sa.ForeignKeyConstraint(['tenant_id'],  ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
        if_not_exists=True,
    )

    # ── 3. Create floors ────────────────────────────────────────────────────
    op.create_table(
        'floors',
        sa.Column('id',          sa.String(36),              nullable=False),
        sa.Column('project_id',  sa.String(36),              nullable=False),
        sa.Column('building_id', sa.String(36),              nullable=False),
        sa.Column('tenant_id',   sa.String(36),              nullable=False),
        sa.Column('name',        sa.String(200),             nullable=False),
        sa.Column('number',      sa.Integer(),               nullable=True),
        sa.Column('sort_order',  sa.Integer(),               nullable=False, server_default='0'),
        sa.Column('created_at',  sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at',  sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['project_id'],  ['projects.id']),
        sa.ForeignKeyConstraint(['building_id'], ['buildings.id']),
        sa.ForeignKeyConstraint(['tenant_id'],   ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
        if_not_exists=True,
    )

    # ── 4. Create unit_types ─────────────────────────────────────────────────
    op.create_table(
        'unit_types',
        sa.Column('id',           sa.String(36),              nullable=False),
        sa.Column('project_id',   sa.String(36),              nullable=False),
        sa.Column('tenant_id',    sa.String(36),              nullable=False),
        sa.Column('code',         sa.String(50),              nullable=False),
        sa.Column('name',         sa.String(200),             nullable=False),
        sa.Column('description',  sa.Text(),                  nullable=True),
        sa.Column('is_mirror',    sa.Boolean(),               nullable=False, server_default='false'),
        sa.Column('is_ada',       sa.Boolean(),               nullable=False, server_default='false'),
        sa.Column('base_type_id', sa.String(36),              nullable=True),
        sa.Column('sort_order',   sa.Integer(),               nullable=False, server_default='0'),
        sa.Column('created_at',   sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at',   sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['project_id'],   ['projects.id']),
        sa.ForeignKeyConstraint(['tenant_id'],    ['tenants.id']),
        sa.ForeignKeyConstraint(['base_type_id'], ['unit_types.id']),
        sa.PrimaryKeyConstraint('id'),
        if_not_exists=True,
    )

    # ── 5. Create units ──────────────────────────────────────────────────────
    op.create_table(
        'units',
        sa.Column('id',           sa.String(36),              nullable=False),
        sa.Column('project_id',   sa.String(36),              nullable=False),
        sa.Column('tenant_id',    sa.String(36),              nullable=False),
        sa.Column('building_id',  sa.String(36),              nullable=True),
        sa.Column('floor_id',     sa.String(36),              nullable=True),
        sa.Column('unit_type_id', sa.String(36),              nullable=True),
        sa.Column('name',         sa.String(200),             nullable=False),
        sa.Column('code',         sa.String(50),              nullable=False),
        sa.Column('variant',      sa.String(20),              nullable=False, server_default='standard'),
        sa.Column('notes',        sa.Text(),                  nullable=True),
        sa.Column('sort_order',   sa.Integer(),               nullable=False, server_default='0'),
        sa.Column('created_at',   sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at',   sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['project_id'],   ['projects.id']),
        sa.ForeignKeyConstraint(['tenant_id'],    ['tenants.id']),
        sa.ForeignKeyConstraint(['building_id'],  ['buildings.id']),
        sa.ForeignKeyConstraint(['floor_id'],     ['floors.id']),
        sa.ForeignKeyConstraint(['unit_type_id'], ['unit_types.id']),
        sa.PrimaryKeyConstraint('id'),
        if_not_exists=True,
    )



def downgrade() -> None:
    op.drop_table('units')
    op.drop_table('unit_types')
    op.drop_table('floors')
    op.drop_table('buildings')

    with op.batch_alter_table('projects') as batch_op:
        batch_op.drop_column('updated_at')
        batch_op.drop_column('hierarchy_config')
        batch_op.drop_column('status')
        batch_op.drop_column('address')
        batch_op.drop_column('description')
        batch_op.drop_column('issue_date')
        batch_op.drop_column('material')
        batch_op.drop_column('client_name')
