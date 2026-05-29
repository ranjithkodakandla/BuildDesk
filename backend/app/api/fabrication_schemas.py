"""
Fabrication API Schemas
=======================
Request / Response Pydantic models for the fabrication API endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.fabrication import (
    AssemblyType,
    CutoutType,
    EdgeType,
    MountType,
    PartType,
    Position,
    SplashType,
)
from app.models.hierarchy import UnitVariant


# --- Value Objects ---

class DimensionsSchema(BaseModel):
    length: float
    depth: float
    thickness: Optional[float] = None


class Point2DSchema(BaseModel):
    x: float
    y: float


# --- Pieces ---

class EdgeTreatmentSchema(BaseModel):
    edge_id: Optional[uuid.UUID] = None
    position: Position
    edge_type: EdgeType = EdgeType.EASED
    length: Optional[float] = None
    notes: Optional[str] = None


class CutoutSchema(BaseModel):
    cutout_id: Optional[uuid.UUID] = None
    cutout_type: CutoutType
    mount_type: MountType = MountType.NONE
    dimensions: DimensionsSchema
    center_x: float
    center_y: float
    notes: Optional[str] = None


class HoleSchema(BaseModel):
    hole_id: Optional[uuid.UUID] = None
    diameter: float
    center_x: float
    center_y: float
    purpose: str


class SplashSchema(BaseModel):
    splash_id: Optional[uuid.UUID] = None
    splash_type: SplashType
    dimensions: DimensionsSchema
    notes: Optional[str] = None


# --- Part ---

class PartSchema(BaseModel):
    part_id: Optional[uuid.UUID] = None
    part_type: PartType
    name: str
    dimensions: DimensionsSchema
    notes: Optional[str] = None
    
    edges: List[EdgeTreatmentSchema] = Field(default_factory=list)
    cutouts: List[CutoutSchema] = Field(default_factory=list)
    holes: List[HoleSchema] = Field(default_factory=list)
    splashes: List[SplashSchema] = Field(default_factory=list)


# --- Notes ---

class FabricationNoteSchema(BaseModel):
    note_id: Optional[uuid.UUID] = None
    content: str


# --- Assembly ---

class AssemblyCreateRequest(BaseModel):
    project_id: uuid.UUID
    unit_id: Optional[uuid.UUID] = None
    unit_type_id: Optional[uuid.UUID] = None
    
    name: str
    assembly_type: AssemblyType
    variant: UnitVariant = UnitVariant.STANDARD
    
    parts: List[PartSchema] = Field(default_factory=list)
    notes: List[FabricationNoteSchema] = Field(default_factory=list)


class AssemblyUpdateRequest(BaseModel):
    unit_id: Optional[uuid.UUID] = None
    unit_type_id: Optional[uuid.UUID] = None
    
    name: str
    assembly_type: AssemblyType
    variant: UnitVariant = UnitVariant.STANDARD
    
    parts: List[PartSchema] = Field(default_factory=list)
    notes: List[FabricationNoteSchema] = Field(default_factory=list)


class AssemblyResponse(BaseModel):
    assembly_id: uuid.UUID
    project_id: uuid.UUID
    tenant_id: uuid.UUID
    unit_id: Optional[uuid.UUID]
    unit_type_id: Optional[uuid.UUID]
    
    name: str
    assembly_type: AssemblyType
    variant: UnitVariant
    
    parts: List[PartSchema]
    notes: List[FabricationNoteSchema]


class AssemblyListResponse(BaseModel):
    assemblies: List[AssemblyResponse]
    total: int
