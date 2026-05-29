"""
Project Hierarchy Domain Models
================================
Flexible, optional hierarchy for multifamily countertop fabrication projects.

Hierarchy levels:
    Project
    ├── Building   (optional — controlled by HierarchyConfig.has_buildings)
    │   ├── Floor  (optional — controlled by HierarchyConfig.has_floors)
    │   │   └── Unit
    │   └── Unit   (floor absent)
    └── Unit       (building + floor absent)

Design decisions:
- All intermediate levels are optional.
- HierarchyConfig is stored as JSON on the Project record.
- UnitVariant captures MIR, ADA, LEFT, RIGHT, REV, CUSTOM.
- UnitType supports derived types (A-MIR derived from A).
- Building/Floor have sort_order to control drawing package page ordering.
"""

from __future__ import annotations

import uuid
from datetime import date
from enum import Enum
from typing import Optional

from pydantic import Field

from app.models.base import BaseDomainModel


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ProjectStatus(str, Enum):
    """Lifecycle states of a fabrication project."""
    draft       = "draft"
    in_progress = "in_progress"
    issued      = "issued"
    archived    = "archived"


class UnitVariant(str, Enum):
    """
    Real-world unit variants used in multifamily countertop fabrication.
    A unit can be a mirror, ADA adaptation, left/right-hand layout, etc.
    """
    STANDARD = "standard"
    MIRROR   = "MIR"
    ADA      = "ADA"
    LEFT     = "LEFT"
    RIGHT    = "RIGHT"
    REVERSED = "REV"
    CUSTOM   = "custom"


# ---------------------------------------------------------------------------
# HierarchyConfig — controls which hierarchy levels are active
# ---------------------------------------------------------------------------

class HierarchyConfig(BaseDomainModel):
    """
    Controls which levels of the project hierarchy are used.
    Stored as JSON inside ProjectRecord.hierarchy_config.

    Examples:
        Simple:        has_buildings=False, has_floors=False
        With buildings: has_buildings=True,  has_floors=False
        Full:          has_buildings=True,  has_floors=True
    """
    has_buildings: bool = Field(default=False)
    has_floors:    bool = Field(default=False)
    has_unit_types: bool = Field(default=True)


# ---------------------------------------------------------------------------
# Project (extended)
# ---------------------------------------------------------------------------

class Project(BaseDomainModel):
    """
    A tenant-scoped fabrication project grouping buildings, units,
    assemblies and their output packages.

    Extended fields vs legacy ProjectRecord:
        client_name, material, issue_date, hierarchy_config, status (issued/archived)
    """
    project_id:       uuid.UUID        = Field(default_factory=uuid.uuid4)
    tenant_id:        uuid.UUID        = Field(..., description="Owning tenant")
    name:             str              = Field(..., min_length=1, max_length=300)
    client_name:      Optional[str]    = Field(default=None, max_length=300)
    material:         Optional[str]    = Field(
        default=None, max_length=500,
        description="Primary countertop material, e.g. 'Calacatta Gold 3cm'"
    )
    issue_date:       Optional[date]   = Field(default=None)
    description:      Optional[str]    = Field(default=None, max_length=1000)
    address:          Optional[str]    = Field(default=None, max_length=500)
    status:           ProjectStatus    = Field(default=ProjectStatus.draft)
    hierarchy_config: HierarchyConfig  = Field(default_factory=HierarchyConfig)


# ---------------------------------------------------------------------------
# Building
# ---------------------------------------------------------------------------

class Building(BaseDomainModel):
    """
    An optional grouping of floors and units within a project.

    Examples: "Building A", "Tower 1", "North Wing"
    """
    building_id: uuid.UUID      = Field(default_factory=uuid.uuid4)
    project_id:  uuid.UUID      = Field(..., description="Parent project")
    tenant_id:   uuid.UUID      = Field(..., description="Owning tenant (denormalized for isolation)")
    name:        str            = Field(..., min_length=1, max_length=200)
    code:        Optional[str]  = Field(default=None, max_length=20,
                                        description="Short code used in labels, e.g. 'A', 'T1'")
    sort_order:  int            = Field(default=0, description="Controls page ordering in package")


# ---------------------------------------------------------------------------
# Floor
# ---------------------------------------------------------------------------

class Floor(BaseDomainModel):
    """
    An optional grouping of units within a building.

    Examples: "Floor 2", "Level 3", "Penthouse"
    """
    floor_id:    uuid.UUID      = Field(default_factory=uuid.uuid4)
    project_id:  uuid.UUID      = Field(..., description="Parent project (denormalized)")
    building_id: uuid.UUID      = Field(..., description="Parent building")
    tenant_id:   uuid.UUID      = Field(..., description="Owning tenant (denormalized)")
    name:        str            = Field(..., min_length=1, max_length=200)
    number:      Optional[int]  = Field(default=None, description="Numeric floor number")
    sort_order:  int            = Field(default=0)


# ---------------------------------------------------------------------------
# UnitType
# ---------------------------------------------------------------------------

class UnitType(BaseDomainModel):
    """
    A named unit plan type within a project.

    Examples: Type A, Type B, Type B1, ADA, A-MIR

    base_type_id: links derived types back to their source
                  (A-MIR.base_type_id → A.unit_type_id)
    """
    unit_type_id: uuid.UUID      = Field(default_factory=uuid.uuid4)
    project_id:   uuid.UUID      = Field(..., description="Parent project")
    tenant_id:    uuid.UUID      = Field(..., description="Owning tenant")
    code:         str            = Field(..., min_length=1, max_length=50,
                                        description="Short identifier: 'A', 'B1', 'ADA'")
    name:         str            = Field(..., min_length=1, max_length=200,
                                        description="Full name: 'Type A — 2BR/2BA'")
    description:  Optional[str]  = Field(default=None, max_length=1000)
    is_mirror:    bool           = Field(default=False,
                                        description="True if this type is a mirror variant")
    is_ada:       bool           = Field(default=False,
                                        description="True if this type is ADA-compliant variant")
    base_type_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Points to source UnitType if this is a derived variant (e.g. A-MIR from A)"
    )
    sort_order:   int            = Field(default=0)


# ---------------------------------------------------------------------------
# Unit
# ---------------------------------------------------------------------------

class Unit(BaseDomainModel):
    """
    A single dwelling or workspace within the project hierarchy.

    Examples: "Apt 201", "Unit A-12", "Suite 4B"

    building_id and floor_id are optional — set to None when those
    hierarchy levels are not active in the project.
    """
    unit_id:      uuid.UUID           = Field(default_factory=uuid.uuid4)
    project_id:   uuid.UUID           = Field(..., description="Parent project")
    tenant_id:    uuid.UUID           = Field(..., description="Owning tenant")
    building_id:  Optional[uuid.UUID] = Field(default=None, description="Parent building (if used)")
    floor_id:     Optional[uuid.UUID] = Field(default=None, description="Parent floor (if used)")
    unit_type_id: Optional[uuid.UUID] = Field(default=None, description="UnitType definition")
    name:         str                 = Field(..., min_length=1, max_length=200,
                                             description="Full unit name: 'Apt 201'")
    code:         str                 = Field(..., min_length=1, max_length=50,
                                             description="Short code: '201', 'A12'")
    variant:      UnitVariant         = Field(default=UnitVariant.STANDARD)
    notes:        Optional[str]       = Field(default=None, max_length=1000)
    sort_order:   int                 = Field(default=0)
