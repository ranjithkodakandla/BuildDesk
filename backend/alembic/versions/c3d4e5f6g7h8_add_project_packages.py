"""
Phase 3 — Add project_packages and package_pages tables.

ADDITIVE ONLY — no drops, no renames.
Safe to run on live Cloud SQL PostgreSQL.

Tables added:
    project_packages  — one row per generated package per project
    package_pages     — one row per page in the package PDF
"""

from alembic import op
import sqlalchemy as sa


revision = "c3d4e5f6g7h8"
down_revision = "b2c3d4e5f6g7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── project_packages ────────────────────────────────────────────────
    op.create_table(
        "project_packages",
        sa.Column("id",                sa.String(36),   nullable=False),
        sa.Column("project_id",        sa.String(36),   nullable=False),
        sa.Column("tenant_id",         sa.String(36),   nullable=False),
        sa.Column("version",           sa.String(50),   nullable=False, server_default="1.0"),
        sa.Column("issued_by",         sa.String(200),  nullable=True),
        sa.Column("issued_date",       sa.DateTime(timezone=True), nullable=True),
        sa.Column("status",            sa.String(30),   nullable=False, server_default="draft"),
        sa.Column("storage_reference", sa.String(1000), nullable=True),
        sa.Column("generated_at",      sa.DateTime(timezone=True), nullable=True),
        sa.Column("page_count",        sa.Integer(),    nullable=False, server_default="0"),
        sa.Column("created_at",        sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at",        sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["tenant_id"],  ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_project_packages_project_tenant",
                    "project_packages", ["project_id", "tenant_id"])
    op.create_index("ix_project_packages_tenant",
                    "project_packages", ["tenant_id"])

    # ── package_pages ────────────────────────────────────────────────────
    op.create_table(
        "package_pages",
        sa.Column("id",          sa.String(36),  nullable=False),
        sa.Column("package_id",  sa.String(36),  nullable=False),
        sa.Column("page_number", sa.Integer(),   nullable=False),
        sa.Column("page_type",   sa.String(30),  nullable=False),
        sa.Column("title",       sa.String(300), nullable=False),
        sa.Column("content_ref", sa.String(500), nullable=False),
        sa.Column("created_at",  sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["package_id"], ["project_packages.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_package_pages_package_id",
                    "package_pages", ["package_id"])


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_index("ix_package_pages_package_id",         table_name="package_pages")
    op.drop_table("package_pages")
    op.drop_index("ix_project_packages_tenant",          table_name="project_packages")
    op.drop_index("ix_project_packages_project_tenant",  table_name="project_packages")
    op.drop_table("project_packages")
