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

    def _build_vanity(
        self,
        template: ShapeTemplate,
        dims: Dict[str, Any],
        project_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> GeometryBuildResult:
        """
        Build geometry for a wall-mounted bathroom vanity countertop.

        Construction rules:
            - Back edge sits flush against the wall → NOT exposed, NOT finished.
            - Front, left, and right edges are exposed and finished.
            - The outline is an OPEN Polyline (closed=False) tracing the 3
              exposed edges only: left-back → left-front → right-front → right-back.
              The wall edge (back) is omitted from the outline.

        Required parameters:
            length          – horizontal span (inches)
            width           – front-to-back depth (inches)

        Optional parameters:
            thickness       – slab thickness; default 0.75"
            backsplash_height – height of integrated backsplash; 0 = none
            sink_cutout     – boolean; if true, adds a Circle at the centre
            sink_diameter   – diameter of the sink cutout; default 15"
            label           – piece name override

        Validation:
            If sink_cutout=True, sink_diameter must fit within the vanity
            (diameter ≤ min(length, width) − 4" clearance).

        Produces:
            - 1 GeometryPiece (full slab)
            - 1 open Polyline (3 exposed edges, wall back omitted)
            - 1 Rectangle (bounding box)
            - 3 DimensionLines: length (front), width left, width right
            - 1 TextAnnotation (piece label at centre)
            - 1 TextAnnotation (backsplash note, if backsplash_height > 0)
            - 1 Circle (sink cutout, if sink_cutout=True)
        """
        length           = float(dims["length"])
        width            = float(dims["width"])
        thickness        = float(dims.get("thickness", 0.75))
        backsplash_h     = float(dims.get("backsplash_height", 0.0))
        sink_cutout_flag = bool(dims.get("sink_cutout", False))
        sink_diameter    = float(dims.get("sink_diameter", 15.0))
        label            = str(dims.get("label", template.name))

        area      = length * width
        # Perimeter counts 3 exposed edges (wall back is not edged/finished)
        perimeter = length + 2 * width

        # ── Sink diameter validation ─────────────────────────────────────
        if sink_cutout_flag:
            clearance   = 4.0   # minimum stone remaining on each side
            max_allowed = min(length, width) - 2 * clearance
            if sink_diameter > max_allowed:
                raise GeometryBuildError(
                    f"sink_diameter {sink_diameter}\" exceeds safe maximum "
                    f"{max_allowed:.1f}\" for a {length}\" × {width}\" vanity "
                    f"(clearance = {clearance}\" per side)."
                )

        # ── GeometryPiece ─────────────────────────────────────────────────
        notes_parts = [f"Vanity slab: {length}\" × {width}\" × {thickness}\"."]
        notes_parts.append("Exposed edges: front, left, right. Wall back: flush/unfinished.")
        if backsplash_h:
            notes_parts.append(f"Integrated backsplash: {backsplash_h}\" height.")
        if sink_cutout_flag:
            notes_parts.append(f"Sink cutout: ⌀{sink_diameter}\" centred.")

        piece = GeometryPiece(
            label=label,
            width=width,
            length=length,
            thickness=thickness,
            area=area,
            notes=" ".join(notes_parts),
        )

        # ── GeometryModel ─────────────────────────────────────────────────
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
                # ── Construction rules ────────────────────────────────────
                "exposed_edges":  ["front", "left", "right"],
                "wall_edge":      "back",
                "wall_edge_note": "Flush against wall; no edge profile required.",
                # ── Options ───────────────────────────────────────────────
                "backsplash_height": backsplash_h,
                "has_backsplash":    backsplash_h > 0,
                "sink_cutout":       sink_cutout_flag,
                "sink_diameter":     sink_diameter if sink_cutout_flag else None,
            },
        )

        # ── Open Polyline outline — 3 exposed edges ───────────────────────
        # Tracing BL → TL (left edge) → TR (front→right) → BR (right edge)
        # Note: 'top' in geometry coords = front of vanity (y=width)
        #        'bottom' in geometry coords = back wall (y=0)
        #
        # Outline: back-left → front-left → front-right → back-right
        # (3 line segments, wall edge NOT drawn)
        outline = Polyline(
            points=[
                Point(x=0.0,    y=0.0),    # back-left   (wall corner)
                Point(x=0.0,    y=width),  # front-left  (exposed)
                Point(x=length, y=width),  # front-right (exposed)
                Point(x=length, y=0.0),    # back-right  (wall corner)
            ],
            closed=False,   # open path — wall edge intentionally omitted
            label=f"{label} outline (3 exposed edges)",
            metadata={
                "edge_type":      "partial_exposed",
                "exposed_edges":  ["left", "front", "right"],
                "omitted_edge":   "back (wall)",
            },
        )

        # ── Bounding Rectangle ────────────────────────────────────────────
        rect = Rectangle(
            origin=Point(x=0.0, y=0.0),
            width=length,
            height=width,
            label=label,
            metadata={"role": "bounding_box"},
        )

        # ── 3 DimensionLines ──────────────────────────────────────────────
        # Front edge (length, horizontal) — front of vanity = top (y=width)
        dim_front = DimensionLine(
            start=Point(x=0.0,    y=width),
            end=  Point(x=length, y=width),
            value=length, unit="in", label=f"{length}\"",
            offset=1.0,   # push above the front edge
        )
        # Left edge (width, vertical)
        dim_left = DimensionLine(
            start=Point(x=0.0, y=0.0),
            end=  Point(x=0.0, y=width),
            value=width, unit="in", label=f"{width}\"",
            offset=-1.0,
        )
        # Right edge (width, vertical)
        dim_right = DimensionLine(
            start=Point(x=length, y=0.0),
            end=  Point(x=length, y=width),
            value=width, unit="in", label=f"{width}\"",
            offset=1.0,
        )

        # ── TextAnnotation — piece label at centre ─────────────────────────
        centre = rect.center
        annotation = TextAnnotation(
            position=centre,
            text=label,
            font_size=14.0,
            bold=True,
            label="piece_label",
        )

        # ── Optional backsplash annotation ───────────────────────────────
        annotations = [annotation]
        if backsplash_h > 0:
            bs_ann = TextAnnotation(
                position=Point(x=length / 2, y=-backsplash_h / 2),
                text=f"Backsplash: {backsplash_h}\" H",
                font_size=10.0,
                bold=False,
                label="backsplash_note",
                metadata={"backsplash_height": backsplash_h},
            )
            annotations.append(bs_ann)

        # ── Optional sink cutout circle ───────────────────────────────────
        circles: List[Circle] = []
        if sink_cutout_flag:
            sink_circle = Circle(
                center=centre,
                radius=sink_diameter / 2,
                label=f"Sink ⌀{sink_diameter}\"",
                metadata={
                    "cutout_type": "undermount_sink",
                    "diameter":    sink_diameter,
                },
            )
            circles.append(sink_circle)

        return GeometryBuildResult(
            geometry=geometry,
            rectangles=[rect],
            polylines=[outline],
            dimension_lines=[dim_front, dim_left, dim_right],
            annotations=annotations,
            circles=circles,
        )

    def _build_straight_kitchen(
        self,
        template: ShapeTemplate,
        dims: Dict[str, Any],
        project_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> GeometryBuildResult:
        """
        Build geometry for a straight kitchen run, supporting multi-piece logic.

        Construction rules:
            - Back edge is flush against a wall (open polyline).
            - Front, left, and right edges are exposed.
        
        Fabrication rules (Seam Logic):
            - If length > slab_max_length and seam_enabled=True, the run is
              divided into multiple slabs.
            - Uses greedy splitting (e.g. 180" run with 120" max → 120" + 60").
        """
        length           = float(dims["length"])
        width            = float(dims["width"])
        thickness        = float(dims.get("thickness", 0.75))
        backsplash_h     = float(dims.get("backsplash_height", 0.0))
        seam_enabled     = bool(dims.get("seam_enabled", True))
        slab_max_length  = float(dims.get("slab_max_length", 120.0))
        base_label       = str(dims.get("label", template.name))

        # ── Fabrication Seam Splitting ────────────────────────────────────
        piece_lengths = []
        if seam_enabled and length > slab_max_length:
            rem = length
            while rem > 0:
                p_len = min(rem, slab_max_length)
                piece_lengths.append(p_len)
                rem -= p_len
        else:
            piece_lengths.append(length)

        seam_count = len(piece_lengths) - 1

        # ── Pieces & GeometryModel ────────────────────────────────────────
        pieces = []
        rectangles = []
        lines = []
        annotations = []
        dim_lines = []

        x_offset = 0.0
        for i, p_len in enumerate(piece_lengths):
            piece_num = i + 1
            is_multi = len(piece_lengths) > 1
            p_label = f"{base_label} - Part {piece_num}" if is_multi else base_label

            piece = GeometryPiece(
                label=p_label,
                width=width,
                length=p_len,
                thickness=thickness,
                area=p_len * width,
                notes=f"Piece {piece_num} of {len(piece_lengths)}." if is_multi else "Single piece."
            )
            pieces.append(piece)

            rect = Rectangle(
                origin=Point(x=x_offset, y=0.0),
                width=p_len,
                height=width,
                label=p_label,
                metadata={"role": "piece", "piece_num": piece_num}
            )
            rectangles.append(rect)

            annotations.append(TextAnnotation(
                position=rect.center,
                text=p_label,
                font_size=12.0,
                bold=True,
                label="piece_label"
            ))

            # Dimension for this specific piece along the back edge
            dim_lines.append(DimensionLine(
                start=Point(x=x_offset, y=0.0),
                end=Point(x=x_offset + p_len, y=0.0),
                value=p_len, unit="in", label=f"{p_len}\"",
                offset=-1.0,
            ))

            # Seam indicator
            if i > 0:
                seam_line = Line(
                    start=Point(x=x_offset, y=0.0),
                    end=Point(x=x_offset, y=width),
                    label=f"Seam {i}",
                    metadata={"line_type": "seam", "stroke_dasharray": "5,5"}
                )
                lines.append(seam_line)
                
                annotations.append(TextAnnotation(
                    position=Point(x=x_offset, y=width / 2),
                    text="SEAM",
                    font_size=8.0,
                    bold=False,
                    label="seam_label"
                ))

            x_offset += p_len

        # Overall GeometryModel
        area      = length * width
        perimeter = length + 2 * width

        geometry = GeometryModel(
            project_id=project_id,
            tenant_id=tenant_id,
            template_id=template.template_id,
            dimensions=dict(dims),
            status=GeometryStatus.computed,
            pieces=pieces,
            computed_area=area,
            computed_perimeter=perimeter,
            metadata={
                "exposed_edges": ["front", "left", "right"],
                "wall_edge": "back",
                "has_backsplash": backsplash_h > 0,
                "backsplash_height": backsplash_h,
                "seam_enabled": seam_enabled,
                "seam_count": seam_count,
            },
        )

        # ── Overall Outline (Open Polyline) ───────────────────────────────
        outline = Polyline(
            points=[
                Point(x=0.0,    y=0.0),
                Point(x=0.0,    y=width),
                Point(x=length, y=width),
                Point(x=length, y=0.0),
            ],
            closed=False,
            label=f"{base_label} overall outline",
            metadata={"edge_type": "partial_exposed", "omitted_edge": "back (wall)"}
        )

        # ── Overall DimensionLines ────────────────────────────────────────
        # Overall Front
        dim_lines.append(DimensionLine(
            start=Point(x=0.0, y=width),
            end=Point(x=length, y=width),
            value=length, unit="in", label=f"Overall: {length}\"",
            offset=1.5,
        ))
        # Left edge
        dim_lines.append(DimensionLine(
            start=Point(x=0.0, y=0.0),
            end=Point(x=0.0, y=width),
            value=width, unit="in", label=f"{width}\"",
            offset=-1.0,
        ))
        # Right edge
        dim_lines.append(DimensionLine(
            start=Point(x=length, y=0.0),
            end=Point(x=length, y=width),
            value=width, unit="in", label=f"{width}\"",
            offset=1.0,
        ))

        if backsplash_h > 0:
            annotations.append(TextAnnotation(
                position=Point(x=length / 2, y=-backsplash_h / 2 - 1.0),
                text=f"Backsplash: {backsplash_h}\" H",
                font_size=10.0,
            ))

        return GeometryBuildResult(
            geometry=geometry,
            rectangles=rectangles,
            polylines=[outline],
            dimension_lines=dim_lines,
            annotations=annotations,
            lines=lines,
            circles=[]
        )

    def _build_l_kitchen(
        self,
        template: ShapeTemplate,
        dims: Dict[str, Any],
        project_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> GeometryBuildResult:
        """
        Build geometry for an L-shaped kitchen.

        Construction rules:
            - The outer corner is at (0,0). Leg A goes UP along the y-axis.
            - Leg B goes RIGHT along the x-axis.
            - The outer edges (x=0, y=0) sit flush against the wall, so they are omitted
              from the overall outline (open polyline).
            - Exposed edges: Leg A end, Leg A front, inner corner, Leg B front, Leg B end.

        Fabrication rules (Corner join):
            - If seam_enabled=True, the shape is split into 2 pieces at the corner.
            - corner_join_type="butt": Leg A gets the corner (y=0 to leg_a_length). Leg B butts into it.
            - corner_join_type="miter": Both pieces meet at a 45-degree angle. Bounding boxes overlap.
        """
        leg_a_length     = float(dims["leg_a_length"])
        leg_b_length     = float(dims["leg_b_length"])
        width            = float(dims["width"])
        thickness        = float(dims.get("thickness", 0.75))
        backsplash_h     = float(dims.get("backsplash_height", 0.0))
        seam_enabled     = bool(dims.get("seam_enabled", True))
        corner_join_type = str(dims.get("corner_join_type", "butt")).lower()
        base_label       = str(dims.get("label", template.name))

        # Overall outline (Open Polyline tracing the exposed edges)
        # Sequence: top-left (Leg A end start) -> top-right -> inner corner -> Leg B top-right -> Leg B bottom-right
        outline = Polyline(
            points=[
                Point(x=0.0,          y=leg_a_length), # Top-left (wall corner)
                Point(x=width,        y=leg_a_length), # Top-right of Leg A
                Point(x=width,        y=width),        # Inner corner
                Point(x=leg_b_length, y=width),        # Top-right of Leg B
                Point(x=leg_b_length, y=0.0),          # Bottom-right of Leg B (wall corner)
            ],
            closed=False,
            label=f"{base_label} exposed outline",
            metadata={"edge_type": "partial_exposed", "omitted_edges": ["back wall A", "back wall B"]}
        )

        pieces = []
        rectangles = []
        lines = []
        annotations = []
        dim_lines = []

        area = (leg_a_length * width) + ((leg_b_length - width) * width)
        perimeter = leg_a_length + leg_b_length + (leg_a_length - width) + (leg_b_length - width) + width + width

        if not seam_enabled:
            # Single piece for the whole L
            pieces.append(GeometryPiece(
                label=base_label,
                width=width,
                length=max(leg_a_length, leg_b_length),
                thickness=thickness,
                area=area,
                notes="Single L-shaped piece."
            ))
            rectangles.append(Rectangle(
                origin=Point(x=0.0, y=0.0),
                width=leg_b_length,
                height=leg_a_length,
                label=base_label,
                metadata={"role": "bounding_box"}
            ))
            annotations.append(TextAnnotation(
                position=Point(x=leg_b_length/2, y=leg_a_length/2),
                text=base_label,
                font_size=14.0,
                bold=True
            ))
        else:
            if corner_join_type == "butt":
                # Leg A owns the corner
                p_a_len = leg_a_length
                p_b_len = leg_b_length - width
                
                # Piece A
                pieces.append(GeometryPiece(
                    label=f"{base_label} - Leg A", width=width, length=p_a_len, thickness=thickness, area=p_a_len*width, notes="Butt join."
                ))
                rectangles.append(Rectangle(
                    origin=Point(x=0.0, y=0.0), width=width, height=p_a_len, label="Leg A", metadata={"role": "piece", "piece_num": 1}
                ))
                annotations.append(TextAnnotation(position=Point(x=width/2, y=leg_a_length/2), text="Leg A", font_size=12.0))

                # Piece B
                pieces.append(GeometryPiece(
                    label=f"{base_label} - Leg B", width=width, length=p_b_len, thickness=thickness, area=p_b_len*width, notes="Butt join."
                ))
                rectangles.append(Rectangle(
                    origin=Point(x=width, y=0.0), width=p_b_len, height=width, label="Leg B", metadata={"role": "piece", "piece_num": 2}
                ))
                annotations.append(TextAnnotation(position=Point(x=width + p_b_len/2, y=width/2), text="Leg B", font_size=12.0))

                # Seam line
                lines.append(Line(
                    start=Point(x=width, y=0.0), end=Point(x=width, y=width),
                    label="Butt Seam", metadata={"line_type": "seam", "stroke_dasharray": "5,5"}
                ))
                annotations.append(TextAnnotation(position=Point(x=width, y=width/2), text="SEAM", font_size=8.0))

            elif corner_join_type == "miter":
                # Both pieces meet at a 45 deg angle
                # We record their full bounding boxes (which overlap in the corner)
                pieces.append(GeometryPiece(
                    label=f"{base_label} - Leg A (Miter)", width=width, length=leg_a_length, thickness=thickness, area=leg_a_length*width - (width*width/2), notes="Miter join."
                ))
                rectangles.append(Rectangle(
                    origin=Point(x=0.0, y=0.0), width=width, height=leg_a_length, label="Leg A", metadata={"role": "bounding_box", "piece_num": 1}
                ))
                annotations.append(TextAnnotation(position=Point(x=width/2, y=leg_a_length/2 + width/2), text="Leg A", font_size=12.0))

                pieces.append(GeometryPiece(
                    label=f"{base_label} - Leg B (Miter)", width=width, length=leg_b_length, thickness=thickness, area=leg_b_length*width - (width*width/2), notes="Miter join."
                ))
                rectangles.append(Rectangle(
                    origin=Point(x=0.0, y=0.0), width=leg_b_length, height=width, label="Leg B", metadata={"role": "bounding_box", "piece_num": 2}
                ))
                annotations.append(TextAnnotation(position=Point(x=leg_b_length/2 + width/2, y=width/2), text="Leg B", font_size=12.0))

                # Seam line (diagonal)
                lines.append(Line(
                    start=Point(x=0.0, y=0.0), end=Point(x=width, y=width),
                    label="Miter Seam", metadata={"line_type": "seam", "stroke_dasharray": "5,5"}
                ))
                annotations.append(TextAnnotation(position=Point(x=width/2, y=width/2), text="MITER SEAM", font_size=8.0))

        # Overall Dimensions
        # Leg A outer length (left wall)
        dim_lines.append(DimensionLine(
            start=Point(x=0.0, y=0.0), end=Point(x=0.0, y=leg_a_length),
            value=leg_a_length, unit="in", label=f"Leg A: {leg_a_length}\"", offset=-1.0
        ))
        # Leg B outer length (bottom wall)
        dim_lines.append(DimensionLine(
            start=Point(x=0.0, y=0.0), end=Point(x=leg_b_length, y=0.0),
            value=leg_b_length, unit="in", label=f"Leg B: {leg_b_length}\"", offset=-1.0
        ))
        # Leg A End width (top)
        dim_lines.append(DimensionLine(
            start=Point(x=0.0, y=leg_a_length), end=Point(x=width, y=leg_a_length),
            value=width, unit="in", label=f"{width}\"", offset=1.0
        ))
        # Leg B End width (right)
        dim_lines.append(DimensionLine(
            start=Point(x=leg_b_length, y=0.0), end=Point(x=leg_b_length, y=width),
            value=width, unit="in", label=f"{width}\"", offset=1.0
        ))

        geometry = GeometryModel(
            project_id=project_id,
            tenant_id=tenant_id,
            template_id=template.template_id,
            dimensions=dict(dims),
            status=GeometryStatus.computed,
            pieces=pieces,
            computed_area=area,
            computed_perimeter=perimeter,
            metadata={
                "corner_join_type": corner_join_type if seam_enabled else "none",
                "corner_count": 1,
                "seam_enabled": seam_enabled,
                "seam_count": 1 if seam_enabled else 0,
            },
        )

        return GeometryBuildResult(
            geometry=geometry,
            rectangles=rectangles,
            polylines=[outline],
            dimension_lines=dim_lines,
            annotations=annotations,
            lines=lines,
            circles=[]
        )

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
