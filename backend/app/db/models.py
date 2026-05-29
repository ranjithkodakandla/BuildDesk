"""
SQLAlchemy ORM Models
=====================
All persistent database models for BuildDesk.

Hierarchy:
    TenantRecord
    ProjectRecord (extended: client_name, material, issue_date,
                             hierarchy_config, status, description, address)
    BuildingRecord
    FloorRecord
    UnitTypeRecord
    UnitRecord
    GeometryRecord  (legacy — kept for backward compatibility)
    UserRecord      (authentication)

Rules:
- All new columns on ProjectRecord are nullable with defaults (additive migration).
- New tables reference tenants.id and projects.id via FK.
- All IDs are VARCHAR(36) UUIDs for PostgreSQL/SQLite portability.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, DateTime, JSON, ForeignKey, Boolean, Integer, Text, Date, Float
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utcnow():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Tenant
# ---------------------------------------------------------------------------

class TenantRecord(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ---------------------------------------------------------------------------
# Project (extended — additive columns only)
# ---------------------------------------------------------------------------

class ProjectRecord(Base):
    """
    Fabrication project record.

    Original columns: id, tenant_id, name, created_at
    Added columns (all nullable, all with defaults):
        client_name, material, issue_date, hierarchy_config,
        status, description, address, updated_at
    """
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # ── Extended fields (additive — all nullable with defaults) ────────────
    client_name: Mapped[Optional[str]] = mapped_column(String(300), nullable=True, default=None)
    material: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, default=None)
    issue_date: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True, default=None)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, default=None)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    # JSON: {"has_buildings": bool, "has_floors": bool, "has_unit_types": bool}
    hierarchy_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=None)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


# ---------------------------------------------------------------------------
# Building (new)
# ---------------------------------------------------------------------------

class BuildingRecord(Base):
    """Optional grouping within a project. e.g. 'Building A', 'Tower 1'."""
    __tablename__ = "buildings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, default=None)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


# ---------------------------------------------------------------------------
# Floor (new)
# ---------------------------------------------------------------------------

class FloorRecord(Base):
    """Optional grouping within a building. e.g. 'Floor 2', 'Level 3'."""
    __tablename__ = "floors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    building_id: Mapped[str] = mapped_column(String(36), ForeignKey("buildings.id"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=None)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


# ---------------------------------------------------------------------------
# UnitType (new)
# ---------------------------------------------------------------------------

class UnitTypeRecord(Base):
    """
    Named unit plan type within a project.
    e.g. Type A, Type B1, ADA, A-MIR
    """
    __tablename__ = "unit_types"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    is_mirror: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_ada: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Points to another UnitTypeRecord if this is a derived variant (A-MIR from A)
    base_type_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("unit_types.id"), nullable=True, default=None
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


# ---------------------------------------------------------------------------
# Unit (new)
# ---------------------------------------------------------------------------

class UnitRecord(Base):
    """
    A single dwelling or workspace in the project.
    building_id and floor_id are nullable — only set when those
    hierarchy levels are active in the project's HierarchyConfig.
    """
    __tablename__ = "units"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    building_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("buildings.id"), nullable=True, default=None
    )
    floor_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("floors.id"), nullable=True, default=None
    )
    unit_type_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("unit_types.id"), nullable=True, default=None
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    # MIR, ADA, LEFT, RIGHT, REV, CUSTOM, standard
    variant: Mapped[str] = mapped_column(String(20), nullable=False, default="standard")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


# ---------------------------------------------------------------------------
# Geometry (legacy — kept for backward compatibility)
# ---------------------------------------------------------------------------

class GeometryRecord(Base):
    """
    Legacy geometry record. Kept for backward compatibility with
    POST /api/v1/geometry. Will be superseded by Assembly/Part
    in Phase 2. Do not use for new fabrication-domain features.
    """
    __tablename__ = "geometries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"))
    shape_type: Mapped[str] = mapped_column(String(50))
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ---------------------------------------------------------------------------
# User (authentication)
# ---------------------------------------------------------------------------

class UserRecord(Base):
    """Persistent user record for JWT-based authentication."""
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="member")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ---------------------------------------------------------------------------
# Fabrication Domain (Phase 2)
# ---------------------------------------------------------------------------

class AssemblyRecord(Base):
    __tablename__ = "assemblies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    unit_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("units.id"), nullable=True, default=None)
    unit_type_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("unit_types.id"), nullable=True, default=None)
    
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    assembly_type: Mapped[str] = mapped_column(String(50), nullable=False)
    variant: Mapped[str] = mapped_column(String(20), nullable=False, default="standard")
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class FabricationNoteRecord(Base):
    __tablename__ = "fabrication_notes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    assembly_id: Mapped[str] = mapped_column(String(36), ForeignKey("assemblies.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PartRecord(Base):
    __tablename__ = "parts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    assembly_id: Mapped[str] = mapped_column(String(36), ForeignKey("assemblies.id"), nullable=False)
    part_type: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Dimensions
    dim_length: Mapped[float] = mapped_column(Float, nullable=False)
    dim_depth: Mapped[float] = mapped_column(Float, nullable=False)
    dim_thickness: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=None)
    
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SplashRecord(Base):
    __tablename__ = "splashes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    part_id: Mapped[str] = mapped_column(String(36), ForeignKey("parts.id"), nullable=False)
    splash_type: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Dimensions
    dim_length: Mapped[float] = mapped_column(Float, nullable=False)
    dim_depth: Mapped[float] = mapped_column(Float, nullable=False)
    dim_thickness: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=None)
    
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CutoutRecord(Base):
    __tablename__ = "cutouts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    part_id: Mapped[str] = mapped_column(String(36), ForeignKey("parts.id"), nullable=False)
    cutout_type: Mapped[str] = mapped_column(String(50), nullable=False)
    mount_type: Mapped[str] = mapped_column(String(50), nullable=False, default="none")
    
    # Position
    center_x: Mapped[float] = mapped_column(Float, nullable=False)
    center_y: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Dimensions
    dim_length: Mapped[float] = mapped_column(Float, nullable=False)
    dim_depth: Mapped[float] = mapped_column(Float, nullable=False)
    dim_thickness: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=None)
    
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class HoleRecord(Base):
    __tablename__ = "holes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    part_id: Mapped[str] = mapped_column(String(36), ForeignKey("parts.id"), nullable=False)
    diameter: Mapped[float] = mapped_column(Float, nullable=False)
    center_x: Mapped[float] = mapped_column(Float, nullable=False)
    center_y: Mapped[float] = mapped_column(Float, nullable=False)
    purpose: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class EdgeTreatmentRecord(Base):
    __tablename__ = "edge_treatments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    part_id: Mapped[str] = mapped_column(String(36), ForeignKey("parts.id"), nullable=False)
    position: Mapped[str] = mapped_column(String(50), nullable=False)
    edge_type: Mapped[str] = mapped_column(String(50), nullable=False, default="eased")
    length: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=None)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ---------------------------------------------------------------------------
# Project Packages  (Phase 3)
# ---------------------------------------------------------------------------

class ProjectPackageRecord(Base):
    """
    Persisted fabrication package for one project.
    One package = one multi-page PDF set.
    Packages are immutable once status='ready'.
    """
    __tablename__ = "project_packages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0")
    issued_by: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, default=None)
    issued_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    # draft | generating | ready | generation_failed | archived
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")
    # Reserved for Phase 6 GCS upload
    storage_reference: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True, default=None)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=None)
    generated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class PackagePageRecord(Base):
    """
    A single page record within a ProjectPackage.
    page_type: cover | type_sheet | assembly_drawing | summary
    content_ref: opaque string used by PackagePdfExporter to locate content.
    """
    __tablename__ = "package_pages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    package_id: Mapped[str] = mapped_column(String(36), ForeignKey("project_packages.id"), nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    # cover | type_sheet | assembly_drawing | summary
    page_type: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    content_ref: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
