"""
API Request / Response Schemas
================================
Clean HTTP contracts — separate from internal domain models.

Design principle:
    HTTP schema   → what the API surface exposes / accepts
    Domain model  → internal representation (GeometryModel, ShapeTemplate, …)

Consumers of these schemas (routers) translate between the two layers.
Internal services never import from this module.

Schemas defined here:
    Shapes API
        ShapeParameterResponse  – single parameter definition (read-only)
        ShapeTemplateResponse   – template listing / detail
        ShapeListResponse       – list of available templates

    Geometry API
        GeometryRequest         – POST /api/v1/geometry request body
        GeometryPieceResponse   – one cut piece in the response
        DimensionLineResponse   – dimension annotation in the response
        GeometryResponse        – full POST response (GeometryModel + primitives)

    Errors
        ValidationErrorDetail   – per-parameter validation failure
        ValidationErrorResponse – 422 body shape for domain validation errors
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shapes API
# ---------------------------------------------------------------------------

class ShapeParameterResponse(BaseModel):
    """Read-only representation of one ShapeParameter for API consumers."""

    name: str
    label: str
    parameter_type: str
    unit: str
    required: bool
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    default_value: Optional[Any] = None
    allowed_options: Optional[List[str]] = None
    description: Optional[str] = None


class ShapeTemplateResponse(BaseModel):
    """Full template detail returned by GET /shapes/{shape_type}."""

    template_id: uuid.UUID
    name: str
    category: str
    description: Optional[str]
    system_template: bool
    schema_version: str
    parameters: List[ShapeParameterResponse]


class ShapeListItemResponse(BaseModel):
    """Compact template summary returned in the shapes list."""

    shape_type: str          # registry slug, e.g. "rectangle"
    template_id: uuid.UUID
    name: str
    category: str
    description: Optional[str]
    parameter_count: int


class ShapeListResponse(BaseModel):
    """Response body for GET /api/v1/shapes."""

    shapes: List[ShapeListItemResponse]
    total: int


# ---------------------------------------------------------------------------
# Geometry API — request
# ---------------------------------------------------------------------------

class GeometryRequest(BaseModel):
    """
    Request body for POST /api/v1/geometry.

    shape_type must match a key in SHAPE_REGISTRY (e.g. "rectangle").
    project_id and tenant_id are required for multi-tenant context.
    dimensions is the raw parameter payload validated by TemplateResolver.
    """

    shape_type: str = Field(
        ...,
        description="Shape type slug, e.g. 'rectangle'. Must exist in the shape registry.",
        examples=["rectangle"],
    )
    project_id: uuid.UUID = Field(
        ...,
        description="Parent project UUID",
    )
    tenant_id: uuid.UUID = Field(
        ...,
        description="Owning tenant UUID",
    )
    dimensions: Dict[str, Any] = Field(
        ...,
        description="Raw parameter key-value map; validated by TemplateResolver.",
        examples=[{"length": 96, "width": 42}],
    )


# ---------------------------------------------------------------------------
# Geometry API — response
# ---------------------------------------------------------------------------

class GeometryPieceResponse(BaseModel):
    """One cut piece produced by the geometry engine."""

    piece_id: uuid.UUID
    label: str
    width: float
    length: float
    thickness: Optional[float]
    area: float
    notes: Optional[str]


class DimensionLineResponse(BaseModel):
    """Dimension annotation produced by the geometry builder."""

    dim_id: uuid.UUID
    value: float
    unit: str
    display_text: str
    start: Dict[str, float]   # {"x": …, "y": …}
    end:   Dict[str, float]


class RectangleResponse(BaseModel):
    """Rectangle primitive produced by the geometry builder."""

    rect_id: uuid.UUID
    label: Optional[str]
    width: float
    height: float
    area: float
    perimeter: float
    origin: Dict[str, float]
    center: Dict[str, float]


class GeometryResponse(BaseModel):
    """
    Full response body for POST /api/v1/geometry.

    Contains the computed GeometryModel summary plus all
    geometry primitives produced by the builder.
    """

    geometry_id: uuid.UUID
    template_id: uuid.UUID
    project_id: uuid.UUID
    tenant_id: uuid.UUID
    shape_type: str
    status: str
    computed_area: Optional[float]
    computed_perimeter: Optional[float]
    dimensions: Dict[str, Any]
    pieces: List[GeometryPieceResponse]
    rectangles: List[RectangleResponse]
    dimension_lines: List[DimensionLineResponse]
    metadata: Optional[Dict[str, Any]] = None
    schema_version: str


# ---------------------------------------------------------------------------
# Error schemas
# ---------------------------------------------------------------------------

class ValidationErrorDetail(BaseModel):
    """A single parameter-level validation failure."""

    parameter: str
    message: str


class ValidationErrorResponse(BaseModel):
    """
    Response body for domain-level 422 responses.

    Distinct from FastAPI's built-in RequestValidationError (which handles
    HTTP schema violations). This covers business-rule violations from
    the TemplateResolver (missing required, out-of-range, bad select option).
    """

    error: str = "validation_error"
    detail: str
    errors: List[ValidationErrorDetail]
