"""
Shapes Router
=============
HTTP endpoints for the BuildDesk shape library.

Endpoints:
    GET /api/v1/shapes              – list all available shape templates
    GET /api/v1/shapes/{shape_type} – retrieve a single template definition

These endpoints are read-only; templates are seeded in memory (Phase 1).
In Phase 2 they will be served from Cloud SQL.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.schemas import (
    ShapeListItemResponse,
    ShapeListResponse,
    ShapeParameterResponse,
    ShapeTemplateResponse,
)
from app.geometry.shapes import SHAPE_REGISTRY

router = APIRouter()


# ---------------------------------------------------------------------------
# GET /shapes
# ---------------------------------------------------------------------------

@router.get(
    "/shapes",
    response_model=ShapeListResponse,
    summary="List available shape templates",
    description=(
        "Returns all shape templates available in the BuildDesk shape library. "
        "Each entry includes the shape_type slug, name, category, and parameter count."
    ),
)
def list_shapes() -> ShapeListResponse:
    """Return all templates in SHAPE_REGISTRY as a compact list."""
    items = [
        ShapeListItemResponse(
            shape_type=slug,
            template_id=tmpl.template_id,
            name=tmpl.name,
            category=tmpl.category.value,
            description=tmpl.description,
            parameter_count=len(tmpl.parameters),
        )
        for slug, tmpl in SHAPE_REGISTRY.items()
    ]
    return ShapeListResponse(shapes=items, total=len(items))


# ---------------------------------------------------------------------------
# GET /shapes/{shape_type}
# ---------------------------------------------------------------------------

@router.get(
    "/shapes/{shape_type}",
    response_model=ShapeTemplateResponse,
    summary="Get a single shape template",
    description=(
        "Returns the full parameter schema for the requested shape type. "
        "Use the `parameters` list to build a dimension input form. "
        "Returns 404 if shape_type is not found."
    ),
    responses={
        404: {"description": "Shape type not found in the registry"},
    },
)
def get_shape(shape_type: str) -> ShapeTemplateResponse:
    """Retrieve full template definition by shape_type slug."""
    tmpl = SHAPE_REGISTRY.get(shape_type.lower())
    if tmpl is None:
        available = ", ".join(sorted(SHAPE_REGISTRY.keys()))
        raise HTTPException(
            status_code=404,
            detail=f"Shape type '{shape_type}' not found. Available: {available}",
        )

    params = [
        ShapeParameterResponse(
            name=p.name,
            label=p.label,
            parameter_type=p.parameter_type.value,
            unit=p.unit.value,
            required=p.required,
            min_value=p.min_value,
            max_value=p.max_value,
            default_value=p.default_value,
            allowed_options=p.allowed_options,
            description=p.description,
        )
        for p in tmpl.parameters
    ]

    return ShapeTemplateResponse(
        template_id=tmpl.template_id,
        name=tmpl.name,
        category=tmpl.category.value,
        description=tmpl.description,
        system_template=tmpl.system_template,
        schema_version=tmpl.schema_version,
        parameters=params,
    )
