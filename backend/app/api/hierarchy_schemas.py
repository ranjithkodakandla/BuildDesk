"""
Project Hierarchy API Schemas
==============================
Request / Response Pydantic models for the hierarchy API endpoints.

Covers: Project, Building, Floor, UnitType, Unit
These are HTTP contracts only — internal domain models are in app/models/hierarchy.py
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums (mirror hierarchy domain enums for API surface)
# ---------------------------------------------------------------------------

class UnitVariantSchema(str, Enum):
    STANDARD = "standard"
    MIRROR   = "MIR"
    ADA      = "ADA"
    LEFT     = "LEFT"
    RIGHT    = "RIGHT"
    REVERSED = "REV"
    CUSTOM   = "custom"


class UnitStatusSchema(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


# ---------------------------------------------------------------------------
# HierarchyConfig
# ---------------------------------------------------------------------------

class HierarchyConfigSchema(BaseModel):
    has_buildings:  bool = False
    has_floors:     bool = False
    has_unit_types: bool = True


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------

class ProjectCreateRequest(BaseModel):
    name:          str                    = Field(..., min_length=1, max_length=300)
    client_name:   Optional[str]          = Field(default=None)
    material:      Optional[str]          = Field(default=None, description="e.g. 'Calacatta Gold 3cm'")
    issue_date:    Optional[date]         = Field(default=None)
    description:   Optional[str]         = Field(default=None)
    address:       Optional[str]         = Field(default=None)
    hierarchy_config: HierarchyConfigSchema = Field(default_factory=HierarchyConfigSchema)


class ProjectResponse(BaseModel):
    project_id:       uuid.UUID
    tenant_id:        uuid.UUID
    name:             str
    client_name:      Optional[str]
    material:         Optional[str]
    issue_date:       Optional[date]
    description:      Optional[str]
    address:          Optional[str]
    status:           str
    hierarchy_config: HierarchyConfigSchema
    created_at:       datetime
    updated_at:       datetime


class ProjectListResponse(BaseModel):
    projects: List[ProjectResponse]
    total:    int


# ---------------------------------------------------------------------------
# Building
# ---------------------------------------------------------------------------

class BuildingCreateRequest(BaseModel):
    name:       str            = Field(..., min_length=1, max_length=200)
    code:       Optional[str]  = Field(default=None, max_length=20)
    sort_order: int            = Field(default=0)


class BuildingResponse(BaseModel):
    building_id: uuid.UUID
    project_id:  uuid.UUID
    name:        str
    code:        Optional[str]
    sort_order:  int
    created_at:  datetime


# ---------------------------------------------------------------------------
# Floor
# ---------------------------------------------------------------------------

class FloorCreateRequest(BaseModel):
    building_id: uuid.UUID
    name:        str           = Field(..., min_length=1, max_length=200)
    number:      Optional[int] = Field(default=None)
    sort_order:  int           = Field(default=0)


class FloorResponse(BaseModel):
    floor_id:    uuid.UUID
    project_id:  uuid.UUID
    building_id: uuid.UUID
    name:        str
    number:      Optional[int]
    sort_order:  int
    created_at:  datetime


# ---------------------------------------------------------------------------
# UnitType
# ---------------------------------------------------------------------------

class UnitTypeCreateRequest(BaseModel):
    code:         str            = Field(..., min_length=1, max_length=50,
                                        description="Short identifier: 'A', 'B1', 'ADA'")
    name:         str            = Field(..., min_length=1, max_length=200)
    description:  Optional[str]  = Field(default=None)
    is_mirror:    bool           = Field(default=False)
    is_ada:       bool           = Field(default=False)
    base_type_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Parent UnitType ID if this is a derived variant (e.g. A-MIR from A)"
    )
    sort_order:   int            = Field(default=0)


class UnitTypeResponse(BaseModel):
    unit_type_id: uuid.UUID
    project_id:   uuid.UUID
    code:         str
    name:         str
    description:  Optional[str]
    is_mirror:    bool
    is_ada:       bool
    base_type_id: Optional[uuid.UUID]
    sort_order:   int
    created_at:   datetime


class UnitTypeListResponse(BaseModel):
    unit_types: List[UnitTypeResponse]
    total:      int


# ---------------------------------------------------------------------------
# Unit
# ---------------------------------------------------------------------------

class UnitCreateRequest(BaseModel):
    name:         str                         = Field(..., min_length=1, max_length=200)
    code:         str                         = Field(..., min_length=1, max_length=50)
    building_id:  Optional[uuid.UUID]         = Field(default=None)
    floor_id:     Optional[uuid.UUID]         = Field(default=None)
    unit_type_id: Optional[uuid.UUID]         = Field(default=None)
    variant:      UnitVariantSchema           = Field(default=UnitVariantSchema.STANDARD)
    notes:        Optional[str]               = Field(default=None)
    sort_order:   int                         = Field(default=0)


class UnitBulkCreateRequest(BaseModel):
    start_number: int                 = Field(..., description="Starting unit number (e.g. 101)")
    end_number:   int                 = Field(..., description="Ending unit number (e.g. 120)")
    prefix:       Optional[str]       = Field(default="", description="Prefix for unit code (e.g. 'A-')")
    suffix:       Optional[str]       = Field(default="", description="Suffix for unit code")
    increment:    int                 = Field(default=1, description="Increment step")
    building_id:  Optional[uuid.UUID] = Field(default=None)
    floor_id:     Optional[uuid.UUID] = Field(default=None)
    unit_type_id: Optional[uuid.UUID] = Field(default=None)
    variant:      UnitVariantSchema   = Field(default=UnitVariantSchema.STANDARD)
    
class UnitBulkCreateResponse(BaseModel):
    created_count: int
    units: List[UnitResponse]


class UnitBulkUpdateRequest(BaseModel):
    unit_ids:     List[uuid.UUID]     = Field(..., description="List of unit IDs to update")
    building_id:  Optional[uuid.UUID] = Field(default=None)
    floor_id:     Optional[uuid.UUID] = Field(default=None)
    unit_type_id: Optional[uuid.UUID] = Field(default=None)
    variant:      Optional[UnitVariantSchema] = Field(default=None)
    status:       Optional[UnitStatusSchema] = Field(default=None)

class UnitBulkUpdateResponse(BaseModel):
    updated_count: int


class UnitResponse(BaseModel):
    unit_id:      uuid.UUID
    project_id:   uuid.UUID
    name:         str
    code:         str
    building_id:  Optional[uuid.UUID]
    floor_id:     Optional[uuid.UUID]
    unit_type_id: Optional[uuid.UUID]
    variant:      str
    status:       str
    notes:        Optional[str]
    sort_order:   int
    created_at:   datetime


class UnitListResponse(BaseModel):
    units: List[UnitResponse]
    total: int


# ---------------------------------------------------------------------------
# Project Tree (full hierarchy view)
# ---------------------------------------------------------------------------

class UnitTypeWithUnitsResponse(BaseModel):
    unit_type: UnitTypeResponse
    units:     List[UnitResponse]
    quantity:  int


class FloorWithUnitsResponse(BaseModel):
    floor: FloorResponse
    units: List[UnitResponse]


class BuildingWithFloorsResponse(BaseModel):
    building: BuildingResponse
    floors:   List[FloorWithUnitsResponse]
    units:    List[UnitResponse]  # units directly on building (no floor)


class ProjectTreeResponse(BaseModel):
    project:    ProjectResponse
    buildings:  List[BuildingWithFloorsResponse]
    unit_types: List[UnitTypeWithUnitsResponse]
    units:      List[UnitResponse]
    total_units: int
