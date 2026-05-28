"""
Geometry Model
==============
A GeometryModel is a concrete instantiation of a ShapeTemplate
with actual dimension values provided by the user.

This is the source of truth in the BuildDesk geometry-first architecture.
All output packages (builder, installer, manufacturer) are derived from
the GeometryModel — never from the PDFs or drawings themselves.

Design decisions:
- dimensions: Dict[str, Any] maps parameter names to concrete values.
  Values may be float, str, or bool depending on ShapeParameter.parameter_type.
- computed_area / computed_perimeter are derived outputs stored here
  to avoid recomputation; the geometry engine populates them.
- schema_version (from BaseDomainModel) must match the source ShapeTemplate.
- stonedesk_geometry_id enables future cross-platform linking.

Inherits from BaseDomainModel: created_at, updated_at, schema_version, touch()
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import Field, model_validator

from app.models.base import BaseDomainModel


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class GeometryStatus(str, Enum):
    """Processing state of the geometry instance."""
    pending = "pending"       # dimensions entered, not yet computed
    computed = "computed"     # geometry engine has run successfully
    error = "error"           # computation failed; see error_message
    locked = "locked"         # approved; no further edits allowed


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class GeometryPiece(BaseDomainModel):
    """
    A single cut piece derived from the overall geometry.

    For example, an L-shape kitchen may yield:
        piece 1: Leg A countertop (96" × 24")
        piece 2: Leg B countertop (48" × 24")
    """

    piece_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    label: str = Field(..., description="Human-readable piece name, e.g. 'Leg A', 'Return'")
    width: float = Field(..., gt=0, description="Width in the template's declared unit")
    length: float = Field(..., gt=0, description="Length in the template's declared unit")
    thickness: Optional[float] = Field(default=None, gt=0)
    area: float = Field(..., gt=0, description="width × length, pre-computed by geometry engine")
    notes: Optional[str] = Field(default=None)


# ---------------------------------------------------------------------------
# Core model
# ---------------------------------------------------------------------------

class GeometryModel(BaseDomainModel):
    """
    Concrete geometry instance produced by applying dimension values
    to a ShapeTemplate.

    geometry-first architecture principle:
        GeometryModel → [Output Engines] → Packages (PDF, reports)
    """

    geometry_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    project_id: uuid.UUID = Field(..., description="Parent project")
    tenant_id: uuid.UUID = Field(..., description="Owning tenant; mirrors project's tenant_id for fast queries")
    template_id: uuid.UUID = Field(..., description="ShapeTemplate this geometry was derived from")

    # Concrete dimension values keyed by parameter name.
    # Values are Any because parameters may be number, string, boolean, or select.
    dimensions: Dict[str, Any] = Field(
        ...,
        description="Map of ShapeParameter.name → value, e.g. {'A': 96.0, 'Depth': 24.0, 'has_sink': True}",
    )

    # Geometry engine outputs
    status: GeometryStatus = Field(default=GeometryStatus.pending)
    pieces: List[GeometryPiece] = Field(
        default_factory=list,
        description="Cut pieces produced by the geometry engine",
    )
    computed_area: Optional[float] = Field(
        default=None,
        description="Total surface area across all pieces (in declared unit²)",
    )
    computed_perimeter: Optional[float] = Field(
        default=None,
        description="Total perimeter / edge length across all pieces",
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Set by the geometry engine when status=error",
    )

    # Future StoneDesk cross-platform linking
    stonedesk_geometry_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Linked StoneDesk geometry record when cross-platform sync is active",
    )

    @model_validator(mode="after")
    def dimensions_must_not_be_empty(self) -> "GeometryModel":
        if not self.dimensions:
            raise ValueError("dimensions must contain at least one parameter value")
        return self
