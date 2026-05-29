"""
Fabrication Domain Models
=========================
Core business entities for real-world countertop fabrication.

Hierarchy:
    Project/Unit (from Phase 1)
    └── Assembly (e.g., Kitchen, Vanity)
        ├── Part (e.g., Main Top, Island)
        │   ├── EdgeTreatment (attached to specific sides of a Part)
        │   ├── Cutout (e.g., Sink, Cooktop)
        │   ├── Hole (e.g., Faucet, Soap dispenser)
        │   └── Splash (e.g., Backsplash, Sidesplash)
        └── FabricationNote
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import List, Optional

from pydantic import Field

from app.models.base import BaseDomainModel
from app.models.hierarchy import UnitVariant


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AssemblyType(str, Enum):
    KITCHEN = "kitchen"
    VANITY = "vanity"
    ISLAND = "island"
    BAR_TOP = "bar_top"
    LAUNDRY = "laundry"
    DESK = "desk"
    CUSTOM = "custom"


class PartType(str, Enum):
    MAIN_TOP = "main_top"
    LEFT_RETURN = "left_return"
    RIGHT_RETURN = "right_return"
    ISLAND_TOP = "island_top"
    BAR_TOP = "bar_top"
    APRON = "apron"
    LOOSE_PIECE = "loose_piece"


class EdgeType(str, Enum):
    EASED = "eased"
    FLAT = "flat"
    MITER = "miter"
    LAMINATED = "laminated"
    POLISHED = "polished"
    RAW = "raw"
    FINISHED = "finished"
    UNFINISHED = "unfinished"
    BULLNOSE = "bullnose"
    HALF_BULLNOSE = "half_bullnose"
    BEVEL = "bevel"
    OGEE = "ogee"


class CutoutType(str, Enum):
    SINK = "sink"
    COOKTOP = "cooktop"
    OUTLET = "outlet"
    NOTCH = "notch"
    GENERIC = "generic"


class MountType(str, Enum):
    UNDERMOUNT = "undermount"
    DROP_IN = "drop_in"
    FARM_SINK = "farm_sink"
    SURFACE_MOUNT = "surface_mount"
    FLUSH_MOUNT = "flush_mount"
    NONE = "none"


class SplashType(str, Enum):
    BACKSPLASH = "backsplash"
    LEFT_SPLASH = "left_splash"
    RIGHT_SPLASH = "right_splash"
    CUSTOM = "custom"


class Position(str, Enum):
    FRONT = "front"
    BACK = "back"
    LEFT = "left"
    RIGHT = "right"
    CENTER = "center"
    CUSTOM = "custom"


# ---------------------------------------------------------------------------
# Value Objects (Shared embedded structures)
# ---------------------------------------------------------------------------

class Dimensions(BaseDomainModel):
    """Physical dimensions in inches."""
    length: float = Field(..., description="Length in inches")
    depth: float = Field(..., description="Depth/Width in inches")
    thickness: Optional[float] = Field(default=None, description="Thickness in inches")


class Point2D(BaseDomainModel):
    """Coordinates within a 2D plane (e.g., on a Part)."""
    x: float
    y: float


# ---------------------------------------------------------------------------
# Core Entities
# ---------------------------------------------------------------------------

class EdgeTreatment(BaseDomainModel):
    """Defines how a specific edge of a part is finished."""
    edge_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    part_id: uuid.UUID
    position: Position = Field(..., description="Which side of the part this edge applies to")
    edge_type: EdgeType = Field(default=EdgeType.EASED)
    length: Optional[float] = Field(default=None, description="Length of the treated edge if partial")
    notes: Optional[str] = Field(default=None)


class Cutout(BaseDomainModel):
    """A removed section of material, usually for an appliance or sink."""
    cutout_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    part_id: uuid.UUID
    cutout_type: CutoutType = Field(..., description="Type of cutout (sink, cooktop, etc.)")
    mount_type: MountType = Field(default=MountType.NONE)
    dimensions: Dimensions = Field(..., description="Size of the cutout")
    center_x: float = Field(..., description="X-coordinate of cutout center relative to part origin")
    center_y: float = Field(..., description="Y-coordinate of cutout center relative to part origin")
    notes: Optional[str] = Field(default=None)


class Hole(BaseDomainModel):
    """Small circular drills, usually for faucets or soap dispensers."""
    hole_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    part_id: uuid.UUID
    diameter: float = Field(..., description="Diameter of the hole in inches")
    center_x: float = Field(..., description="X coordinate relative to part origin")
    center_y: float = Field(..., description="Y coordinate relative to part origin")
    purpose: str = Field(..., description="e.g., Faucet, Soap, Air Switch", max_length=100)


class Splash(BaseDomainModel):
    """A vertical piece of stone attached to a wall."""
    splash_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    part_id: uuid.UUID = Field(..., description="The base part this splash attaches to")
    splash_type: SplashType = Field(...)
    dimensions: Dimensions = Field(..., description="Dimensions of the splash piece itself")
    notes: Optional[str] = Field(default=None)


class Part(BaseDomainModel):
    """A single fabricated piece of stone (e.g., Main Top)."""
    part_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    assembly_id: uuid.UUID
    part_type: PartType = Field(...)
    name: str = Field(..., max_length=100)
    dimensions: Dimensions = Field(...)
    notes: Optional[str] = Field(default=None)
    
    # Relationships
    edges: List[EdgeTreatment] = Field(default_factory=list)
    cutouts: List[Cutout] = Field(default_factory=list)
    holes: List[Hole] = Field(default_factory=list)
    splashes: List[Splash] = Field(default_factory=list)


class FabricationNote(BaseDomainModel):
    """General assembly-level instruction or warning."""
    note_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    assembly_id: uuid.UUID
    content: str = Field(..., max_length=1000)


class Assembly(BaseDomainModel):
    """
    A logical grouping of countertop pieces that form a single functional area.
    Examples: A full kitchen layout, a bathroom vanity.
    """
    assembly_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    project_id: uuid.UUID
    tenant_id: uuid.UUID
    unit_id: Optional[uuid.UUID] = Field(default=None, description="Linked unit, if any")
    unit_type_id: Optional[uuid.UUID] = Field(default=None, description="Linked unit type, if any")
    
    name: str = Field(..., max_length=200, description="e.g., Kitchen, Master Bath Vanity")
    assembly_type: AssemblyType = Field(...)
    variant: UnitVariant = Field(default=UnitVariant.STANDARD)
    
    # Relationships
    parts: List[Part] = Field(default_factory=list)
    notes: List[FabricationNote] = Field(default_factory=list)
