"""
Geometry Builder
================
Service that takes a ShapeTemplate + resolved parameters and produces
a fully populated GeometryModel with GeometryPiece entries and
computed primitives (Rectangle, DimensionLine, TextAnnotation).

Architecture position:
    TemplateResolver → ResolvedDimensions
                            ↓
                    GeometryBuilder
                            ↓
                    GeometryModel  (source of truth)
                            ↓
                   [Output Engines]  (PDF, reports — future)

This module is intentionally free of:
    - database I/O
    - HTTP / FastAPI concerns
    - SVG / PDF / DXF rendering
    - frontend logic

Shape dispatch table:
    "rectangle"       → _build_rectangle   ← MVP, implemented
    "island"          → future
    "vanity"          → future
    "straight_kitchen"→ future
    "l_kitchen"       → future

Usage::

    resolver = TemplateResolver()
    builder  = GeometryBuilder()

    resolved = resolver.resolve(template, payload)
    if resolved.has_errors:
        raise ValueError(resolved.errors)

    geometry = builder.build(
        template=template,
        resolved=resolved,
        project_id=project_id,
        tenant_id=tenant_id,
    )
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List

from app.geometry.primitives import (
    DimensionLine,
    Point,
    Rectangle,
    TextAnnotation,
)
from app.models.geometry import GeometryModel, GeometryPiece, GeometryStatus
from app.models.shape_template import ShapeTemplate
from app.services.template_resolver import ResolvedDimensions


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class GeometryBuildError(Exception):
    """Raised when the geometry builder cannot process the given inputs."""


class UnsupportedShapeError(GeometryBuildError):
    """Raised when shape_type has no registered handler."""


# ---------------------------------------------------------------------------
# Build result
# ---------------------------------------------------------------------------

class GeometryBuildResult:
    """
    Full output of one geometry build pass.

    Attributes:
        geometry    – populated GeometryModel (status=computed)
        rectangles  – list of Rectangle primitives produced
        dimensions  – list of DimensionLine primitives produced
        annotations – list of TextAnnotation primitives produced

    Primitives are stored here (not on GeometryModel) because the
    domain model stays clean; output engines receive this result
    and decide what to render.
    """

    def __init__(
        self,
        geometry: GeometryModel,
        rectangles: List[Rectangle],
        dimension_lines: List[DimensionLine],
        annotations: List[TextAnnotation],
    ) -> None:
        self.geometry = geometry
        self.rectangles = rectangles
        self.dimension_lines = dimension_lines
        self.annotations = annotations

    def __repr__(self) -> str:
        return (
            f"GeometryBuildResult("
            f"geometry_id={self.geometry.geometry_id}, "
            f"pieces={len(self.geometry.pieces)}, "
            f"rects={len(self.rectangles)}, "
            f"dims={len(self.dimension_lines)}, "
            f"annotations={len(self.annotations)})"
        )


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------

class GeometryBuilder:
    """
    Stateless service that produces a GeometryModel from a resolved
    parameter set and a ShapeTemplate.

    Shape dispatch is driven by ShapeTemplate.category and the
    optional 'shape_type' metadata key in the template. Handlers
    are registered in the _DISPATCH table at class level.

    Extending to a new shape:
        1. Add a handler method: _build_<shape_name>
        2. Register it in _DISPATCH

    Instantiate once and reuse; no mutable state is held.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(
        self,
        template: ShapeTemplate,
        resolved: ResolvedDimensions,
        project_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> GeometryBuildResult:
        """
        Build a GeometryModel from resolved parameters.

        Args:
            template:   The ShapeTemplate that defines the shape.
            resolved:   Output of TemplateResolver.resolve() — must not have errors.
            project_id: Parent project UUID.
            tenant_id:  Owning tenant UUID.

        Returns:
            GeometryBuildResult with a computed GeometryModel and primitives.

        Raises:
            GeometryBuildError:   if resolved.has_errors is True.
            UnsupportedShapeError: if the template's shape_type is not handled.
        """
        if resolved.has_errors:
            raise GeometryBuildError(
                f"Cannot build geometry from a resolution with errors: {resolved.errors}"
            )

        shape_type = self._detect_shape_type(template)
        handler = self._DISPATCH.get(shape_type)

        if handler is None:
            supported = ", ".join(sorted(self._DISPATCH.keys()))
            raise UnsupportedShapeError(
                f"Shape type '{shape_type}' has no registered handler. "
                f"Supported: {supported}"
            )

        return handler(self, template, resolved.dimensions, project_id, tenant_id)

    # ------------------------------------------------------------------
    # Shape type detection
    # ------------------------------------------------------------------

    def _detect_shape_type(self, template: ShapeTemplate) -> str:
        """
        Determine the shape_type to dispatch on.

        Priority:
            1. template.metadata["shape_type"] if present
            2. Infer from template.name (lowercase, spaces→underscores)
            3. Fall back to template.category value
        """
        # Check metadata override
        meta_type = getattr(template, "metadata", {})
        if isinstance(meta_type, dict) and "shape_type" in meta_type:
            return meta_type["shape_type"].lower()

        # Infer from name
        name_slug = template.name.lower().replace(" ", "_").replace("-", "_")
        for key in self._DISPATCH:
            if key in name_slug:
                return key

        # Fall back to category
        return template.category.value

    # ------------------------------------------------------------------
    # Shape handlers
    # ------------------------------------------------------------------

    def _build_rectangle(
        self,
        template: ShapeTemplate,
        dims: Dict[str, Any],
        project_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> GeometryBuildResult:
        """
        Build geometry for a simple rectangle shape.

        Required parameters:
            length  – the longer horizontal dimension (inches)
            width   – the shorter depth dimension (inches)

        Optional parameters:
            thickness – slab thickness (inches); defaults to 0.75" (3/4 slab)
            label     – piece name override

        Produces:
            - 1 GeometryPiece (the countertop slab)
            - 1 Rectangle primitive at origin (0, 0)
            - 2 DimensionLines (length along bottom, width along left)
            - 1 TextAnnotation (piece label at centre)
        """
        length    = float(dims["length"])
        width     = float(dims["width"])
        thickness = float(dims.get("thickness", 0.75))
        label     = str(dims.get("label", template.name))

        area = length * width

        # ── GeometryPiece ───────────────────────────────────────────────
        piece = GeometryPiece(
            label=label,
            width=width,
            length=length,
            thickness=thickness,
            area=area,
            notes=f"Single slab: {length}\" × {width}\" × {thickness}\"",
        )

        # ── GeometryModel ───────────────────────────────────────────────
        geometry = GeometryModel(
            project_id=project_id,
            tenant_id=tenant_id,
            template_id=template.template_id,
            dimensions=dict(dims),
            status=GeometryStatus.computed,
            pieces=[piece],
            computed_area=area,
            computed_perimeter=2 * (length + width),
        )

        # ── Primitives ───────────────────────────────────────────────────
        origin = Point(x=0.0, y=0.0)
        rect   = Rectangle(
            origin=origin,
            width=length,
            height=width,
            label=label,
        )

        # Dimension: length (horizontal, below the slab)
        dim_length = DimensionLine(
            start=Point(x=0.0,    y=0.0),
            end=  Point(x=length, y=0.0),
            value=length,
            unit="in",
            label=f"{length}\"",
            offset=-1.0,
        )

        # Dimension: width (vertical, left of the slab)
        dim_width = DimensionLine(
            start=Point(x=0.0, y=0.0),
            end=  Point(x=0.0, y=width),
            value=width,
            unit="in",
            label=f"{width}\"",
            offset=-1.0,
        )

        # Centre label annotation
        centre = rect.center
        annotation = TextAnnotation(
            position=centre,
            text=label,
            font_size=14.0,
            bold=True,
            label="piece_label",
        )

        return GeometryBuildResult(
            geometry=geometry,
            rectangles=[rect],
            dimension_lines=[dim_length, dim_width],
            annotations=[annotation],
        )

    # ------------------------------------------------------------------
    # Future shape stubs (not yet implemented)
    # ------------------------------------------------------------------

    def _build_island(self, template, dims, project_id, tenant_id):
        raise UnsupportedShapeError("Island shape handler not yet implemented.")

    def _build_vanity(self, template, dims, project_id, tenant_id):
        raise UnsupportedShapeError("Vanity shape handler not yet implemented.")

    def _build_straight_kitchen(self, template, dims, project_id, tenant_id):
        raise UnsupportedShapeError("Straight kitchen shape handler not yet implemented.")

    def _build_l_kitchen(self, template, dims, project_id, tenant_id):
        raise UnsupportedShapeError("L-kitchen shape handler not yet implemented.")

    # ------------------------------------------------------------------
    # Dispatch table
    # ------------------------------------------------------------------

    _DISPATCH = {
        "rectangle":        _build_rectangle,
        "island":           _build_island,
        "vanity":           _build_vanity,
        "straight_kitchen": _build_straight_kitchen,
        "l_kitchen":        _build_l_kitchen,
    }
