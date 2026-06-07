"""
Simple Configuration Model  (Phase 3.5)
=========================================
Installer-friendly configuration layer for BuildDesk templates.

Design rule: NOTHING in this file should require CAD knowledge.
Users see human words, not fabrication math.

Hidden from users (lives inside simple_mapper.py):
    major_axis, minor_axis, corner_radius, offset values,
    SinkShape, SinkAlignment, all geometry constants.

Exposed to users:
    width, depth, thickness, mirror
    splash back/left/right toggles + height
    sink type (rectangle / oval / none)
    sink position (center / left / right)
    sink size (small / standard / large)
    edge finish (polished / eased / miter / flat)

Full flow:
    SimpleTemplateConfig
        → SimpleConfigMapper.to_template_config()
        → TemplateConfig
        → registry.build()
        → Assembly
        → FabricationDrawingEngine   ← unchanged
"""
from __future__ import annotations

import uuid
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# User-visible enums  (no geometry terminology)
# ---------------------------------------------------------------------------

class SimpleSinkType(str, Enum):
    """Sink cutout shape — words a fabricator uses every day."""
    RECTANGLE = "rectangle"   # "Undermount Rectangle"
    OVAL      = "oval"        # "Undermount Oval"
    NONE      = "none"        # "No Sink"


class SimpleSinkPosition(str, Enum):
    """Where the sink sits along the countertop width."""
    CENTER = "center"
    LEFT   = "left"
    RIGHT  = "right"


class SinkSize(str, Enum):
    """
    T-shirt size for sink cutouts.
    Resolves to concrete dimensions inside SimpleConfigMapper.

    Small:    compact; fits 36\" vanities and prep sinks
    Standard: most common residential sink
    Large:    farm / laundry / double-bowl kitchen
    """
    SMALL    = "small"
    STANDARD = "standard"
    LARGE    = "large"


class SimpleEdgeFinish(str, Enum):
    """
    Edge profile choices — the four fabricators use most.
    Maps 1-to-1 to EdgeType; named for site workers, not CAD.
    """
    POLISHED = "polished"   # smooth, mirrored finish — most common
    EASED    = "eased"      # slightly softened square edge
    MITER    = "miter"      # 45-degree waterfall / laminated edge
    FLAT     = "flat"       # flat polish (stove/range areas)


# ---------------------------------------------------------------------------
# Simple sub-configs
# ---------------------------------------------------------------------------

class SimpleSplashConfig(BaseModel):
    """
    Splash toggle panel — three switches and a height.
    No geometry, no edge-ownership concepts.
    """
    back:   bool  = Field(default=True,  description="Include back splash piece")
    left:   bool  = Field(default=True,  description="Include left side splash piece")
    right:  bool  = Field(default=True,  description="Include right side splash piece")
    height: float = Field(
        default=4.0, ge=1.0, le=12.0,
        description="Splash height in inches (1–12\")",
    )


class SimpleSinkConfig(BaseModel):
    """
    Sink configuration — three fields maximum.
    Concrete dimensions are resolved by SimpleConfigMapper from the preset table.
    """
    type:     SimpleSinkType     = Field(
        default=SimpleSinkType.NONE,
        description="Sink cutout shape",
    )
    position: SimpleSinkPosition = Field(
        default=SimpleSinkPosition.CENTER,
        description="Horizontal placement within the countertop",
    )
    size:     SinkSize           = Field(
        default=SinkSize.STANDARD,
        description="Sink size preset (small / standard / large)",
    )


# ---------------------------------------------------------------------------
# Primary simple config
# ---------------------------------------------------------------------------

class SimpleTemplateConfig(BaseModel):
    """
    Human-friendly countertop configuration.

    Every field in this model is safe to show directly to installers,
    fabricators, and office staff.  No geometry terminology.

    The only backend-internal fields are the UUID identifiers which
    come from the application context, not from the user.

    Naming:
        width  → countertop horizontal span  (fabricators say "width")
        depth  → front-to-back distance      (fabricators say "depth")
    """
    # ── Identity (from app context, not user input) ──────────────────────────
    template_id:  str
    project_id:   uuid.UUID
    tenant_id:    uuid.UUID

    name:         str                  = Field(default="", max_length=200,
                                              description="Optional assembly label")
    unit_id:      Optional[uuid.UUID]  = None
    unit_type_id: Optional[uuid.UUID]  = None

    # ── Dimensions ────────────────────────────────────────────────────────────
    width:     float = Field(gt=0,    description="Horizontal span in inches")
    depth:     float = Field(gt=0,    description="Front-to-back depth in inches")
    thickness: float = Field(
        default=1.25, gt=0, le=6.0,
        description="Slab thickness in inches (default 1¼\")",
    )

    # ── Options ───────────────────────────────────────────────────────────────
    mirror:      bool              = Field(default=False,
                                          description="Flip countertop left-to-right")
    edge_finish: SimpleEdgeFinish  = Field(
        default=SimpleEdgeFinish.POLISHED,
        description="Edge profile for all exposed edges",
    )
    splash:      SimpleSplashConfig = Field(
        default_factory=SimpleSplashConfig,
        description="Back and side splash toggles",
    )
    sink:        SimpleSinkConfig   = Field(
        default_factory=SimpleSinkConfig,
        description="Sink cutout type, position, and size",
    )
