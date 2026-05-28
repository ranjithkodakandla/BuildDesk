"""
Demo Router
===========
Browser-accessible demo endpoints — no request body required.

Endpoints:
    GET /api/v1/demo/rectangle   → SVG of a standard 96" × 26" countertop
    GET /api/v1/demo/island      → SVG of a standard 72" × 36" island

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
from app.geometry.shapes import SHAPE_REGISTRY
from app.services.geometry_builder import GeometryBuilder
from app.services.template_resolver import TemplateResolver

router = APIRouter()

# ---------------------------------------------------------------------------
# Singletons
# ---------------------------------------------------------------------------

_resolver = TemplateResolver()
_builder  = GeometryBuilder()
_exporter = SvgExporter(scale=4.0)

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
    return _exporter.export(result)


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
