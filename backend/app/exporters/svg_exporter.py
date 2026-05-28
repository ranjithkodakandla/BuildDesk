"""
SVG Exporter
============
Converts a GeometryBuildResult into a self-contained SVG string.

This is BuildDesk's first visual drawing output.

Architecture position:
    GeometryBuildResult
            ↓
        SvgExporter
            ↓
        SVG string   ← returned by POST /api/v1/export/svg
                       or saved to Cloud Storage (Phase 3)

Design decisions:
    - SVG coordinates: origin is top-left, y increases downward.
      The geometry coordinate system has origin at bottom-left with
      y increasing upward. Coordinate mapping flips the y-axis.
    - All dimensions are in SVG user units (1 unit = 1 inch by default).
      A scale_factor converts geometric inches to SVG pixels.
    - Margin padding surrounds the drawing content to avoid clipping.
    - Dimension lines use a classic engineering style:
        extension lines → short perpendicular ticks
        measurement text → centred above the dimension line
    - Colour palette is minimal and print-safe:
        shape fill     #f0f4f8  (light blue-grey)
        shape stroke   #1a2332  (dark navy)
        dim lines      #4a7fb5  (medium blue)
        dim text       #1a2332
        annotation     #2d5f8a  (muted blue)
    - Zero external dependencies; uses only Python stdlib string formatting.

Supported primitives:
    Rectangle     → <rect>
    Line          → <line>
    Circle        → <circle>
    Polyline      → <polyline>
    DimensionLine → <line> + tick marks + <text>
    TextAnnotation → <text>

Usage::

    exporter = SvgExporter()
    svg_string = exporter.export(result)
"""

from __future__ import annotations

import math
from typing import List, Optional

from app.geometry.primitives import (
    Circle,
    DimensionLine,
    Line,
    Point,
    Polyline,
    Rectangle,
    TextAnnotation,
)
from app.services.geometry_builder import GeometryBuildResult


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# SVG user-units per geometric inch
_DEFAULT_SCALE: float = 4.0

# Margin around the drawing content (SVG units)
_MARGIN: float = 80.0

# Dimension line offset from the shape edge (SVG units)
_DIM_OFFSET: float = 30.0

# Tick length for dimension extension lines (SVG units / 2 each side)
_TICK_HALF: float = 6.0

# Colours
_COL_FILL       = "#f0f4f8"
_COL_STROKE     = "#1a2332"
_COL_DIM        = "#4a7fb5"
_COL_DIM_TEXT   = "#1a2332"
_COL_ANNOTATION = "#2d5f8a"
_COL_TITLE_BG   = "#1a2332"
_COL_TITLE_TEXT = "#ffffff"


# ---------------------------------------------------------------------------
# SvgExporter
# ---------------------------------------------------------------------------

