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

Query parameters:
    download=true  → adds Content-Disposition: attachment, triggering file download.
                     Default (false) renders inline (browser-viewable).

HTTP status codes:
    200  – SVG generated; body is SVG text
    404  – shape_type not found in registry
    422  – dimension validation error (domain-level)
    400  – shape type not yet implemented
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, Response

from app.api.schemas import (
    GeometryRequest,
    ValidationErrorDetail,
    ValidationErrorResponse,
)
from app.exporters.svg_exporter import SvgExporter
from app.exporters.pdf_exporter import PdfExporter
from app.geometry.shapes import SHAPE_REGISTRY
from app.services.geometry_builder import GeometryBuilder, UnsupportedShapeError
from app.services.template_resolver import TemplateResolver
from app.tenant_context import get_current_tenant
from fastapi import Depends

router = APIRouter()

# Stateless service singletons
_resolver = TemplateResolver()
_builder  = GeometryBuilder()
_svg_exporter = SvgExporter()
_pdf_exporter = PdfExporter()


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
        "Response Content-Type is image/svg+xml. "
        "Add `?download=true` to receive the SVG as a file attachment."
    ),
    responses={
        200: {
            "content": {"image/svg+xml": {}},
            "description": "SVG drawing (inline or attachment)",
        },
        404: {"description": "Shape type not found in registry"},
        422: {"description": "Dimension validation error"},
        400: {"description": "Shape type not yet implemented"},
    },
    status_code=200,
)
def export_svg(
    request: GeometryRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    download: bool = Query(
        default=False,
        description=(
            "Set to true to return SVG as a downloadable file attachment "
            "instead of rendering inline in the browser."
        ),
    ),
) -> Response:
    """
    Full export pipeline:
        request → template lookup → resolver → builder → SVG exporter → response

    When download=true: Content-Disposition is 'attachment' (triggers download).
    When download=false (default): Content-Disposition is 'inline' (renders in browser).
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
            tenant_id=tenant_id,
        )
    except UnsupportedShapeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # ── 4. SVG export ───────────────────────────────────────────────────────
    svg_string = _svg_exporter.export(result)

    filename   = f"buildesk-{request.shape_type}.svg"
    disposition = f'attachment; filename="{filename}"' if download else f'inline; filename="{filename}"'

    return Response(
        content=svg_string,
        media_type="image/svg+xml",
        headers={
            "Content-Disposition": disposition,
            "Cache-Control": "no-store",
        },
    )

# ---------------------------------------------------------------------------
# POST /export/pdf
# ---------------------------------------------------------------------------

@router.post(
    "/export/pdf",
    summary="Generate PDF drawing from shape + dimensions",
    description=(
        "Accepts the same payload as POST /geometry. "
        "Runs the full geometry pipeline and returns a 8.5x11 PDF. "
        "Response Content-Type is application/pdf. "
        "Add `?download=true` to receive the PDF as a file attachment."
    ),
    responses={
        200: {"content": {"application/pdf": {}}, "description": "PDF drawing"},
        404: {"description": "Shape type not found in registry"},
        422: {"description": "Dimension validation error (domain-level)"},
        400: {"description": "Shape type not yet implemented"},
    },
    status_code=200,
)
def export_pdf(
    request: GeometryRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    download: bool = False
) -> Response:
    template = SHAPE_REGISTRY.get(request.shape_type.lower())
    if not template:
        raise HTTPException(status_code=404, detail=f"Shape '{request.shape_type}' not found.")

    resolve_res = _resolver.resolve(template, request.dimensions)
    if resolve_res.has_errors:
        raise HTTPException(
            status_code=422,
            detail={"message": "Validation failed", "errors": resolve_res.errors},
        )

    try:
        result = _builder.build(
            template=template,
            resolved=resolve_res,
            project_id=request.project_id,
            tenant_id=tenant_id,
        )
    except UnsupportedShapeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    pdf_bytes = _pdf_exporter.export(result, request.shape_type.lower())

    filename = f"buildesk-{request.shape_type}.pdf"
    disposition = f'attachment; filename="{filename}"' if download else f'inline; filename="{filename}"'

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": disposition,
            "Cache-Control": "no-store",
        },
    )
