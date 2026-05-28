"""
Geometry Router
===============
HTTP endpoint for the BuildDesk geometry generation pipeline.

Endpoint:
    POST /api/v1/geometry

Pipeline:
    GeometryRequest (shape_type + project_id + tenant_id + dimensions)
        → ShapeTemplate lookup (SHAPE_REGISTRY)
        → TemplateResolver.resolve()
        → GeometryBuilder.build()
        → GeometryResponse

HTTP status codes used:
    200  – geometry computed successfully
    404  – shape_type not found in registry
    422  – domain validation error (missing required param, out-of-range, etc.)
    400  – unsupported shape (template exists but handler not yet implemented)
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.api.schemas import (
    DimensionLineResponse,
    GeometryPieceResponse,
    GeometryRequest,
    GeometryResponse,
    RectangleResponse,
    ValidationErrorDetail,
    ValidationErrorResponse,
)
from app.geometry.shapes import SHAPE_REGISTRY
from app.services.geometry_builder import GeometryBuilder, UnsupportedShapeError
from app.services.template_resolver import TemplateResolver

router = APIRouter()

# ---------------------------------------------------------------------------
# Singletons — stateless services, safe to share across requests
# ---------------------------------------------------------------------------

_resolver = TemplateResolver()
_builder  = GeometryBuilder()


# ---------------------------------------------------------------------------
# POST /geometry
# ---------------------------------------------------------------------------

@router.post(
    "/geometry",
    response_model=GeometryResponse,
    summary="Generate geometry from shape + dimensions",
    description=(
        "Accepts a shape_type, project context, and a dimension payload. "
        "Runs TemplateResolver validation then GeometryBuilder to produce "
        "a fully computed GeometryModel with cut pieces and primitives."
    ),
    responses={
        404: {"description": "Shape type not found in registry"},
        422: {"description": "Dimension validation error (missing / out-of-range / bad option)"},
        400: {"description": "Shape type not yet implemented"},
    },
    status_code=200,
)
def create_geometry(request: GeometryRequest) -> GeometryResponse:
    """
    Full geometry generation pipeline:
        request → template lookup → resolver → builder → response
    """

    # ── 1. Template lookup ──────────────────────────────────────────────────
    template = SHAPE_REGISTRY.get(request.shape_type.lower())
    if template is None:
        available = ", ".join(sorted(SHAPE_REGISTRY.keys()))
        raise HTTPException(
            status_code=404,
            detail=f"Shape type '{request.shape_type}' not found. Available: {available}",
        )

    # ── 2. Parameter resolution + validation ────────────────────────────────
    resolved = _resolver.resolve(template, request.dimensions)
    if resolved.has_errors:
        error_response = ValidationErrorResponse(
            error="validation_error",
            detail=f"{len(resolved.errors)} parameter validation error(s).",
            errors=[
                ValidationErrorDetail(parameter=e.parameter, message=e.message)
                for e in resolved.errors
            ],
        )
        return JSONResponse(
            status_code=422,
            content=error_response.model_dump(),
        )

    # ── 3. Geometry build ───────────────────────────────────────────────────
    try:
        result = _builder.build(
            template=template,
            resolved=resolved,
            project_id=request.project_id,
            tenant_id=request.tenant_id,
        )
    except UnsupportedShapeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # ── 4. Map to response schema ───────────────────────────────────────────
    g = result.geometry

    pieces = [
        GeometryPieceResponse(
            piece_id=p.piece_id,
            label=p.label,
            width=p.width,
            length=p.length,
            thickness=p.thickness,
            area=p.area,
            notes=p.notes,
        )
        for p in g.pieces
    ]

    rectangles = [
        RectangleResponse(
            rect_id=r.rect_id,
            label=r.label,
            width=r.width,
            height=r.height,
            area=r.area,
            perimeter=r.perimeter,
            origin={"x": r.origin.x, "y": r.origin.y},
            center={"x": r.center.x, "y": r.center.y},
        )
        for r in result.rectangles
    ]

    dimension_lines = [
        DimensionLineResponse(
            dim_id=d.dim_id,
            value=d.value,
            unit=d.unit,
            display_text=d.display_text,
            start={"x": d.start.x, "y": d.start.y},
            end={"x": d.end.x, "y": d.end.y},
        )
        for d in result.dimension_lines
    ]

    return GeometryResponse(
        geometry_id=g.geometry_id,
        template_id=g.template_id,
        project_id=g.project_id,
        tenant_id=g.tenant_id,
        shape_type=request.shape_type.lower(),
        status=g.status.value,
        computed_area=g.computed_area,
        computed_perimeter=g.computed_perimeter,
        dimensions=g.dimensions,
        pieces=pieces,
        rectangles=rectangles,
        dimension_lines=dimension_lines,
        schema_version=g.schema_version,
    )
