"""
Shape Library — Seed Templates
================================
System-level (global) ShapeTemplate definitions for the BuildDesk
MVP shape library.

Shapes defined here:
    RECTANGLE_TEMPLATE  – simple rectangular countertop slab
    ISLAND_TEMPLATE     – kitchen island (all 4 edges exposed)
    VANITY_TEMPLATE     – wall-mounted bathroom vanity (3 edges exposed, optional sink)

Future shapes (not yet implemented):
    STRAIGHT_KITCHEN_TEMPLATE
    L_KITCHEN_TEMPLATE

These templates are system_template=True (available to all tenants).
They are pure in-memory fixtures for Phase 1. In Phase 2 they will be
seeded into Cloud SQL on first startup.

Usage::

    from app.geometry.shapes import ISLAND_TEMPLATE, SHAPE_REGISTRY

    resolved = resolver.resolve(ISLAND_TEMPLATE, {"length": 96, "width": 42})
    result   = builder.build(ISLAND_TEMPLATE, resolved, project_id, tenant_id)
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
# Island — all 4 edges exposed
# ---------------------------------------------------------------------------

ISLAND_TEMPLATE = ShapeTemplate(
    name="Island",
    category=ShapeCategory.island,
    system_template=True,
    description=(
        "Kitchen island countertop — freestanding, all four edges exposed/finished. "
        "Supports optional corner radius for rounded corners."
    ),
    parameters=[
        ShapeParameter(
            name="length",
            label="Length",
            parameter_type=ShapeParameterType.number,
            unit=DimensionUnit.inches,
            min_value=12.0,
            max_value=480.0,
            required=True,
            description="Longest dimension of the island",
        ),
        ShapeParameter(
            name="width",
            label="Width",
            parameter_type=ShapeParameterType.number,
            unit=DimensionUnit.inches,
            min_value=12.0,
            max_value=120.0,
            required=True,
            description="Width of the island (both sides accessible)",
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
            description="Slab thickness; defaults to 3/4\"",
        ),
        ShapeParameter(
            name="corner_radius",
            label="Corner radius",
            parameter_type=ShapeParameterType.number,
            unit=DimensionUnit.inches,
            min_value=0.0,
            max_value=12.0,
            default_value=0.0,
            required=False,
            description="Rounded corner radius (0 = square corners)",
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
# Vanity — wall-mounted, 3 exposed edges, optional sink cutout
# ---------------------------------------------------------------------------

VANITY_TEMPLATE = ShapeTemplate(
    name="Vanity",
    category=ShapeCategory.bathroom,
    system_template=True,
    description=(
        "Wall-mounted bathroom vanity countertop. "
        "Three edges are exposed and finished (front, left, right); "
        "the back edge sits flush against the wall. "
        "Supports optional backsplash and sink cutout."
    ),
    parameters=[
        ShapeParameter(
            name="length",
            label="Length",
            parameter_type=ShapeParameterType.number,
            unit=DimensionUnit.inches,
            min_value=12.0,
            max_value=240.0,
            required=True,
            description="Horizontal span of the vanity top",
        ),
        ShapeParameter(
            name="width",
            label="Width (depth)",
            parameter_type=ShapeParameterType.number,
            unit=DimensionUnit.inches,
            min_value=10.0,
            max_value=36.0,
            required=True,
            description="Front-to-back depth of the vanity top",
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
            description="Slab thickness; defaults to 3/4\"",
        ),
        ShapeParameter(
            name="backsplash_height",
            label="Backsplash height",
            parameter_type=ShapeParameterType.number,
            unit=DimensionUnit.inches,
            min_value=0.0,
            max_value=24.0,
            default_value=0.0,
            required=False,
            description="Height of the integrated backsplash (0 = no backsplash)",
        ),
        ShapeParameter(
            name="sink_cutout",
            label="Include sink cutout",
            parameter_type=ShapeParameterType.boolean,
            default_value=False,
            required=False,
            description="If true, a sink cutout circle is generated at the vanity centre",
        ),
        ShapeParameter(
            name="sink_diameter",
            label="Sink diameter",
            parameter_type=ShapeParameterType.number,
            unit=DimensionUnit.inches,
            min_value=8.0,
            max_value=24.0,
            default_value=15.0,
            required=False,
            description="Diameter of the sink cutout (only used when sink_cutout=true)",
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
# Future stubs (not yet implemented)
# ---------------------------------------------------------------------------

# STRAIGHT_KITCHEN_TEMPLATE = ...
# L_KITCHEN_TEMPLATE       = ...

# ---------------------------------------------------------------------------
# Registry: shape_type slug → template
# ---------------------------------------------------------------------------

SHAPE_REGISTRY: dict[str, ShapeTemplate] = {
    "rectangle": RECTANGLE_TEMPLATE,
    "island":    ISLAND_TEMPLATE,
    "vanity":    VANITY_TEMPLATE,
}
