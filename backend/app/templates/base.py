"""
Base Template Interface
=======================
All fabrication templates implement BaseTemplate and return Assembly objects
directly, feeding the existing fabrication pipeline unchanged.

Flow:
    TemplateConfig → BaseTemplate.build() → Assembly → FabricationDrawingEngine

Naming convention (user-visible → domain model):
    config.width  → Dimensions.length  (horizontal span)
    config.depth  → Dimensions.depth   (front-to-back)
"""
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator

from app.models.fabrication import Assembly, EdgeType


class TemplateCategory(str, Enum):
    KITCHEN = "kitchen"
    VANITY  = "vanity"
    ISLAND  = "island"


class SinkShape(str, Enum):
    RECTANGLE = "rectangle"
    OVAL      = "oval"
    NONE      = "none"


class SinkAlignment(str, Enum):
    CENTER = "center"
    LEFT   = "left"
    RIGHT  = "right"


class SplashConfig(BaseModel):
    """Which splash pieces to include and their shared height."""
    back:   bool  = True
    left:   bool  = True
    right:  bool  = True
    height: float = Field(default=4.0, ge=1.0, le=12.0)


class SinkConfig(BaseModel):
    """Sink cutout geometry and placement."""
    shape:     SinkShape     = SinkShape.NONE
    alignment: SinkAlignment = SinkAlignment.CENTER

    # Rectangle-specific
    width:         float = Field(default=16.0, ge=4.0)
    depth:         float = Field(default=12.0, ge=4.0)
    corner_radius: float = Field(default=0.0,  ge=0.0)

    # Oval-specific (bounding box used for drawing engine cutout)
    major_axis: float = Field(default=16.0, ge=4.0)
    minor_axis: float = Field(default=12.0, ge=4.0)

    # Horizontal distance from the nearer edge for LEFT / RIGHT alignment
    offset: float = Field(default=12.0, ge=2.0)

    @model_validator(mode="after")
    def _check_geometry(self) -> "SinkConfig":
        if self.shape == SinkShape.OVAL:
            if self.major_axis < self.minor_axis:
                raise ValueError(
                    f"Oval sink major_axis ({self.major_axis}\") must be ≥ "
                    f"minor_axis ({self.minor_axis}\")."
                )
        if self.shape == SinkShape.RECTANGLE:
            half_min = min(self.width, self.depth) / 2.0
            if self.corner_radius > half_min:
                raise ValueError(
                    f"corner_radius ({self.corner_radius}\") exceeds half of the "
                    f"smaller sink dimension ({half_min:.2f}\"). "
                    f"Maximum: {half_min:.2f}\"."
                )
        return self


class TemplateConfig(BaseModel):
    """
    User-facing configuration for all fabrication templates.

    Templates convert this into an Assembly with fully populated Parts.
    The Assembly is then passed unchanged into the existing drawing pipeline.

    Dimension naming:
        width → Dimensions.length  (horizontal span, e.g. 62")
        depth → Dimensions.depth   (front-to-back,   e.g. 22")
    """
    template_id:   str
    project_id:    uuid.UUID
    tenant_id:     uuid.UUID

    # Assembly identity
    name:          str                  = ""    # falls back to template display_name
    unit_id:       Optional[uuid.UUID]  = None
    unit_type_id:  Optional[uuid.UUID]  = None

    # Primary dimensions
    width:     float = Field(gt=0, description="Horizontal span in inches")
    depth:     float = Field(gt=0, description="Front-to-back depth in inches")
    thickness: float = Field(default=1.25, gt=0, description="Slab thickness in inches")

    # Geometry options
    mirror:      bool        = False
    splash:      SplashConfig = Field(default_factory=SplashConfig)
    sink:        SinkConfig   = Field(default_factory=SinkConfig)
    edge_finish: EdgeType     = EdgeType.POLISHED

    # Template-specific overrides (e.g. ref_width for KitchenStraightRef)
    extra_params: Dict[str, Any] = Field(default_factory=dict)


class TemplateDefinition(BaseModel):
    """Metadata about a template — used to populate the template picker UI."""
    id:                 str
    category:           TemplateCategory
    display_name:       str
    description:        str
    defaults:           Dict[str, Any]
    editable_fields:    List[str]
    supported_features: List[str]


class BaseTemplate(ABC):
    """
    Abstract base for all fabrication templates.

    Subclass and implement:
        definition  → static metadata (id, category, defaults, …)
        build()     → Assembly from TemplateConfig

    The returned Assembly feeds directly into:
        FabricationDrawingEngine.draw_assembly(canvas, assembly, ...)
    No renderer, SVG, PDF, or database layer is touched.
    """

    @property
    @abstractmethod
    def definition(self) -> TemplateDefinition:
        """Static metadata for the template picker UI."""
        ...

    @abstractmethod
    def build(self, config: TemplateConfig) -> Assembly:
        """
        Convert TemplateConfig into an Assembly with fully populated Parts.

        Constraints:
            - Must not access the database.
            - Must not call FabricationDrawingEngine, PackagePdfExporter, or SVG exporter.
            - May call helpers from app.templates._helpers freely.
        """
        ...