class SvgExporter:
    """
    Stateless service that renders a GeometryBuildResult as an SVG string.

    Usage::

        exporter = SvgExporter(scale=4.0)
        svg = exporter.export(result)
    """

    def __init__(self, scale: float = _DEFAULT_SCALE) -> None:
        """
        Args:
            scale: SVG pixels per geometric unit (inch). Default 4.0 gives
                   a 96" countertop a 384-unit SVG width — good for screen.
        """
        self.scale = scale

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def export(self, result: GeometryBuildResult) -> str:
        """
        Render *result* to a self-contained SVG string.

        Returns:
            Complete SVG document as a UTF-8 string (no BOM).
        """
        elements: List[str] = []

        # ── Collect content bounds ──────────────────────────────────────
        # Scan rectangles and polylines for max extents.
        rect_w = max((r.width  for r in result.rectangles), default=0.0)
        rect_h = max((r.height for r in result.rectangles), default=0.0)
        poly_w = max(
            (max(p.x for p in pl.points) for pl in result.polylines if pl.points),
            default=0.0,
        )
        poly_h = max(
            (max(p.y for p in pl.points) for pl in result.polylines if pl.points),
            default=0.0,
        )
        max_w = max(rect_w, poly_w) or 100.0
        max_h = max(rect_h, poly_h) or 50.0

        # SVG viewport: content + margins + dim line space
        dim_extra = _DIM_OFFSET + 40.0     # extra for bottom/left dim lines
        svg_w = max_w * self.scale + _MARGIN * 2 + dim_extra
        svg_h = max_h * self.scale + _MARGIN * 2 + dim_extra + 50.0  # +50 title

        title_h = 44.0

        # ── Background ──────────────────────────────────────────────────
        elements.append(self._bg(svg_w, svg_h + title_h))

        # ── Title bar ───────────────────────────────────────────────────
        geo = result.geometry
        title = geo.pieces[0].label if geo.pieces else "BuildDesk Drawing"
        area  = geo.computed_area or 0.0
        perim = geo.computed_perimeter or 0.0
        elements.append(self._title_bar(
            svg_w, title,
            subtitle=f"Area: {area:.2f} in²  |  Perimeter: {perim:.2f} in",
            title_h=title_h,
        ))

        # Drawing content shifted down by title_h
        dy_title = title_h

        # ── Rectangles ──────────────────────────────────────────────────
        for rect in result.rectangles:
            elements.append(self._render_rect(rect, svg_h, dy_title))

        # ── Dimension lines ─────────────────────────────────────────────
        for dim in result.dimension_lines:
            elements.append(self._render_dimension(dim, svg_h, dy_title))

        # ── Text annotations ────────────────────────────────────────────
        for ann in result.annotations:
            elements.append(self._render_annotation(ann, svg_h, dy_title))

        # ── Loose lines ─────────────────────────────────────────────────
        for line in result.lines:
            elements.append(self._render_line(line, svg_h, dy_title))

        # ── Circles ─────────────────────────────────────────────────────
        for circle in result.circles:
            elements.append(self._render_circle(circle, svg_h, dy_title))

        # ── Polylines ───────────────────────────────────────────────────
        for poly in result.polylines:
            elements.append(self._render_polyline(poly, svg_h, dy_title))

        # ── Build SVG document ──────────────────────────────────────────
        total_h = svg_h + title_h
        body = "\n  ".join(elements)
        return self._wrap(svg_w, total_h, body)

    # ------------------------------------------------------------------
    # Coordinate mapping
    # ------------------------------------------------------------------

    def _sx(self, x: float) -> float:
        """Geometry x  →  SVG x (with left margin)."""
        return _MARGIN + x * self.scale

    def _sy(self, y: float, svg_h: float, dy: float = 0.0) -> float:
        """
        Geometry y (bottom-left origin, y-up)
        →  SVG y (top-left origin, y-down).

        svg_h: the height of the drawing content area (excludes title).
        dy:    additional downward offset (e.g. title bar height).
        """
        # Flip: svg_y = svg_h - margin - y*scale + margin = svg_h - y*scale
        return dy + svg_h - _MARGIN - y * self.scale

    # ------------------------------------------------------------------
    # Primitive renderers
    # ------------------------------------------------------------------

    def _render_rect(self, rect: Rectangle, svg_h: float, dy: float) -> str:
        sx = self._sx(rect.origin.x)
        sy = self._sy(rect.origin.y + rect.height, svg_h, dy)   # top-left in SVG
        sw = rect.width  * self.scale
        sh = rect.height * self.scale

        label_attr = f'id="rect-{rect.rect_id}"'
        return (
            f'<rect {label_attr} x="{sx:.2f}" y="{sy:.2f}" '
            f'width="{sw:.2f}" height="{sh:.2f}" '
            f'fill="{_COL_FILL}" stroke="{_COL_STROKE}" '
            f'stroke-width="2" rx="2" />'
        )

    def _render_line(self, line: Line, svg_h: float, dy: float) -> str:
        x1 = self._sx(line.start.x)
        y1 = self._sy(line.start.y, svg_h, dy)
        x2 = self._sx(line.end.x)
        y2 = self._sy(line.end.y, svg_h, dy)
        return (
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" '
            f'x2="{x2:.2f}" y2="{y2:.2f}" '
            f'stroke="{_COL_STROKE}" stroke-width="1.5" />'
        )

    def _render_circle(self, circle: Circle, svg_h: float, dy: float) -> str:
        cx = self._sx(circle.center.x)
        cy = self._sy(circle.center.y, svg_h, dy)
        r  = circle.radius * self.scale
        return (
            f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" '
            f'fill="none" stroke="{_COL_STROKE}" stroke-width="1.5" '
            f'stroke-dasharray="4 2" />'
        )

    def _render_polyline(self, poly: Polyline, svg_h: float, dy: float) -> str:
        pts = " ".join(
            f"{self._sx(p.x):.2f},{self._sy(p.y, svg_h, dy):.2f}"
            for p in poly.points
        )
        close = " Z" if poly.closed else ""
        # Use SVG <polyline> or <polygon> depending on closed flag
        if poly.closed:
            return (
                f'<polygon points="{pts}" '
                f'fill="{_COL_FILL}" stroke="{_COL_STROKE}" stroke-width="1.5" />'
            )
        return (
            f'<polyline points="{pts}" '
            f'fill="none" stroke="{_COL_STROKE}" stroke-width="1.5" />'
        )

    def _render_dimension(self, dim: DimensionLine, svg_h: float, dy: float) -> str:
        """
        Render a DimensionLine with:
            - the main dimension line
            - arrow-style ticks at each end
            - centred measurement text above the line
        """
        x1 = self._sx(dim.start.x)
        y1 = self._sy(dim.start.y, svg_h, dy)
        x2 = self._sx(dim.end.x)
        y2 = self._sy(dim.end.y, svg_h, dy)

        # Determine if line is horizontal or vertical
        is_horizontal = abs(y1 - y2) < 0.5

        # Offset: push the dimension line away from the shape edge
        offset_px = dim.offset * _DIM_OFFSET  # dim.offset is -1.0 → below/left

        if is_horizontal:
            # Horizontal dimension: push down (positive y in SVG = down)
            lx1, ly1 = x1, y1 - offset_px
            lx2, ly2 = x2, y2 - offset_px
            # Extension lines (vertical ticks)
            ext1 = (
                f'<line x1="{x1:.2f}" y1="{y1:.2f}" '
                f'x2="{lx1:.2f}" y2="{ly1:.2f}" '
                f'stroke="{_COL_DIM}" stroke-width="1" />'
            )
            ext2 = (
                f'<line x1="{x2:.2f}" y1="{y2:.2f}" '
                f'x2="{lx2:.2f}" y2="{ly2:.2f}" '
                f'stroke="{_COL_DIM}" stroke-width="1" />'
            )
            # Main dim line
            main = (
                f'<line x1="{lx1:.2f}" y1="{ly1:.2f}" '
                f'x2="{lx2:.2f}" y2="{ly2:.2f}" '
                f'stroke="{_COL_DIM}" stroke-width="1.5" '
                f'marker-start="url(#arrow)" marker-end="url(#arrow)" />'
            )
            # Text centred above the dim line
            tx = (lx1 + lx2) / 2
            ty = ly1 - 6
            text = (
                f'<text x="{tx:.2f}" y="{ty:.2f}" '
                f'text-anchor="middle" font-size="11" '
                f'fill="{_COL_DIM_TEXT}" font-family="monospace" '
                f'font-weight="600">{_esc(dim.display_text)}</text>'
            )
        else:
            # Vertical dimension: push left (negative x in SVG = left)
            lx1, ly1 = x1 + offset_px, y1
            lx2, ly2 = x2 + offset_px, y2
            ext1 = (
                f'<line x1="{x1:.2f}" y1="{y1:.2f}" '
                f'x2="{lx1:.2f}" y2="{ly1:.2f}" '
                f'stroke="{_COL_DIM}" stroke-width="1" />'
            )
            ext2 = (
                f'<line x1="{x2:.2f}" y1="{y2:.2f}" '
                f'x2="{lx2:.2f}" y2="{ly2:.2f}" '
                f'stroke="{_COL_DIM}" stroke-width="1" />'
            )
            main = (
                f'<line x1="{lx1:.2f}" y1="{ly1:.2f}" '
                f'x2="{lx2:.2f}" y2="{ly2:.2f}" '
                f'stroke="{_COL_DIM}" stroke-width="1.5" '
                f'marker-start="url(#arrow)" marker-end="url(#arrow)" />'
            )
            # Text rotated, centred along the dim line
            tx = lx1 - 16
            ty = (ly1 + ly2) / 2
            text = (
                f'<text x="{tx:.2f}" y="{ty:.2f}" '
                f'text-anchor="middle" font-size="11" '
                f'fill="{_COL_DIM_TEXT}" font-family="monospace" '
                f'font-weight="600" '
                f'transform="rotate(-90,{tx:.2f},{ty:.2f})">'
                f'{_esc(dim.display_text)}</text>'
            )

        return "\n  ".join([ext1, ext2, main, text])

    def _render_annotation(self, ann: TextAnnotation, svg_h: float, dy: float) -> str:
        ax = self._sx(ann.position.x)
        ay = self._sy(ann.position.y, svg_h, dy)
        weight = "bold" if ann.bold else "normal"
        fs = ann.font_size * (self.scale / 4.0)   # scale font with drawing
        fs = max(10.0, min(fs, 28.0))              # clamp to readable range
        return (
            f'<text x="{ax:.2f}" y="{ay:.2f}" '
            f'text-anchor="middle" dominant-baseline="middle" '
            f'font-size="{fs:.1f}" font-weight="{weight}" '
            f'fill="{_COL_ANNOTATION}" font-family="sans-serif" '
            f'opacity="0.85">'
            f'{_esc(ann.text)}</text>'
        )

    # ------------------------------------------------------------------
    # Document structure helpers
    # ------------------------------------------------------------------

    def _bg(self, w: float, h: float) -> str:
        return (
            f'<rect x="0" y="0" width="{w:.2f}" height="{h:.2f}" '
            f'fill="#ffffff" />'
        )

    def _title_bar(
        self,
        w: float,
        title: str,
        subtitle: str,
        title_h: float,
    ) -> str:
        return (
            f'<rect x="0" y="0" width="{w:.2f}" height="{title_h:.2f}" '
            f'fill="{_COL_TITLE_BG}" />'
            f'\n  <text x="16" y="16" font-size="14" font-weight="bold" '
            f'fill="{_COL_TITLE_TEXT}" font-family="sans-serif" '
            f'dominant-baseline="hanging">{_esc(title)}</text>'
            f'\n  <text x="16" y="32" font-size="10" '
            f'fill="#aac4e0" font-family="monospace" '
            f'dominant-baseline="hanging">{_esc(subtitle)}</text>'
            f'\n  <text x="{w - 12:.2f}" y="24" font-size="9" '
            f'fill="#6a8cac" font-family="monospace" '
            f'text-anchor="end" dominant-baseline="middle">'
            f'BuildDesk v1</text>'
        )

    def _arrow_defs(self) -> str:
        """SVG arrowhead marker definition."""
        return (
            '<defs>\n'
            '  <marker id="arrow" markerWidth="6" markerHeight="6" '
            'refX="3" refY="3" orient="auto" markerUnits="strokeWidth">\n'
            f'    <path d="M0,0 L0,6 L6,3 z" fill="{_COL_DIM}" />\n'
            '  </marker>\n'
            '</defs>'
        )

    def _grid(self, w: float, h: float, dy: float) -> str:
        """Subtle grid pattern for the drawing area."""
        step = 10.0 * self.scale
        lines = []
        x = _MARGIN
        while x <= w - _MARGIN:
            lines.append(
                f'<line x1="{x:.1f}" y1="{dy:.1f}" '
                f'x2="{x:.1f}" y2="{h + dy:.1f}" '
                f'stroke="#e8eef4" stroke-width="0.5" />'
            )
            x += step
        y = dy + _MARGIN
        while y <= h + dy - _MARGIN:
            lines.append(
                f'<line x1="{_MARGIN:.1f}" y1="{y:.1f}" '
                f'x2="{w - _MARGIN:.1f}" y2="{y:.1f}" '
                f'stroke="#e8eef4" stroke-width="0.5" />'
            )
            y += step
        return "\n  ".join(lines)

    def _wrap(self, w: float, h: float, body: str) -> str:
        """Wrap content in a valid SVG root element with metadata."""
        defs = self._arrow_defs()
        return (
            f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{w:.2f}" height="{h:.2f}" '
            f'viewBox="0 0 {w:.2f} {h:.2f}">\n'
            f'  <!-- BuildDesk SVG Export v1 -->\n'
            f'  {defs}\n'
            f'  {body}\n'
            f'</svg>'
        )


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _esc(text: str) -> str:
    """Escape special characters for safe SVG text embedding."""
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
