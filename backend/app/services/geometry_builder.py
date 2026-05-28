"""
Geometry Builder
================
Service that takes a ShapeTemplate + resolved parameters and produces
a fully populated GeometryModel with GeometryPiece entries and
computed primitives (Rectangle, Polyline, DimensionLine, TextAnnotation).

Architecture position:
    TemplateResolver → ResolvedDimensions
                            ↓
                    GeometryBuilder
                            ↓
                    GeometryModel  (source of truth)
                            ↓
                   [Output Engines]  (SVG, PDF — future)

This module is intentionally free of:
    - database I/O
    - HTTP / FastAPI concerns
    - SVG / PDF / DXF rendering
    - frontend logic

Shape dispatch table:
    "rectangle"       → _build_rectangle   ← implemented
    "island"          → _build_island       ← implemented
    "vanity"          → stub (future)
    "straight_kitchen"→ stub (future)
    "l_kitchen"       → stub (future)

Adding a new shape:
    1. Add handler: _build_<shape_name>(self, template, dims, project_id, tenant_id)
    2. Register it in _DISPATCH
    3. Add template to geometry/shapes.py + SHAPE_REGISTRY

Usage::

    resolver = TemplateResolver()
    builder  = GeometryBuilder()

    resolved = resolver.resolve(template, payload)
    if resolved.has_errors:
        raise ValueError(resolved.errors)

    result = builder.build(
        template=template,
        resolved=resolved,
        project_id=project_id,
        tenant_id=tenant_id,
    )
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from app.geometry.primitives import (
    Circle,
    DimensionLine,
    Line,
    Point,
    Polyline,
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
        geometry       – populated GeometryModel (status=computed)
        rectangles     – Rectangle primitives
        polylines      – Polyline primitives (used for complex outlines)
        dimension_lines – DimensionLine primitives
        annotations    – TextAnnotation primitives
        lines          – loose Line primitives (optional)
        circles        – Circle primitives (optional)

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
        polylines: Optional[List[Polyline]] = None,
        lines: Optional[List[Line]] = None,
        circles: Optional[List[Circle]] = None,
    ) -> None:
        self.geometry        = geometry
        self.rectangles      = rectangles
        self.dimension_lines = dimension_lines
        self.annotations     = annotations
        self.polylines       = polylines or []
        self.lines           = lines or []
        self.circles         = circles or []

    def __repr__(self) -> str:
        return (
            f"GeometryBuildResult("
            f"geometry_id={self.geometry.geometry_id}, "
            f"pieces={len(self.geometry.pieces)}, "
            f"rects={len(self.rectangles)}, "
            f"polys={len(self.polylines)}, "
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

    Shape dispatch is driven by the optional 'shape_type' metadata key
    in the template, then inferred from the template name, then the category.
    Handlers are registered in the _DISPATCH table at class level.

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
            GeometryBuildError:    if resolved.has_errors is True.
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
        # 1. Explicit metadata override
        meta = getattr(template, "metadata", {})
        if isinstance(meta, dict) and "shape_type" in meta:
            return meta["shape_type"].lower()

        # 2. Infer from name slug
        name_slug = template.name.lower().replace(" ", "_").replace("-", "_")
        for key in self._DISPATCH:
            if key in name_slug:
                return key

        # 3. Fall back to category
        return template.category.value

    # ------------------------------------------------------------------
    # ── Handler: Rectangle ──────────────────────────────────────────────
    # ------------------------------------------------------------------

    def _build_rectangle(
        self,
        template: ShapeTemplate,
        dims: Dict[str, Any],
        project_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> GeometryBuildResult:
        """
        Build geometry for a simple rectangular countertop slab.

        Required parameters:
            length    – longest horizontal dimension (inches)
            width     – shorter depth dimension (inches)

        Optional parameters:
            thickness – slab thickness (inches); defaults to 0.75" (3/4 slab)
            label     – piece name override

        Produces:
            - 1 GeometryPiece
            - 1 Rectangle primitive at origin (0, 0)
            - 2 DimensionLines (length bottom, width left)
            - 1 TextAnnotation at centre
        """
        length    = float(dims["length"])
        width     = float(dims["width"])
        thickness = float(dims.get("thickness", 0.75))
        label     = str(dims.get("label", template.name))
        area      = length * width

        piece = GeometryPiece(
            label=label,
            width=width,
            length=length,
            thickness=thickness,
            area=area,
            notes=f"Single slab: {length}\" × {width}\" × {thickness}\"",
        )

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

        origin = Point(x=0.0, y=0.0)
        rect   = Rectangle(origin=origin, width=length, height=width, label=label)

        dim_length = DimensionLine(
            start=Point(x=0.0,    y=0.0),
            end=  Point(x=length, y=0.0),
            value=length, unit="in", label=f"{length}\"", offset=-1.0,
        )
        dim_width = DimensionLine(
            start=Point(x=0.0, y=0.0),
            end=  Point(x=0.0, y=width),
            value=width,  unit="in", label=f"{width}\"",  offset=-1.0,
        )

        annotation = TextAnnotation(
            position=rect.center,
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
    # ── Handler: Island ─────────────────────────────────────────────────
    # ------------------------------------------------------------------

    def _build_island(
        self,
        template: ShapeTemplate,
        dims: Dict[str, Any],
        project_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> GeometryBuildResult:
        """
        Build geometry for a kitchen island countertop.

        An island is a freestanding rectangle accessible from all four sides,
        so all four edges are finished (exposed) — represented by a closed Polyline
        outline rather than a simple Rectangle to signal "all edges visible".

        Required parameters:
            length        – longest dimension (inches)
            width         – shorter dimension (inches)

        Optional parameters:
            thickness     – slab thickness (inches); defaults to 0.75"
            corner_radius – rounded corner radius (inches); stored in metadata
            label         – piece name override

        Produces:
            - 1 GeometryPiece (full slab)
            - 1 closed Polyline outline (4 corners — all edges exposed)
            - 1 Rectangle primitive (for bounding-box calculations)
            - 4 DimensionLines:
                length bottom, length top, width left, width right
            - 1 TextAnnotation at centre
        """
        length        = float(dims["length"])
        width         = float(dims["width"])
        thickness     = float(dims.get("thickness", 0.75))
        corner_radius = float(dims.get("corner_radius", 0.0))
        label         = str(dims.get("label", template.name))
        area          = length * width
        perimeter     = 2 * (length + width)

        # ── GeometryPiece ───────────────────────────────────────────────
        piece = GeometryPiece(
            label=label,
            width=width,
            length=length,
            thickness=thickness,
            area=area,
            notes=(
                f"Island slab: {length}\" × {width}\" × {thickness}\". "
                f"All 4 edges exposed."
                + (f" Corner radius: {corner_radius}\"." if corner_radius else "")
            ),
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
            computed_perimeter=perimeter,
            metadata={
                "corner_radius": corner_radius,
                "exposed_edges": ["bottom", "right", "top", "left"],
            },
        )

        # ── Closed Polyline outline (all 4 edges exposed) ────────────────
        # Counter-clockwise: BL → BR → TR → TL → (back to BL via closed=True)
        outline = Polyline(
            points=[
                Point(x=0.0,    y=0.0),    # bottom-left
                Point(x=length, y=0.0),    # bottom-right
                Point(x=length, y=width),  # top-right
                Point(x=0.0,    y=width),  # top-left
            ],
            closed=True,
            label=f"{label} outline",
            metadata={
                "corner_radius": corner_radius,
                "edge_type": "all_exposed",
            },
        )

        # ── Rectangle (for bounding box / area calcs / SVG fallback) ────
        rect = Rectangle(
            origin=Point(x=0.0, y=0.0),
            width=length,
            height=width,
            label=label,
            metadata={"role": "bounding_box"},
        )

        # ── 4 DimensionLines (all four sides of the island) ──────────────
        # Bottom: length
        dim_bottom = DimensionLine(
            start=Point(x=0.0,    y=0.0),
            end=  Point(x=length, y=0.0),
            value=length, unit="in", label=f"{length}\"",
            offset=-1.0,
        )
        # Top: length
        dim_top = DimensionLine(
            start=Point(x=0.0,    y=width),
            end=  Point(x=length, y=width),
            value=length, unit="in", label=f"{length}\"",
            offset=1.0,
        )
        # Left: width
        dim_left = DimensionLine(
            start=Point(x=0.0, y=0.0),
            end=  Point(x=0.0, y=width),
            value=width, unit="in", label=f"{width}\"",
            offset=-1.0,
        )
        # Right: width
        dim_right = DimensionLine(
            start=Point(x=length, y=0.0),
            end=  Point(x=length, y=width),
            value=width, unit="in", label=f"{width}\"",
            offset=1.0,
        )

        # ── TextAnnotation at centre ─────────────────────────────────────
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
            polylines=[outline],
            dimension_lines=[dim_bottom, dim_top, dim_left, dim_right],
            annotations=[annotation],
        )

    # ------------------------------------------------------------------
    # ── Future shape stubs ──────────────────────────────────────────────
    # ------------------------------------------------------------------

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
