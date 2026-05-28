"""
Demo Router
===========
Browser-accessible demo endpoints — no request body required.

Endpoints:
    GET /api/v1/demo/rectangle        → SVG of a standard 96" × 26" countertop
    GET /api/v1/demo/island           → SVG of a standard 72" × 36" island
    GET /api/v1/demo/vanity           → SVG of a standard 48" × 22" vanity with sink
    GET /api/v1/demo/straight-kitchen → SVG of a 180" × 26" kitchen (multi-piece)
    GET /api/v1/demo/l-kitchen        → SVG of a 120" × 96" L-shaped kitchen

Purpose:
    Frictionless demo path. Open a URL in a browser and immediately see
    a BuildDesk-generated drawing with no JSON payload needed.

Demo payloads are hardcoded with realistic countertop dimensions.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter
from fastapi.responses import Response

from app.exporters.svg_exporter import SvgExporter
from app.exporters.pdf_exporter import PdfExporter
from app.geometry.shapes import SHAPE_REGISTRY
from app.services.geometry_builder import GeometryBuilder
from app.services.template_resolver import TemplateResolver

router = APIRouter()

# ---------------------------------------------------------------------------
# Singletons
# ---------------------------------------------------------------------------

_resolver = TemplateResolver()
_builder  = GeometryBuilder()
_svg_exporter = SvgExporter(scale=4.0)
_pdf_exporter = PdfExporter()

# Stable demo UUIDs — same every request so responses are deterministic
_DEMO_PROJECT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
_DEMO_TENANT_ID  = uuid.UUID("00000000-0000-0000-0000-000000000002")

# Demo payloads: realistic production countertop dimensions
_DEMO_PAYLOADS = {
    "rectangle": {
        "length": 96.0,
        "width": 26.0,
        "thickness": 0.75,
        "label": "Standard Countertop",
    },
    "island": {
        "length": 72.0,
        "width": 36.0,
        "thickness": 0.75,
        "corner_radius": 2.0,
        "label": "Kitchen Island",
    },
    "vanity": {
        "length": 48.0,
        "width": 22.0,
        "thickness": 0.75,
        "backsplash_height": 4.0,
        "sink_cutout": True,
        "sink_diameter": 12.0,
        "label": "Bathroom Vanity",
    },
    "straight_kitchen": {
        "length": 180.0,
        "width": 26.0,
        "thickness": 0.75,
        "backsplash_height": 4.0,
        "seam_enabled": True,
        "slab_max_length": 120.0,
        "label": "Main Kitchen Run",
    },
    "l_kitchen": {
        "leg_a_length": 120.0,
        "leg_b_length": 96.0,
        "width": 26.0,
        "thickness": 1.18,
        "seam_enabled": True,
        "corner_join_type": "miter",
        "label": "L-Shape Layout",
    },
}


def _build_demo_svg(shape_type: str) -> str:
    """Run the full pipeline for a demo shape and return the SVG string."""
    template = SHAPE_REGISTRY[shape_type]
    dims     = _DEMO_PAYLOADS[shape_type]
    resolved = _resolver.resolve(template, dims)
    result   = _builder.build(
        template=template,
        resolved=resolved,
        project_id=_DEMO_PROJECT_ID,
        tenant_id=_DEMO_TENANT_ID,
    )
    return _svg_exporter.export(result)


def _svg_response(shape_type: str) -> Response:
    svg = _build_demo_svg(shape_type)
    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={
            "Content-Disposition": f'inline; filename="demo-{shape_type}.svg"',
            "Cache-Control": "no-store",
            "X-BuildDesk-Demo": "true",
        },
    )


def _pdf_response(shape_type: str) -> Response:
    """Helper to generate PDF for a demo payload."""
    payload = _DEMO_PAYLOADS.get(shape_type)
    template = SHAPE_REGISTRY.get(shape_type)
    resolved = _resolver.resolve(template, payload)
    result   = _builder.build(
        template=template,
        resolved=resolved,
        project_id=_DEMO_PROJECT_ID,
        tenant_id=_DEMO_TENANT_ID,
    )
    pdf_bytes = _pdf_exporter.export(result, shape_type)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="demo-{shape_type}.pdf"',
            "Cache-Control": "no-store",
            "X-BuildDesk-Demo": "true",
        },
    )


# ---------------------------------------------------------------------------
# GET /demo/rectangle
# ---------------------------------------------------------------------------

@router.get(
    "/demo/rectangle",
    summary="Rectangle demo drawing",
    description=(
        "Returns a pre-built SVG of a standard 96\" × 26\" countertop. "
        "Open directly in a browser — no request body required."
    ),
    responses={200: {"content": {"image/svg+xml": {}}, "description": "Demo SVG"}},
    status_code=200,
)
def demo_rectangle() -> Response:
    """Render the rectangle demo SVG inline."""
    return _svg_response("rectangle")


# ---------------------------------------------------------------------------
# GET /demo/island
# ---------------------------------------------------------------------------

@router.get(
    "/demo/island",
    summary="Island demo drawing",
    description=(
        "Returns a pre-built SVG of a standard 72\" × 36\" kitchen island. "
        "Open directly in a browser — no request body required."
    ),
    responses={200: {"content": {"image/svg+xml": {}}, "description": "Demo SVG"}},
    status_code=200,
)
def demo_island() -> Response:
    """Render the island demo SVG inline."""
    return _svg_response("island")


# ---------------------------------------------------------------------------
# GET /demo/vanity
# ---------------------------------------------------------------------------

@router.get(
    "/demo/vanity",
    summary="Vanity demo drawing",
    description=(
        "Returns a pre-built SVG of a standard 48\" × 22\" bathroom vanity "
        "with a 4\" backsplash and a 15\" sink cutout. "
        "Open directly in a browser — no request body required."
    ),
    responses={200: {"content": {"image/svg+xml": {}}, "description": "Demo SVG"}},
    status_code=200,
)
def demo_vanity() -> Response:
    """Render the vanity demo SVG inline."""
    return _svg_response("vanity")


# ---------------------------------------------------------------------------
# GET /demo/straight-kitchen
# ---------------------------------------------------------------------------

@router.get(
    "/demo/straight-kitchen",
    summary="Straight Kitchen demo drawing",
    description=(
        "Returns a pre-built SVG of a 180\" × 26\" straight kitchen run. "
        "Demonstrates multi-piece fabrication logic with seams. "
        "Open directly in a browser — no request body required."
    ),
    responses={200: {"content": {"image/svg+xml": {}}, "description": "Demo SVG"}},
    status_code=200,
)
def demo_straight_kitchen() -> Response:
    """Render the straight kitchen demo SVG inline."""
    return _svg_response("straight_kitchen")


# ---------------------------------------------------------------------------
# GET /demo/l-kitchen
# ---------------------------------------------------------------------------

@router.get(
    "/demo/l-kitchen",
    summary="L-Kitchen demo drawing",
    description=(
        "Returns a pre-built SVG of a 120\" × 96\" L-shaped kitchen. "
        "Demonstrates corner join logic (miter) and seam splitting. "
        "Open directly in a browser — no request body required."
    ),
    responses={200: {"content": {"image/svg+xml": {}}, "description": "Demo SVG"}},
    status_code=200,
)
def demo_l_kitchen() -> Response:
    """Render the L-kitchen demo SVG inline."""
    return _svg_response("l_kitchen")

# ---------------------------------------------------------------------------
# PDF Endpoints
# ---------------------------------------------------------------------------

@router.get("/demo/pdf/rectangle", responses={200: {"content": {"application/pdf": {}}}})
def demo_pdf_rectangle() -> Response:
    return _pdf_response("rectangle")

@router.get("/demo/pdf/island", responses={200: {"content": {"application/pdf": {}}}})
def demo_pdf_island() -> Response:
    return _pdf_response("island")

@router.get("/demo/pdf/vanity", responses={200: {"content": {"application/pdf": {}}}})
def demo_pdf_vanity() -> Response:
    return _pdf_response("vanity")

@router.get("/demo/pdf/straight-kitchen", responses={200: {"content": {"application/pdf": {}}}})
def demo_pdf_straight_kitchen() -> Response:
    return _pdf_response("straight_kitchen")

@router.get("/demo/pdf/l-kitchen", responses={200: {"content": {"application/pdf": {}}}})
def demo_pdf_l_kitchen() -> Response:
    return _pdf_response("l_kitchen")
