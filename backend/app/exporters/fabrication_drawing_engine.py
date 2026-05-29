"""
Fabrication Drawing Engine  (Phase 4)
=======================================
Renders scaled vector drawings of fabrication assemblies onto a ReportLab canvas.

This is the CORE drawing primitive layer for Phase 4. It handles:
    - Auto-scaling parts to fit a drawing zone
    - Scaled part outlines (rectangles to real dimensions)
    - Edge visual differentiation (polished=thick, raw=dashed, miter=double)
    - Cutout overlays (dashed rect, rounded for sinks)
    - Hole circles with Ø label
    - Splash bands (shaded edge bands)
    - Dimension callout lines with arrows
    - Seam lines between adjacent parts
    - Edge legend block

All drawing is fabrication-aware:
    - "polished" = thick solid line (exposed edge)
    - "raw" = thin dashed line (wall/cabinet contact)
    - "eased" = medium solid line
    - "miter" = 45° hatch marks
    - "finished" = double line

Coordinate system:
    ReportLab y=0 at bottom of page.
    Drawing zone origin is passed in as (origin_x, origin_y) where origin_y is
    the BOTTOM of the drawing zone.
    Parts are laid out left-to-right within the drawing zone.

Scale calculation:
    max_available_width  → fits all parts + gaps
    max_available_height → fits tallest part + dimension callout space
    scale = min(w_scale, h_scale)  — uniform scale
    min scale: 1 pt per inch (so 96" part = 96 pts = 1.33 in)
    max scale: 6 pts per inch (so 24" depth = 144 pts = 2 in)
"""

from __future__ import annotations

import math
from typing import List, Optional, Tuple

from reportlab.lib.colors import HexColor, Color
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas as rl_canvas

from app.models.fabrication import (
    Assembly, Cutout, CutoutType, EdgeTreatment, EdgeType,
    Hole, MountType, Part, Position, Splash, SplashType,
)
from app.models.hierarchy import UnitVariant


# ---------------------------------------------------------------------------
# Drawing constants — print-safe, fabrication-conventional
# ---------------------------------------------------------------------------
_C_PART_FILL   = HexColor("#f0f4f8")   # stone surface fill
_C_PART_STROKE = HexColor("#1a2332")   # part outline (default)
_C_POLISHED    = HexColor("#1a2332")   # exposed polished edge — dark navy, thick
_C_RAW         = HexColor("#aaaaaa")   # raw/wall contact — grey, dashed
_C_EASED       = HexColor("#4a7fb5")   # eased — blue
_C_MITER       = HexColor("#e67e22")   # miter join — orange
_C_FINISHED    = HexColor("#2ecc71")   # finished — green
_C_CUTOUT_FILL = HexColor("#ffffff")   # cutout interior — white void
_C_CUTOUT_STR  = HexColor("#c0392b")   # cutout outline — red dashed
_C_HOLE        = HexColor("#8e44ad")   # hole circle — purple
_C_SPLASH      = HexColor("#3498db")   # splash band — blue tint
_C_SPLASH_FILL = HexColor("#d6eaf8")   # splash fill — very light blue
_C_SEAM        = HexColor("#e74c3c")   # seam line — red
_C_DIM         = HexColor("#4a7fb5")   # dimension lines
_C_LEGEND_BG   = HexColor("#f8f9fa")   # legend background
_C_LABEL       = HexColor("#1a2332")   # part labels

# Edge stroke widths (points)
_W_POLISHED = 3.0
_W_EASED    = 2.0
_W_RAW      = 1.0
_W_MITER    = 2.5
_W_FINISHED = 2.0
_W_DEFAULT  = 1.5

# Dimension offset outside part boundary
_DIM_OFFSET = 18.0   # pts gap from part edge to callout line
_DIM_GAP    = 8.0    # pts gap between tick and text

# Splash band width
_SPLASH_W   = 8.0    # pts

# Part gap
_PART_GAP   = 24.0   # pts between parts


