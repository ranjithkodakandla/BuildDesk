"""
Shape Library — Seed Templates
================================
System-level (global) ShapeTemplate definitions for the BuildDesk
MVP shape library.

Shapes defined here:
    RECTANGLE_TEMPLATE  – simple rectangular countertop slab

Future shapes (not yet implemented):
    ISLAND_TEMPLATE
    VANITY_TEMPLATE
    STRAIGHT_KITCHEN_TEMPLATE
    L_KITCHEN_TEMPLATE

These templates are system_template=True (available to all tenants).
They are pure in-memory fixtures for Phase 1. In Phase 2 they will be
seeded into Cloud SQL on first startup.

Usage::

    from app.geometry.shapes import RECTANGLE_TEMPLATE

    resolved = resolver.resolve(RECTANGLE_TEMPLATE, {"length": 96, "width": 42})
    result   = builder.build(RECTANGLE_TEMPLATE, resolved, project_id, tenant_id)
"""

from __future__ import annotations

from app.models.shape_template import (
    DimensionUnit,
    ShapeCategory,
    ShapeParameter,
    ShapeParameterType,
    ShapeTemplate,
)

# ---------------------------------------------------------------------------
# Rectangle — MVP shape
# ---------------------------------------------------------------------------

RECTANGLE_TEMPLATE = ShapeTemplate(
    name="Rectangle",
    category=ShapeCategory.custom,
    system_template=True,
    description="Simple rectangular countertop slab. Single piece, two dimensions.",
    parameters=[
        ShapeParameter(
            name="length",
            label="Length",
            parameter_type=ShapeParameterType.number,
            unit=DimensionUnit.inches,
            min_value=6.0,
            max_value=480.0,
            required=True,
            description="Longest dimension of the slab",
        ),
        ShapeParameter(
            name="width",
            label="Width (depth)",
            parameter_type=ShapeParameterType.number,
            unit=DimensionUnit.inches,
            min_value=6.0,
            max_value=72.0,
            required=True,
            description="Shorter dimension (counter depth)",
        ),
        ShapeParameter(
            name="thickness",
            label="Thickness",
            parameter_type=ShapeParameterType.number,
            unit=DimensionUnit.inches,
            min_value=0.25,
            max_value=4.0,
            default_value=0.75,
            required=False,
            description="Slab thickness; defaults to 3/4\" (standard)",
        ),
        ShapeParameter(
            name="label",
            label="Piece label",
            parameter_type=ShapeParameterType.string,
            required=False,
            description="Custom piece name shown on output packages",
        ),
    ],
)

# ---------------------------------------------------------------------------
# Future stubs (not yet implemented — placeholders for dispatch table)
# ---------------------------------------------------------------------------

# ISLAND_TEMPLATE          = ...
# VANITY_TEMPLATE          = ...
# STRAIGHT_KITCHEN_TEMPLATE = ...
# L_KITCHEN_TEMPLATE       = ...

# ---------------------------------------------------------------------------
# Registry: shape_type slug → template
# ---------------------------------------------------------------------------

SHAPE_REGISTRY: dict[str, ShapeTemplate] = {
    "rectangle": RECTANGLE_TEMPLATE,
}
