"""add_fabrication_domain

Phase 2 migration: Fabrication Assembly Model

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-29

Changes:
    1. CREATE TABLE assemblies
    2. CREATE TABLE fabrication_notes
    3. CREATE TABLE parts
    4. CREATE TABLE splashes
    5. CREATE TABLE cutouts
    6. CREATE TABLE holes
    7. CREATE TABLE edge_treatments

Downgrade: drops all new tables.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# ---------------------------------------------------------------------------
revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on:    Union[str, Sequence[str], None] = None
# ---------------------------------------------------------------------------


def upgrade() -> None:
    # ── 1. Create assemblies ────────────────────────────────────────────────
    op.create_table(
        'assemblies',
        sa.Column('id',            sa.String(36),              nullable=False),
        sa.Column('project_id',    sa.String(36),              nullable=False),
        sa.Column('tenant_id',     sa.String(36),              nullable=False),
        sa.Column('unit_id',       sa.String(36),              nullable=True),
        sa.Column('unit_type_id',  sa.String(36),              nullable=True),
        sa.Column('name',          sa.String(200),             nullable=False),
        sa.Column('assembly_type', sa.String(50),              nullable=False),
        sa.Column('variant',       sa.String(20),              nullable=False, server_default='standard'),
        sa.Column('created_at',    sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at',    sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['project_id'],   ['projects.id']),
        sa.ForeignKeyConstraint(['tenant_id'],    ['tenants.id']),
        sa.ForeignKeyConstraint(['unit_id'],      ['units.id']),
        sa.ForeignKeyConstraint(['unit_type_id'], ['unit_types.id']),
        sa.PrimaryKeyConstraint('id'),
        if_not_exists=True,
    )

    # ── 2. Create fabrication_notes ─────────────────────────────────────────
    op.create_table(
        'fabrication_notes',
        sa.Column('id',          sa.String(36),              nullable=False),
        sa.Column('assembly_id', sa.String(36),              nullable=False),
        sa.Column('content',     sa.Text(),                  nullable=False),
        sa.Column('created_at',  sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['assembly_id'], ['assemblies.id']),
        sa.PrimaryKeyConstraint('id'),
        if_not_exists=True,
    )

    # ── 3. Create parts ─────────────────────────────────────────────────────
    op.create_table(
        'parts',
        sa.Column('id',            sa.String(36),              nullable=False),
        sa.Column('assembly_id',   sa.String(36),              nullable=False),
        sa.Column('part_type',     sa.String(50),              nullable=False),
        sa.Column('name',          sa.String(100),             nullable=False),
        sa.Column('dim_length',    sa.Float(),                 nullable=False),
        sa.Column('dim_depth',     sa.Float(),                 nullable=False),
        sa.Column('dim_thickness', sa.Float(),                 nullable=True),
        sa.Column('notes',         sa.Text(),                  nullable=True),
        sa.Column('created_at',    sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['assembly_id'], ['assemblies.id']),
        sa.PrimaryKeyConstraint('id'),
        if_not_exists=True,
    )

    # ── 4. Create splashes ──────────────────────────────────────────────────
    op.create_table(
        'splashes',
        sa.Column('id',            sa.String(36),              nullable=False),
        sa.Column('part_id',       sa.String(36),              nullable=False),
        sa.Column('splash_type',   sa.String(50),              nullable=False),
        sa.Column('dim_length',    sa.Float(),                 nullable=False),
        sa.Column('dim_depth',     sa.Float(),                 nullable=False),
        sa.Column('dim_thickness', sa.Float(),                 nullable=True),
        sa.Column('notes',         sa.Text(),                  nullable=True),
        sa.Column('created_at',    sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['part_id'], ['parts.id']),
        sa.PrimaryKeyConstraint('id'),
        if_not_exists=True,
    )

    # ── 5. Create cutouts ───────────────────────────────────────────────────
    op.create_table(
        'cutouts',
        sa.Column('id',            sa.String(36),              nullable=False),
        sa.Column('part_id',       sa.String(36),              nullable=False),
        sa.Column('cutout_type',   sa.String(50),              nullable=False),
        sa.Column('mount_type',    sa.String(50),              nullable=False, server_default='none'),
        sa.Column('center_x',      sa.Float(),                 nullable=False),
        sa.Column('center_y',      sa.Float(),                 nullable=False),
        sa.Column('dim_length',    sa.Float(),                 nullable=False),
        sa.Column('dim_depth',     sa.Float(),                 nullable=False),
        sa.Column('dim_thickness', sa.Float(),                 nullable=True),
        sa.Column('notes',         sa.Text(),                  nullable=True),
        sa.Column('created_at',    sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['part_id'], ['parts.id']),
        sa.PrimaryKeyConstraint('id'),
        if_not_exists=True,
    )

    # ── 6. Create holes ─────────────────────────────────────────────────────
    op.create_table(
        'holes',
        sa.Column('id',          sa.String(36),              nullable=False),
        sa.Column('part_id',     sa.String(36),              nullable=False),
        sa.Column('diameter',    sa.Float(),                 nullable=False),
        sa.Column('center_x',    sa.Float(),                 nullable=False),
        sa.Column('center_y',    sa.Float(),                 nullable=False),
        sa.Column('purpose',     sa.String(100),             nullable=False),
        sa.Column('created_at',  sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['part_id'], ['parts.id']),
        sa.PrimaryKeyConstraint('id'),
        if_not_exists=True,
    )

    # ── 7. Create edge_treatments ───────────────────────────────────────────
    op.create_table(
        'edge_treatments',
        sa.Column('id',          sa.String(36),              nullable=False),
        sa.Column('part_id',     sa.String(36),              nullable=False),
        sa.Column('position',    sa.String(50),              nullable=False),
        sa.Column('edge_type',   sa.String(50),              nullable=False, server_default='eased'),
        sa.Column('length',      sa.Float(),                 nullable=True),
        sa.Column('notes',       sa.Text(),                  nullable=True),
        sa.Column('created_at',  sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['part_id'], ['parts.id']),
        sa.PrimaryKeyConstraint('id'),
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_table('edge_treatments')
    op.drop_table('holes')
    op.drop_table('cutouts')
    op.drop_table('splashes')
    op.drop_table('parts')
    op.drop_table('fabrication_notes')
    op.drop_table('assemblies')