class FabricationDrawingEngine:
    """
    Renders a full fabrication assembly drawing onto a ReportLab canvas zone.

    Usage:
        engine = FabricationDrawingEngine()
        engine.draw_assembly(
            c=canvas,
            assembly=assembly,
            zone_x=margin, zone_y=bottom_y,
            zone_w=drawing_width, zone_h=drawing_height,
        )
    """

    def draw_assembly(
        self,
        c: rl_canvas.Canvas,
        assembly: Assembly,
        zone_x: float,
        zone_y: float,
        zone_w: float,
        zone_h: float,
        is_mirror: bool = False,
    ) -> float:
        """
        Draw all parts of an assembly scaled to fit the zone.
        Returns the actual height used (for layout calculations).

        zone_x, zone_y = bottom-left of drawing zone (ReportLab coords)
        zone_w, zone_h = available width and height
        is_mirror: if True, apply horizontal flip for MIR assemblies
        """
        parts = assembly.parts
        if not parts:
            self._draw_no_parts_message(c, zone_x, zone_y, zone_w, zone_h)
            return zone_h * 0.2

        # Calculate layout
        layout = self._compute_layout(parts, zone_w, zone_h)
        scale = layout["scale"]
        positions = layout["positions"]  # list of (px, py) bottom-left per part in zone coords

        # Apply mirror transform if needed
        if is_mirror or assembly.variant == UnitVariant.MIRROR:
            positions = self._mirror_positions(positions, parts, scale, zone_w)

        # Draw each part
        for i, (part, (px, py)) in enumerate(zip(parts, positions)):
            abs_x = zone_x + px
            abs_y = zone_y + py
            pw = part.dimensions.length * scale
            ph = part.dimensions.depth  * scale
            label = chr(65 + i)

            self._draw_part_outline(c, part, abs_x, abs_y, pw, ph, label)
            self._draw_splash_bands(c, part, abs_x, abs_y, pw, ph, scale)
            self._draw_cutouts(c, part, abs_x, abs_y, pw, ph, scale)
            self._draw_holes(c, part, abs_x, abs_y, pw, ph, scale)
            self._draw_edge_treatments(c, part, abs_x, abs_y, pw, ph)
            self._draw_dimensions(c, part, abs_x, abs_y, pw, ph, scale)

        # Draw seam lines between adjacent parts
        for i in range(len(parts) - 1):
            _, (px, py) = parts[i], positions[i]
            pw = parts[i].dimensions.length * scale
            seam_x = zone_x + px + pw
            seam_y1 = zone_y + py
            seam_y2 = zone_y + py + parts[i].dimensions.depth * scale
            self._draw_seam(c, seam_x, seam_y1, seam_y2)

        return layout["total_height"]

    def draw_edge_legend(
        self, c: rl_canvas.Canvas,
        x: float, y: float, w: float = 160.0
    ) -> float:
        """
        Draw a compact edge type legend box.
        Returns height used.
        """
        entries = [
            (_C_POLISHED, _W_POLISHED, None, "Polished Edge (Exposed)"),
            (_C_EASED,    _W_EASED,    None, "Eased Edge"),
            (_C_MITER,    _W_MITER,    None, "Miter Edge"),
            (_C_FINISHED, _W_FINISHED, None, "Finished Edge"),
            (_C_RAW,      _W_RAW,      [3, 2], "Raw / Wall Contact"),
        ]
        row_h = 14.0
        pad = 6.0
        total_h = pad * 2 + len(entries) * row_h + 14

        c.setFillColor(_C_LEGEND_BG)
        c.setStrokeColor(HexColor("#cccccc"))
        c.setLineWidth(0.5)
        c.rect(x, y - total_h, w, total_h, fill=1, stroke=1)

        c.setFillColor(_C_LABEL)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(x + pad, y - pad - 8, "EDGE LEGEND")

        ey = y - pad - 8 - 4
        for color, lw, dash, label in entries:
            ey -= row_h
            c.setStrokeColor(color)
            c.setLineWidth(lw)
            if dash:
                c.setDash(*dash)
            else:
                c.setDash(1, 0)
            c.line(x + pad, ey + 4, x + pad + 24, ey + 4)
            c.setDash(1, 0)
            c.setFillColor(_C_LABEL)
            c.setFont("Helvetica", 6)
            c.drawString(x + pad + 28, ey, label)

        return total_h

    # ------------------------------------------------------------------
    # Part outline
    # ------------------------------------------------------------------

    def _draw_part_outline(
        self, c: rl_canvas.Canvas,
        part: Part, x: float, y: float, pw: float, ph: float, label: str
    ):
        """Draw the stone slab rectangle with fill. Edges drawn separately."""
        # Fill
        c.setFillColor(_C_PART_FILL)
        c.setStrokeColor(_C_PART_STROKE)
        c.setLineWidth(_W_DEFAULT)
        c.setDash(1, 0)
        c.rect(x, y, pw, ph, fill=1, stroke=1)

        # Part label — top-left inside part
        c.setFillColor(_C_LABEL)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(x + 5, y + ph - 13, f"PART {label}")

        # Part name — small below label
        c.setFont("Helvetica", 7)
        c.setFillColor(HexColor("#555555"))
        # Truncate name if too long for part width
        name = part.name
        max_chars = max(8, int(pw / 5))
        if len(name) > max_chars:
            name = name[:max_chars - 1] + "…"
        c.drawString(x + 5, y + ph - 23, name)

    # ------------------------------------------------------------------
    # Edge treatments — draw line on correct edge with style
    # ------------------------------------------------------------------

    def _draw_edge_treatments(
        self, c: rl_canvas.Canvas,
        part: Part, x: float, y: float, pw: float, ph: float
    ):
        """
        Draw styled edge lines over the part outline.
        Each edge position maps to a side of the rectangle.
        """
        edge_map: dict = {e.position: e for e in part.edges}

        sides = [
            (Position.FRONT, (x, y,       x + pw, y)),        # bottom
            (Position.BACK,  (x, y + ph,  x + pw, y + ph)),   # top
            (Position.LEFT,  (x, y,       x, y + ph)),         # left
            (Position.RIGHT, (x + pw, y,  x + pw, y + ph)),   # right
        ]

        for pos, (x1, y1, x2, y2) in sides:
            edge = edge_map.get(pos)
            if edge:
                self._set_edge_style(c, edge.edge_type)
                c.line(x1, y1, x2, y2)
            # Reset
        c.setDash(1, 0)
        c.setLineWidth(_W_DEFAULT)
        c.setStrokeColor(_C_PART_STROKE)

    def _set_edge_style(self, c: rl_canvas.Canvas, edge_type: EdgeType):
        if edge_type == EdgeType.POLISHED:
            c.setStrokeColor(_C_POLISHED)
            c.setLineWidth(_W_POLISHED)
            c.setDash(1, 0)
        elif edge_type == EdgeType.EASED:
            c.setStrokeColor(_C_EASED)
            c.setLineWidth(_W_EASED)
            c.setDash(1, 0)
        elif edge_type == EdgeType.MITER:
            c.setStrokeColor(_C_MITER)
            c.setLineWidth(_W_MITER)
            c.setDash(4, 2)
        elif edge_type == EdgeType.FINISHED:
            c.setStrokeColor(_C_FINISHED)
            c.setLineWidth(_W_FINISHED)
            c.setDash(1, 0)
        elif edge_type == EdgeType.RAW:
            c.setStrokeColor(_C_RAW)
            c.setLineWidth(_W_RAW)
            c.setDash(3, 2)
        else:
            c.setStrokeColor(_C_PART_STROKE)
            c.setLineWidth(_W_DEFAULT)
            c.setDash(1, 0)

    # ------------------------------------------------------------------
    # Cutout overlays
    # ------------------------------------------------------------------

    def _draw_cutouts(
        self, c: rl_canvas.Canvas,
        part: Part, x: float, y: float, pw: float, ph: float, scale: float
    ):
        for co in part.cutouts:
            cw = co.dimensions.length * scale
            ch = co.dimensions.depth  * scale
            # center_x/center_y from part origin (0,0 = bottom-left of part)
            cx = x + co.center_x * scale - cw / 2
            cy = y + co.center_y * scale - ch / 2

            # Clip to part bounds
            cx = max(x, min(cx, x + pw - cw))
            cy = max(y, min(cy, y + ph - ch))

            c.setFillColor(_C_CUTOUT_FILL)
            c.setStrokeColor(_C_CUTOUT_STR)
            c.setLineWidth(1.5)
            c.setDash(4, 2)

            # Sink cutouts get rounded corners (r = 4pts represents actual radius)
            if co.cutout_type == CutoutType.SINK:
                radius = min(6.0, cw * 0.08, ch * 0.08)
                c.roundRect(cx, cy, cw, ch, radius, fill=1, stroke=1)
            else:
                c.rect(cx, cy, cw, ch, fill=1, stroke=1)

            c.setDash(1, 0)

            # Cutout label inside rectangle
            if cw > 20 and ch > 10:
                c.setFillColor(_C_CUTOUT_STR)
                c.setFont("Helvetica-Bold", 6)
                lbl = co.cutout_type.value.replace("_", " ").upper()
                if len(lbl) * 4 > cw:
                    lbl = lbl[:int(cw / 4)]
                c.drawCentredString(cx + cw / 2, cy + ch / 2 - 3, lbl)

                # Mount type annotation
                mount_str = "U/M" if co.mount_type == MountType.UNDERMOUNT else "O/M"
                c.setFont("Helvetica", 5)
                c.drawCentredString(cx + cw / 2, cy + 2, mount_str)

            # Center offset dimension callout (X from left, Y from front)
            self._draw_cutout_dims(c, co, x, y, cx, cy, cw, ch, scale)

    def _draw_cutout_dims(
        self, c: rl_canvas.Canvas, co: Cutout,
        px: float, py: float, cx: float, cy: float,
        cw: float, ch: float, scale: float
    ):
        """Small tick-mark dimension callouts from part edge to cutout center."""
        c.setStrokeColor(_C_DIM)
        c.setLineWidth(0.5)
        c.setDash(1, 0)
        c.setFillColor(_C_DIM)
        c.setFont("Helvetica", 5)

        # X offset — from left edge to cutout center (horizontal)
        center_cx = cx + cw / 2
        dim_y = py - 10
        c.line(px, dim_y, center_cx, dim_y)
        c.line(px, dim_y - 4, px, dim_y + 4)
        c.line(center_cx, dim_y - 4, center_cx, dim_y + 4)
        c.drawCentredString((px + center_cx) / 2, dim_y - 10, f'{co.center_x}"')

    # ------------------------------------------------------------------
    # Holes
    # ------------------------------------------------------------------

    def _draw_holes(
        self, c: rl_canvas.Canvas,
        part: Part, x: float, y: float, pw: float, ph: float, scale: float
    ):
        for hole in part.holes:
            hx = x + hole.center_x * scale
            hy = y + hole.center_y * scale
            r  = max(3.0, (hole.diameter / 2) * scale)

            c.setFillColor(_C_CUTOUT_FILL)
            c.setStrokeColor(_C_HOLE)
            c.setLineWidth(1.5)
            c.setDash(1, 0)
            c.circle(hx, hy, r, fill=1, stroke=1)

            # Cross-hair inside circle
            c.setLineWidth(0.5)
            c.line(hx - r * 0.7, hy, hx + r * 0.7, hy)
            c.line(hx, hy - r * 0.7, hx, hy + r * 0.7)

            # Ø label above circle
            c.setFillColor(_C_HOLE)
            c.setFont("Helvetica-Bold", 6)
            label = f'Ø{hole.diameter}"'
            c.drawCentredString(hx, hy + r + 3, label)

            # Purpose label below
            if hole.purpose:
                c.setFont("Helvetica", 5)
                c.drawCentredString(hx, hy - r - 8, hole.purpose)

    # ------------------------------------------------------------------
    # Splash bands
    # ------------------------------------------------------------------

    def _draw_splash_bands(
        self, c: rl_canvas.Canvas,
        part: Part, x: float, y: float, pw: float, ph: float, scale: float
    ):
        for sp in part.splashes:
            stype = sp.splash_type.value.lower()
            sw = sp.dimensions.length  * scale
            sd = sp.dimensions.depth   * scale

            c.setFillColor(_C_SPLASH_FILL)
            c.setStrokeColor(_C_SPLASH)
            c.setLineWidth(1.0)
            c.setDash(1, 0)

            if "back" in stype:
                # Band along top edge (back of part)
                bw = min(sw, pw)
                bh = min(sd, _SPLASH_W)
                c.rect(x, y + ph, bw, bh, fill=1, stroke=1)
                c.setFillColor(_C_SPLASH)
                c.setFont("Helvetica", 5)
                if bw > 20:
                    c.drawCentredString(x + bw / 2, y + ph + bh / 2 - 2, f'BSP {sp.dimensions.depth}"')

            elif "left" in stype:
                bw = min(sd, _SPLASH_W)
                bh = min(sw, ph)
                c.rect(x - bw, y, bw, bh, fill=1, stroke=1)
                c.setFillColor(_C_SPLASH)
                c.setFont("Helvetica", 5)
                if bh > 14:
                    c.drawCentredString(x - bw / 2, y + bh / 2, "L-SP")

            elif "right" in stype:
                bw = min(sd, _SPLASH_W)
                bh = min(sw, ph)
                c.rect(x + pw, y, bw, bh, fill=1, stroke=1)
                c.setFillColor(_C_SPLASH)
                c.setFont("Helvetica", 5)
                if bh > 14:
                    c.drawCentredString(x + pw + bw / 2, y + bh / 2, "R-SP")

    # ------------------------------------------------------------------
    # Dimension callout lines
    # ------------------------------------------------------------------

    def _draw_dimensions(
        self, c: rl_canvas.Canvas,
        part: Part, x: float, y: float, pw: float, ph: float, scale: float
    ):
        dims = part.dimensions
        c.setStrokeColor(_C_DIM)
        c.setLineWidth(0.75)
        c.setDash(1, 0)
        c.setFillColor(_C_DIM)

        # ── Width dim (horizontal, below part) ───────────────────────
        dim_y = y - _DIM_OFFSET
        # Extension lines
        c.line(x,       y,     x,       dim_y)
        c.line(x + pw,  y,     x + pw,  dim_y)
        # Dimension line with arrowheads
        self._dim_line_h(c, x, dim_y, pw)
        # Text
        c.setFont("Helvetica", 7)
        c.drawCentredString(x + pw / 2, dim_y - _DIM_GAP, f'{dims.length}"')

        # ── Depth dim (vertical, right of part) ──────────────────────
        dim_x = x + pw + _DIM_OFFSET
        # Extension lines
        c.line(x + pw,  y,      dim_x, y)
        c.line(x + pw,  y + ph, dim_x, y + ph)
        # Dimension line with arrowheads
        self._dim_line_v(c, dim_x, y, ph)
        # Text (rotated)
        c.saveState()
        c.translate(dim_x + _DIM_GAP + 6, y + ph / 2)
        c.rotate(90)
        c.setFont("Helvetica", 7)
        c.drawCentredString(0, 0, f'{dims.depth}"')
        c.restoreState()

        # ── Thickness annotation (small text on part) ─────────────────
        if dims.thickness:
            c.setFont("Helvetica", 6)
            c.setFillColor(HexColor("#888888"))
            c.drawCentredString(x + pw / 2, y + 5, f'Thk: {dims.thickness}"')

    def _dim_line_h(self, c: rl_canvas.Canvas, x: float, y: float, length: float):
        """Draw horizontal dimension line with tick marks at ends."""
        c.setLineWidth(0.75)
        c.line(x, y, x + length, y)
        # Ticks
        c.line(x, y - 3, x, y + 3)
        c.line(x + length, y - 3, x + length, y + 3)

    def _dim_line_v(self, c: rl_canvas.Canvas, x: float, y: float, height: float):
        """Draw vertical dimension line with tick marks at ends."""
        c.setLineWidth(0.75)
        c.line(x, y, x, y + height)
        c.line(x - 3, y, x + 3, y)
        c.line(x - 3, y + height, x + 3, y + height)

    # ------------------------------------------------------------------
    # Seam line
    # ------------------------------------------------------------------

    def _draw_seam(self, c: rl_canvas.Canvas, x: float, y1: float, y2: float):
        """Draw a vertical seam line between two adjacent parts."""
        c.setStrokeColor(_C_SEAM)
        c.setLineWidth(1.5)
        c.setDash(5, 2)
        c.line(x, y1, x, y2)
        c.setDash(1, 0)
        # Seam label
        mid_y = (y1 + y2) / 2
        c.setFillColor(_C_SEAM)
        c.setFont("Helvetica-Bold", 5)
        c.drawCentredString(x, mid_y + 2, "SEAM")

    # ------------------------------------------------------------------
    # Layout computation
    # ------------------------------------------------------------------

    def _compute_layout(
        self, parts: List[Part], zone_w: float, zone_h: float
    ) -> dict:
        """
        Compute scale and part positions to fit all parts in the zone.

        Returns:
            scale: pts per inch
            positions: list of (x, y) bottom-left per part in zone-local coords
            total_height: actual height used (pts)
        """
        n = len(parts)
        # Total raw width and max raw depth (in inches)
        total_raw_w = sum(p.dimensions.length for p in parts)
        max_raw_h   = max(p.dimensions.depth for p in parts)

        # Reserve space for dimension callouts
        dim_margin_w = _DIM_OFFSET + 20.0   # right-side depth dim
        dim_margin_h = _DIM_OFFSET + 15.0   # below width dim

        avail_w = zone_w - dim_margin_w - _PART_GAP * (n - 1) - _SPLASH_W * 2
        avail_h = zone_h - dim_margin_h - _SPLASH_W * 2 - 30.0  # 30pt for labels

        # Avoid division by zero
        avail_w = max(avail_w, 20.0)
        avail_h = max(avail_h, 20.0)

        scale_w = avail_w / max(total_raw_w, 0.1)
        scale_h = avail_h / max(max_raw_h, 0.1)
        scale   = min(scale_w, scale_h, 6.0)   # cap at 6 pts/inch (very large parts)
        scale   = max(scale, 0.8)               # floor at 0.8 pts/inch

        # Position parts left-to-right, starting offset for splash bands
        positions = []
        cursor_x  = _SPLASH_W + 4.0
        # Vertical: centre each part relative to zone height (above dimension space)
        base_y    = dim_margin_h + _SPLASH_W + 4.0

        for part in parts:
            positions.append((cursor_x, base_y))
            cursor_x += part.dimensions.length * scale + _PART_GAP

        total_height = base_y + max_raw_h * scale + _SPLASH_W + 30.0
        return {"scale": scale, "positions": positions, "total_height": total_height}

    def _mirror_positions(
        self, positions: List[Tuple[float, float]],
        parts: List[Part], scale: float, zone_w: float
    ) -> List[Tuple[float, float]]:
        """Flip X coordinates for MIR assemblies."""
        mirrored = []
        for (px, py), part in zip(positions, parts):
            pw = part.dimensions.length * scale
            new_x = zone_w - px - pw
            mirrored.append((new_x, py))
        # Re-sort left to right
        combined = sorted(zip(mirrored, parts), key=lambda item: item[0][0])
        return [pos for pos, _ in combined]

    def _draw_no_parts_message(
        self, c: rl_canvas.Canvas, x: float, y: float, w: float, h: float
    ):
        c.setFillColor(HexColor("#eeeeee"))
        c.rect(x, y, w, h, fill=1, stroke=0)
        c.setFillColor(HexColor("#888888"))
        c.setFont("Helvetica", 10)
        c.drawCentredString(x + w / 2, y + h / 2, "No parts defined for this assembly.")
