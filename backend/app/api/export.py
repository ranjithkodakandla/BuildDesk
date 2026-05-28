"""
Export Router
=============
HTTP endpoints for BuildDesk drawing exports.

Endpoints:
    POST /api/v1/export/svg

Pipeline:
    GeometryRequest (same body as POST /geometry)
        → ShapeTemplate lookup
        → TemplateResolver
        → GeometryBuilder
        → SvgExporter
        → SVG Response (Content-Type: image/svg+xml)

HTTP status codes:
    200  – SVG generated; body is SVG text
    404  – shape_type not found in registry
    422  – dimension validation error (domain-level)
    400  – shape type not yet implemented
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, Response

from app.api.schemas import (
    GeometryRequest,
    ValidationErrorDetail,
    ValidationErrorResponse,
)
from app.exporters.svg_exporter import SvgExporter
from app.geometry.shapes import SHAPE_REGISTRY
from app.services.geometry_builder import GeometryBuilder, UnsupportedShapeError
from app.services.template_resolver import TemplateResolver

router = APIRouter()

# Stateless service singletons
_resolver = TemplateResolver()
_builder  = GeometryBuilder()
_exporter = SvgExporter()


# ---------------------------------------------------------------------------
# POST /export/svg
# ---------------------------------------------------------------------------

@router.post(
    "/export/svg",
    summary="Generate SVG drawing from shape + dimensions",
    description=(
        "Accepts the same payload as POST /geometry. "
        "Runs the full geometry pipeline and returns a self-contained SVG "
        "string with the shape outline, dimension lines, and annotations. "
        "Response Content-Type is image/svg+xml."
    ),
    responses={
        200: {
            "content": {"image/svg+xml": {}},
            "description": "SVG drawing",
        },
        404: {"description": "Shape type not found in registry"},
        422: {"description": "Dimension validation error"},
        400: {"description": "Shape type not yet implemented"},
    },
    status_code=200,
)
def export_svg(request: GeometryRequest) -> Response:
    """
    Full export pipeline:
        request → template lookup → resolver → builder → SVG exporter → response
    """

    # ── 1. Template lookup ──────────────────────────────────────────────────
    template = SHAPE_REGISTRY.get(request.shape_type.lower())
    if template is None:
        available = ", ".join(sorted(SHAPE_REGISTRY.keys()))
        raise HTTPException(
            status_code=404,
            detail=f"Shape type '{request.shape_type}' not found. Available: {available}",
        )

    # ── 2. Parameter resolution ─────────────────────────────────────────────
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
        return JSONResponse(status_code=422, content=error_response.model_dump())

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

    # ── 4. SVG export ───────────────────────────────────────────────────────
    svg_string = _exporter.export(result)

    return Response(
        content=svg_string,
        media_type="image/svg+xml",
        headers={
            "Content-Disposition": (
                f'inline; filename="buildesk-{request.shape_type}.svg"'
            ),
            "Cache-Control": "no-store",
        },
    )
