"""
Fabrication Drawing Engine  (Phase 19 — Geometry-Aware Composition)
======================================================================
Renders fabrication shop drawings with geometry-driven, edge-aware placement.

Key improvements over Phase 4:
  - Two-zone layout: backsplash/side-splash pieces in TOP zone as separate
    rectangular stone pieces; main countertop pieces in BOTTOM zone.
  - Each splash piece is horizontally aligned (centered) above the main top
    with the matching width — NOT drawn as an edge band overlay.
  - Splash bands on the main top are suppressed when separate splash parts
    already exist in the assembly's parts list.
  - Scale calculation uses min(w_scale, h_scale) — previously used max (bug).
  - L-shape detection and corner-indicator annotation.
  - Edge-aware seam lines: only between adjacent main-top parts.
  - Collision-aware gap accounting.

Drawing conventions match Virgin Surfaces reference PDFs:
  - Polished edges: thick dark line + "X" midpoint mark
  - Raw/wall edges: thin grey dashed line
  - Piece numbers: large grey centred text inside each rectangle
  - BS label on thin (backsplash) pieces
  - Dual inch/mm dimensions: 28.5" [724]

Coordinate system:
  ReportLab y=0 at bottom of page.
  zone_y = bottom of drawing zone.
  Splash pieces drawn ABOVE main tops (higher y value).
"""

from __future__ import annotations

import math
import re
from typing import List, Optional, Tuple

from reportlab.lib.colors import HexColor
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas as rl_canvas

from app.models.fabrication import (
    Assembly, Cutout, CutoutType, EdgeTreatment, EdgeType,
    Hole, MountType, Part, PartType, Position, Splash, SplashType,
)
from app.models.hierarchy import UnitVariant


# ---------------------------------------------------------------------------
# Drawing constants — matches professional fabrication shop drawing conventions.
# All stone pieces: white fill, black/dark-grey lines, weight = edge type.
# Colour is ONLY used for sink cutouts (red) to match reference PDFs.
# ---------------------------------------------------------------------------
_C_PART_FILL   = HexColor("#ffffff")   # white — matches reference CAD style
_C_PART_STROKE = HexColor("#1a2332")   # dark navy outline
_C_POLISHED    = HexColor("#1a2332")   # polished edge — thick dark
_C_RAW         = HexColor("#666666")   # raw/wall contact — medium grey, dashed
_C_EASED       = HexColor("#333333")   # eased — dark, medium weight
_C_MITER       = HexColor("#333333")   # miter — dark, dashed pattern
_C_FINISHED    = HexColor("#333333")   # finished — dark
_C_CUTOUT_FILL = HexColor("#ffffff")   # cutout interior — white void
_C_CUTOUT_STR  = HexColor("#c0392b")   # cutout outline — red dashed (in all refs)
_C_HOLE        = HexColor("#444444")   # hole circle — dark grey
_C_SPLASH_FILL = HexColor("#f5f5f5")   # splash piece — very light grey (not white)
_C_SPLASH_STR  = HexColor("#444444")   # splash outline — dark grey
_C_SEAM        = HexColor("#e74c3c")   # seam line — red (visible in references)
_C_DIM         = HexColor("#333333")   # dimension lines — dark grey
_C_LEGEND_BG   = HexColor("#f8f9fa")   # legend background
_C_LABEL       = HexColor("#1a2332")   # part labels
_C_WHITE       = HexColor("#ffffff")
_C_GREY        = HexColor("#888888")

# Edge stroke widths — line weight IS the visual differentiator (no colour)
_W_POLISHED = 2.5   # exposed polished edge — thickest
_W_EASED    = 1.5   # eased edge — medium
_W_RAW      = 0.75  # raw/wall contact — thinnest, dashed
_W_MITER    = 1.5   # miter — medium, dashed
_W_FINISHED = 1.5   # finished — medium
_W_DEFAULT  = 1.0

# Layout constants
_DIM_OFFSET = 18.0   # pts gap from part edge to callout line
_DIM_GAP    = 8.0    # pts gap between tick and text
_PART_GAP   = 24.0   # pts between parts in same row
_ROW_GAP    = 36.0   # pts between splash row and main-top row
_SPLASH_W   = 8.0    # legacy constant kept for compatibility

# Depth threshold: parts at or below this depth are treated as splash pieces
_SPLASH_MAX_DEPTH_IN = 5.5

_INCH_TO_MM = 25.4

# Dimension display styles
DIM_INCH_MM  = "inch_mm"   # 28.5" [724]        — BULL OUTDOOR / default
DIM_FRAC     = "frac"      # 23 1/4"             — Deforest / US CAD style
DIM_DECIMAL  = "decimal"   # 28.5"               — simple decimal
DIM_LONG_MM  = "long_mm"   # 28.5 in [724 mm]    — Concord North style


def format_dimension_inch_mm(inches: float, precision: int = 1) -> str:
    """Virgin-style dual dimension: 28.5\" [724]."""
    if precision == 0:
        val = str(int(round(inches)))
    else:
        val = f"{inches:.{precision}f}".rstrip("0").rstrip(".")
    mm = int(round(inches * _INCH_TO_MM))
    return f'{val}" [{mm}]'


def format_dimension_frac(inches: float) -> str:
    """
    US fractional inch notation matching Deforest/Haven reference style.
    Examples: 23 1/4", 25 1/2", 4", 110 3/4"
    """
    _FRAC: dict = {
        0: '',    1: '1/8', 2: '1/4', 3: '3/8',
        4: '1/2', 5: '5/8', 6: '3/4', 7: '7/8',
    }
    if inches <= 0:
        return '0"'
    whole = int(inches)
    eighths = round((inches - whole) * 8)
    if eighths >= 8:
        whole += 1
        eighths = 0
    frac = _FRAC.get(eighths, f'{eighths}/8')
    if whole == 0:
        return f'{frac}"' if frac else '0"'
    return f'{whole} {frac}"' if frac else f'{whole}"'


def format_dimension_long_mm(inches: float) -> str:
    """Concord North style: 28.5 in [724 mm]."""
    mm = int(round(inches * _INCH_TO_MM))
    val = f"{inches:.3g}"
    return f'{val} in [{mm} mm]'


def fmt_dim(inches: float, style: str = DIM_INCH_MM) -> str:
    """Dispatch to the correct dimension formatter for the given style."""
    if style == DIM_FRAC:
        return format_dimension_frac(inches)
    if style == DIM_DECIMAL:
        val = f"{inches:.3g}"
        return f'{val}"'
    if style == DIM_LONG_MM:
        return format_dimension_long_mm(inches)
    return format_dimension_inch_mm(inches)   # DIM_INCH_MM default


def dim_style_label(style: str) -> str:
    """Human-readable scale note for the given dimension style."""
    return {
        DIM_FRAC:    "Dimensions in fractional inches",
        DIM_DECIMAL: "Dimensions in inches",
        DIM_LONG_MM: "Dimensions in inches [mm]",
    }.get(style, "Dimensions in inch [mm]")


def format_scale_ratio(pts_per_inch: float) -> str:
    """
    Convert an internal pts/inch scale factor to a paper scale string.

    ReportLab: 72 pts = 1 printed inch.
    pts_per_inch / 72 = printed inches per model inch.
    Multiplied by 12 → printed inches per model foot.
    Round to nearest common architectural scale.

    Examples:
        6.24 pts/in → 0.087 in/in → 1.04 in/ft → nearest 1.0 → 1" = 1'-0"
        8.0  pts/in → 0.111 in/in → 1.33 in/ft → nearest 1.5 → 1 1/2" = 1'-0"
        3.0  pts/in → 0.042 in/in → 0.5  in/ft → nearest 0.5 → 1/2" = 1'-0"
    """
    paper_per_foot = (pts_per_inch / 72.0) * 12.0
    _SCALES = [
        (3.0, '3"'), (2.0, '2"'), (1.5, '1 1/2"'), (1.0, '1"'),
        (0.75, '3/4"'), (0.5, '1/2"'), (0.375, '3/8"'),
        (0.25, '1/4"'), (0.125, '1/8"'),
    ]
    closest_label = min(_SCALES, key=lambda s: abs(s[0] - paper_per_foot))[1]
    return f"{closest_label} = 1'-0\""


def _piece_index_from_name(name: str, fallback: int) -> int:
    m = re.search(r"piece\s*(\d+)", name, re.I)
    return int(m.group(1)) if m else fallback


def _parse_part_annotations(notes: Optional[str]) -> dict:
    text = (notes or "").lower()
    radii: List[str] = re.findall(r"r\s*1\s*/\s*(\d+)", notes or "", re.I)
    return {
        "grain": "grain" in text,
        "break_corners": "break corner" in text,
        "radii": [f"R1/{d}" for d in radii],
    }


def _is_splash_part(part: Part) -> bool:
    """True if this Part represents a backsplash or side-splash stone piece."""
    return part.dimensions.depth <= _SPLASH_MAX_DEPTH_IN


def _get_splash_label(part: Part) -> str:
    """Return BS, L-SS, R-SS, or SS based on the part's name."""
    name = (part.name or "").lower()
    if "left" in name or "l-ss" in name or "l_ss" in name:
        return "L-SS"
    if "right" in name or "r-ss" in name or "r_ss" in name:
        return "R-SS"
    if "side" in name or " ss" in name or name.startswith("ss"):
        return "SS"
    return "BS"  # default: backsplash


class FabricationDrawingEngine:
    """
    Renders a full fabrication assembly drawing onto a ReportLab canvas zone.

    Usage::

        engine = FabricationDrawingEngine()
        engine.draw_assembly(
            c=canvas,
            assembly=assembly,
            zone_x=margin, zone_y=bottom_y,
            zone_w=drawing_width, zone_h=drawing_height,
        )
    """

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def draw_assembly(
        self,
        c: rl_canvas.Canvas,
        assembly: Assembly,
        zone_x: float,
        zone_y: float,
        zone_w: float,
        zone_h: float,
        is_mirror: bool = False,
        shop_sheet_layout: bool = False,
        dim_style: str = DIM_INCH_MM,
    ) -> float:
        """
        Draw all parts of an assembly scaled to fit the zone.

        Returns the actual height used (pts) for layout calculations.

        Geometry-aware rules applied here:
          - Thin parts (depth ≤ 5.5") → splash zone (top area).
          - Deep parts → main-top zone (bottom area).
          - Each splash piece is x-aligned above its width-matching main top.
          - Splash bands are NOT drawn on main tops when separate splash parts
            exist (they are redundant and incorrect in that case).
          - L-shape assemblies get a corner-angle indicator.
        """
        parts = assembly.parts
        if not parts:
            self._draw_no_parts_message(c, zone_x, zone_y, zone_w, zone_h)
            return zone_h * 0.2

        # Decide layout mode
        has_separate_splash_parts = any(_is_splash_part(p) for p in parts)
        has_main_tops = any(not _is_splash_part(p) for p in parts)
        is_l_shape = self._detect_l_shape(parts)

        # Use two-zone layout whenever the assembly mixes main tops with
        # separate splash/BS pieces — regardless of total part count.
        if has_separate_splash_parts and has_main_tops:
            layout = self._compute_shop_sheet_layout(parts, zone_w, zone_h)
        else:
            layout = self._compute_layout(parts, zone_w, zone_h)

        scale = layout["scale"]
        positions = layout["positions"]

        self._last_scale = scale   # expose for scale-ratio notation in callers

        if is_mirror or assembly.variant == UnitVariant.MIRROR:
            positions = self._mirror_positions(positions, parts, scale, zone_w)

        # Draw each part
        for i, (part, (px, py)) in enumerate(zip(parts, positions)):
            abs_x = zone_x + px
            abs_y = zone_y + py
            pw = part.dimensions.length * scale
            ph = part.dimensions.depth * scale
            label = chr(65 + i)
            piece_num = _piece_index_from_name(part.name, i + 1)
            ann = _parse_part_annotations(part.notes)
            splash_piece = _is_splash_part(part)

            self._draw_part_outline(c, part, abs_x, abs_y, pw, ph, label, piece_num)

            if splash_piece:
                # Splash piece: show type label, no cutouts/holes
                self._draw_splash_type_label(c, part, abs_x, abs_y, pw, ph)
                self._draw_splash_piece_edges(c, abs_x, abs_y, pw, ph)
            else:
                # Main top: cutouts, holes, optional splash bands
                self._draw_cutouts(c, part, abs_x, abs_y, pw, ph, scale, dim_style=dim_style)
                self._draw_holes(c, part, abs_x, abs_y, pw, ph, scale)
                if not has_separate_splash_parts:
                    self._draw_splash_bands(c, part, abs_x, abs_y, pw, ph, scale)

            self._draw_edge_treatments(c, part, abs_x, abs_y, pw, ph)
            self._draw_polished_edge_marks(c, part, abs_x, abs_y, pw, ph)

            if ann["grain"]:
                self._draw_grain_arrow(c, abs_x + pw / 2, abs_y + ph / 2, pw, horizontal=True)
            self._draw_corner_annotations(c, part, abs_x, abs_y, pw, ph, ann)
            self._draw_dimensions(c, part, abs_x, abs_y, pw, ph, scale, dim_style=dim_style)

        # Seam lines between adjacent main-top parts only
        if not shop_sheet_layout:
            main_pairs = [
                (parts[i], positions[i], parts[i + 1], positions[i + 1])
                for i in range(len(parts) - 1)
                if not _is_splash_part(parts[i]) and not _is_splash_part(parts[i + 1])
            ]
            for pa, (pax, pay), pb, (pbx, pby) in main_pairs:
                seam_x = zone_x + pax + pa.dimensions.length * scale
                next_x = zone_x + pbx
                if abs(seam_x - next_x) < _PART_GAP * 2.0:
                    self._draw_seam(
                        c, seam_x,
                        zone_y + pay,
                        zone_y + pay + pa.dimensions.depth * scale,
                    )

        # L-shape corner indicator
        if is_l_shape:
            self._draw_l_shape_indicator(c, parts, positions, scale, zone_x, zone_y)

        return layout["total_height"]

    # ------------------------------------------------------------------
    # Legend blocks
    # ------------------------------------------------------------------

    def draw_edge_legend(
        self, c: rl_canvas.Canvas,
        x: float, y: float, w: float = 160.0
    ) -> float:
        """Draw a compact edge-type legend box. Returns height used."""
        entries = [
            (_C_POLISHED, _W_POLISHED, None,   "Polished Edge (Exposed)"),
            (_C_EASED,    _W_EASED,    None,   "Eased Edge"),
            (_C_MITER,    _W_MITER,    None,   "Miter Edge"),
            (_C_FINISHED, _W_FINISHED, None,   "Finished Edge"),
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

    def draw_granite_quartz_key_notes(
        self, c: rl_canvas.Canvas, x: float, y: float, w: float = 200.0
    ) -> float:
        """Virgin Surfaces–style GRANITE/QUARTZ KEY NOTES legend."""
        entries = [
            ("X",   "3MM ROUND"),
            ("F",   "FLAT EDGE (STOVE POLISH)"),
            ("BS",  "BACK SPLASH"),
            ("SS",  "SIDE SPLASH"),
            ("TR",  '1/8" RADIUS'),
            ("RAW", "RAW EDGE"),
            ("□",   "OVERSIZED PART"),
        ]
        row_h = 11.0
        pad = 5.0
        title_h = 14.0
        total_h = pad * 2 + title_h + len(entries) * row_h + 8

        c.setFillColor(_C_WHITE)
        c.setStrokeColor(HexColor("#333333"))
        c.setLineWidth(0.75)
        c.rect(x, y - total_h, w, total_h, fill=1, stroke=1)

        c.setFillColor(_C_LABEL)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(x + pad, y - pad - 8, "GRANITE/QUARTZ KEY NOTES:")

        ey = y - pad - title_h
        c.setFont("Helvetica", 6)
        for sym, desc in entries:
            ey -= row_h
            c.setFont("Helvetica-Bold", 7)
            c.drawString(x + pad, ey, sym)
            c.setFont("Helvetica", 6)
            c.drawString(x + pad + 14, ey, f"= {desc}")

        c.setFont("Helvetica-Oblique", 5)
        c.setFillColor(_C_GREY)
        c.drawString(
            x + pad,
            y - total_h + 4,
            "ALL PARTS MADE TO SIZE UNLESS NOTED WITH A 'RECTANGLE' ON THE DIMENSION",
        )
        return total_h

    # ------------------------------------------------------------------
    # Part outline
    # ------------------------------------------------------------------

    def _draw_part_outline(
        self, c: rl_canvas.Canvas,
        part: Part, x: float, y: float, pw: float, ph: float,
        label: str, piece_num: Optional[int] = None,
    ):
        """Draw the stone slab rectangle with fill. Edges drawn separately."""
        is_splash = _is_splash_part(part)
        fill_color = _C_SPLASH_FILL if is_splash else _C_PART_FILL

        c.setFillColor(fill_color)
        c.setStrokeColor(_C_PART_STROKE)
        c.setLineWidth(_W_DEFAULT)
        c.setDash(1, 0)
        c.rect(x, y, pw, ph, fill=1, stroke=1)

        # Large centred piece number — light grey, prominent but not dominant
        if piece_num is not None and pw > 30 and ph > 18:
            num_font = min(
                40 if not is_splash else 16,   # bigger cap for main tops
                ph * 0.60,                     # max 60 % of piece height
                pw * 0.45,                     # max 45 % of piece width
            )
            c.setFillColor(HexColor("#bbbbbb"))   # light grey
            c.setFont("Helvetica-Bold", num_font)
            c.drawCentredString(x + pw / 2, y + ph / 2 - num_font * 0.30, str(piece_num))


    # ------------------------------------------------------------------
    # Splash piece drawing
    # ------------------------------------------------------------------

    def _draw_splash_type_label(
        self, c: rl_canvas.Canvas,
        part: Part, x: float, y: float, pw: float, ph: float,
    ):
        """Draw BS / SS type label prominently on a splash piece."""
        lbl = _get_splash_label(part)
        c.setFillColor(_C_LABEL)
        c.setFont("Helvetica-Bold", min(8, ph * 0.6))
        c.drawString(x + 4, y + ph - 10, lbl)

        # Part name below label
        if pw > 40:
            c.setFont("Helvetica", 5.5)
            c.setFillColor(_C_GREY)
            name = part.name
            max_chars = max(8, int(pw / 5))
            if len(name) > max_chars:
                name = name[: max_chars - 1] + "…"
            c.drawString(x + 4, y + ph - 18, name)

    def _draw_splash_piece_edges(
        self, c: rl_canvas.Canvas,
        x: float, y: float, pw: float, ph: float,
    ):
        """
        Draw edge treatment for a splash piece:
          Top, Left, Right → polished (dark, thick)
          Bottom            → raw/wall contact (grey, dashed)
        """
        # Top polished
        c.setStrokeColor(_C_POLISHED)
        c.setLineWidth(_W_POLISHED)
        c.setDash(1, 0)
        c.line(x, y + ph, x + pw, y + ph)

        # Left polished
        c.line(x, y, x, y + ph)

        # Right polished
        c.line(x + pw, y, x + pw, y + ph)

        # Bottom raw (wall contact)
        c.setStrokeColor(_C_RAW)
        c.setLineWidth(_W_RAW)
        c.setDash(3, 2)
        c.line(x, y, x + pw, y)
        c.setDash(1, 0)

        # X marks on polished edges
        c.setFillColor(_C_LABEL)
        c.setFont("Helvetica-Bold", 7)
        if pw > 20:
            c.drawCentredString(x + pw / 2, y + ph + 2, "X")
        if ph > 12:
            c.drawCentredString(x - 7, y + ph / 2, "X")
            c.drawCentredString(x + pw + 7, y + ph / 2, "X")

    # ------------------------------------------------------------------
    # Edge treatments — styled lines over part outline
    # ------------------------------------------------------------------

    def _draw_edge_treatments(
        self, c: rl_canvas.Canvas,
        part: Part, x: float, y: float, pw: float, ph: float,
    ):
        """Draw styled edge lines. Each edge position maps to a side."""
        edge_map: dict = {e.position: e for e in part.edges}

        sides = [
            (Position.FRONT, (x,      y,      x + pw, y)),
            (Position.BACK,  (x,      y + ph, x + pw, y + ph)),
            (Position.LEFT,  (x,      y,      x,      y + ph)),
            (Position.RIGHT, (x + pw, y,      x + pw, y + ph)),
        ]

        for pos, (x1, y1, x2, y2) in sides:
            edge = edge_map.get(pos)
            if edge:
                self._set_edge_style(c, edge.edge_type)
                c.line(x1, y1, x2, y2)

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
    # Polished edge X marks
    # ------------------------------------------------------------------

    def _draw_polished_edge_marks(
        self, c: rl_canvas.Canvas,
        part: Part, x: float, y: float, pw: float, ph: float,
    ):
        """X tick marks on explicitly polished edges (reference convention)."""
        edge_map = {e.position: e for e in part.edges}
        sides = [
            (Position.FRONT, x + pw / 2, y),
            (Position.BACK,  x + pw / 2, y + ph),
            (Position.LEFT,  x,           y + ph / 2),
            (Position.RIGHT, x + pw,      y + ph / 2),
        ]
        c.setFillColor(_C_LABEL)
        c.setFont("Helvetica-Bold", 7)
        for pos, tx, ty in sides:
            edge = edge_map.get(pos)
            if edge and edge.edge_type == EdgeType.POLISHED:
                c.drawCentredString(tx, ty, "X")

    # ------------------------------------------------------------------
    # Cutout overlays
    # ------------------------------------------------------------------

    def _draw_cutouts(
        self, c: rl_canvas.Canvas,
        part: Part, x: float, y: float, pw: float, ph: float, scale: float,
        dim_style: str = DIM_INCH_MM,
    ):
        for co in part.cutouts:
            cw = co.dimensions.length * scale
            ch = co.dimensions.depth  * scale
            cx = x + co.center_x * scale - cw / 2
            cy = y + co.center_y * scale - ch / 2

            cx = max(x, min(cx, x + pw - cw))
            cy = max(y, min(cy, y + ph - ch))

            c.setFillColor(_C_CUTOUT_FILL)
            c.setStrokeColor(_C_CUTOUT_STR)
            c.setLineWidth(1.5)
            c.setDash(4, 2)

            if co.cutout_type == CutoutType.SINK:
                radius = min(6.0, cw * 0.08, ch * 0.08)
                c.roundRect(cx, cy, cw, ch, radius, fill=1, stroke=1)
            else:
                c.rect(cx, cy, cw, ch, fill=1, stroke=1)

            c.setDash(1, 0)

            if cw > 20 and ch > 10:
                c.setFillColor(_C_CUTOUT_STR)
                c.setFont("Helvetica-Bold", 6)
                if co.cutout_type == CutoutType.SINK:
                    mount = "Undermount" if co.mount_type == MountType.UNDERMOUNT else "Top mount"
                    lbl = f"{mount} Sink"
                else:
                    lbl = co.cutout_type.value.replace("_", " ").title()
                c.drawCentredString(cx + cw / 2, cy + ch / 2 - 2, lbl)

                mount_str = "U/M" if co.mount_type == MountType.UNDERMOUNT else "O/M"
                c.setFont("Helvetica", 5)
                c.drawCentredString(cx + cw / 2, cy + 2, mount_str)

            self._draw_cutout_dims(c, co, x, y, cx, cy, cw, ch, scale, dim_style=dim_style)

    def _draw_cutout_dims(
        self, c: rl_canvas.Canvas, co: Cutout,
        px: float, py: float, cx: float, cy: float,
        cw: float, ch: float, scale: float,
        dim_style: str = DIM_INCH_MM,
    ):
        c.setStrokeColor(_C_DIM)
        c.setLineWidth(0.5)
        c.setDash(1, 0)
        c.setFillColor(_C_DIM)
        c.setFont("Helvetica", 5)

        center_cx = cx + cw / 2
        dim_y = py - 10
        c.line(px, dim_y, center_cx, dim_y)
        c.line(px, dim_y - 4, px, dim_y + 4)
        c.line(center_cx, dim_y - 4, center_cx, dim_y + 4)
        c.drawCentredString(
            (px + center_cx) / 2,
            dim_y - 10,
            fmt_dim(co.center_x, dim_style),
        )

    # ------------------------------------------------------------------
    # Holes
    # ------------------------------------------------------------------

    def _draw_holes(
        self, c: rl_canvas.Canvas,
        part: Part, x: float, y: float, pw: float, ph: float, scale: float,
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

            c.setLineWidth(0.5)
            c.line(hx - r * 0.7, hy, hx + r * 0.7, hy)
            c.line(hx, hy - r * 0.7, hx, hy + r * 0.7)

            c.setFillColor(_C_HOLE)
            c.setFont("Helvetica-Bold", 6)
            c.drawCentredString(hx, hy + r + 3, f'Ø{hole.diameter}"')

            if hole.purpose:
                c.setFont("Helvetica", 5)
                c.drawCentredString(hx, hy - r - 8, hole.purpose)

    # ------------------------------------------------------------------
    # Splash bands (legacy — only used when no separate splash parts exist)
    # ------------------------------------------------------------------

    def _draw_splash_bands(
        self, c: rl_canvas.Canvas,
        part: Part, x: float, y: float, pw: float, ph: float, scale: float,
    ):
        """
        Draw thin annotation bands for splash sub-objects attached to a Part.
        Only called when no separate splash Part objects exist in the assembly.
        """
        for sp in part.splashes:
            stype = sp.splash_type.value.lower()
            sw = sp.dimensions.length * scale
            sd = sp.dimensions.depth * scale

            c.setFillColor(_C_SPLASH_FILL)
            c.setStrokeColor(_C_SPLASH_STR)
            c.setLineWidth(1.0)
            c.setDash(1, 0)

            if "back" in stype:
                bw = min(sw, pw)
                bh = min(sd, _SPLASH_W)
                c.rect(x, y + ph, bw, bh, fill=1, stroke=1)
                c.setFillColor(_C_SPLASH_STR)
                c.setFont("Helvetica", 5)
                if bw > 20:
                    c.drawCentredString(x + bw / 2, y + ph + bh / 2 - 2,
                                        f'BSP {sp.dimensions.depth}"')

            elif "left" in stype:
                bw = min(sd, _SPLASH_W)
                bh = min(sw, ph)
                c.rect(x - bw, y, bw, bh, fill=1, stroke=1)
                c.setFillColor(_C_SPLASH_STR)
                c.setFont("Helvetica", 5)
                if bh > 14:
                    c.drawCentredString(x - bw / 2, y + bh / 2, "L-SP")

            elif "right" in stype:
                bw = min(sd, _SPLASH_W)
                bh = min(sw, ph)
                c.rect(x + pw, y, bw, bh, fill=1, stroke=1)
                c.setFillColor(_C_SPLASH_STR)
                c.setFont("Helvetica", 5)
                if bh > 14:
                    c.drawCentredString(x + pw + bw / 2, y + bh / 2, "R-SP")

    # ------------------------------------------------------------------
    # Grain arrow
    # ------------------------------------------------------------------

    def _draw_grain_arrow(
        self, c: rl_canvas.Canvas,
        cx: float, cy: float, span: float, horizontal: bool = True,
    ):
        half = min(span * 0.35, 36.0)
        c.setStrokeColor(HexColor("#2c3e50"))
        c.setLineWidth(1.0)
        c.setDash(1, 0)
        c.setFillColor(HexColor("#2c3e50"))
        if horizontal:
            x1, x2 = cx - half, cx + half
            c.line(x1, cy, x2, cy)
            for tip_x, dx in ((x1, 1), (x2, -1)):
                c.line(tip_x, cy, tip_x + dx * 5, cy + 3)
                c.line(tip_x, cy, tip_x + dx * 5, cy - 3)
        else:
            y1, y2 = cy - half, cy + half
            c.line(cx, y1, cx, y2)
            for tip_y, dy in ((y1, 1), (y2, -1)):
                c.line(cx, tip_y, cx + 3, tip_y + dy * 5)
                c.line(cx, tip_y, cx - 3, tip_y + dy * 5)

    # ------------------------------------------------------------------
    # Corner annotations
    # ------------------------------------------------------------------

    def _draw_corner_annotations(
        self, c: rl_canvas.Canvas,
        part: Part, x: float, y: float, pw: float, ph: float, ann: dict,
    ):
        c.setFillColor(_C_LABEL)
        c.setFont("Helvetica-Bold", 6)
        if ann.get("break_corners"):
            c.drawString(x + pw - 52, y + ph - 8, "Break Corners")
        for i, rlabel in enumerate(ann.get("radii", [])[:2]):
            ox = x + 4 + i * 28
            c.drawString(ox, y + 4, rlabel)

    # ------------------------------------------------------------------
    # Dimension callout lines
    # ------------------------------------------------------------------

    def _draw_dimensions(
        self, c: rl_canvas.Canvas,
        part: Part, x: float, y: float, pw: float, ph: float, scale: float,
        dim_style: str = DIM_INCH_MM,
    ):
        dims = part.dimensions
        c.setStrokeColor(_C_DIM)
        c.setLineWidth(0.75)
        c.setDash(1, 0)
        c.setFillColor(_C_DIM)

        # Width (horizontal, below part) — extension lines + dim line + text
        dim_y = y - _DIM_OFFSET
        c.line(x,      y, x,      dim_y)
        c.line(x + pw, y, x + pw, dim_y)
        self._dim_line_h(c, x, dim_y, pw)
        c.setFont("Helvetica", 7)
        c.drawCentredString(x + pw / 2, dim_y - _DIM_GAP, fmt_dim(dims.length, dim_style))

        # Depth (vertical, right of part)
        dim_x = x + pw + _DIM_OFFSET
        c.line(x + pw, y,      dim_x, y)
        c.line(x + pw, y + ph, dim_x, y + ph)
        self._dim_line_v(c, dim_x, y, ph)
        c.saveState()
        c.translate(dim_x + _DIM_GAP + 6, y + ph / 2)
        c.rotate(90)
        c.setFont("Helvetica", 7)
        c.drawCentredString(0, 0, fmt_dim(dims.depth, dim_style))
        c.restoreState()


    def _dim_line_h(self, c: rl_canvas.Canvas, x: float, y: float, length: float):
        """Horizontal dimension line with inward open arrowheads at both ends."""
        c.setLineWidth(0.75)
        c.line(x, y, x + length, y)
        self._arrowhead(c, x,          y, 'right')   # left end → points right
        self._arrowhead(c, x + length, y, 'left')    # right end → points left

    def _dim_line_v(self, c: rl_canvas.Canvas, x: float, y: float, height: float):
        """Vertical dimension line with inward open arrowheads at both ends."""
        c.setLineWidth(0.75)
        c.line(x, y, x, y + height)
        self._arrowhead(c, x, y,          'up')      # bottom end → points up
        self._arrowhead(c, x, y + height, 'down')    # top end → points down

    def _arrowhead(self, c: rl_canvas.Canvas, x: float, y: float, direction: str):
        """Open arrowhead (V shape), 6 pt long × 3 pt wide — CAD shop drawing style."""
        L, W = 6.0, 3.0
        c.setLineWidth(0.75)
        if direction == 'right':
            c.line(x, y, x - L, y + W)
            c.line(x, y, x - L, y - W)
        elif direction == 'left':
            c.line(x, y, x + L, y + W)
            c.line(x, y, x + L, y - W)
        elif direction == 'up':
            c.line(x, y, x - W, y - L)
            c.line(x, y, x + W, y - L)
        elif direction == 'down':
            c.line(x, y, x - W, y + L)
            c.line(x, y, x + W, y + L)

    # ------------------------------------------------------------------
    # Seam line
    # ------------------------------------------------------------------

    def _draw_seam(self, c: rl_canvas.Canvas, x: float, y1: float, y2: float):
        c.setStrokeColor(_C_SEAM)
        c.setLineWidth(1.5)
        c.setDash(5, 2)
        c.line(x, y1, x, y2)
        c.setDash(1, 0)

    # ------------------------------------------------------------------
    # L-shape support
    # ------------------------------------------------------------------

    def _detect_l_shape(self, parts: List[Part]) -> bool:
        """True if assembly contains return-leg parts (L or U shape)."""
        return any(
            p.part_type in (PartType.LEFT_RETURN, PartType.RIGHT_RETURN)
            for p in parts
        )

    def _draw_l_shape_indicator(
        self, c: rl_canvas.Canvas,
        parts: List[Part],
        positions: List[Tuple[float, float]],
        scale: float,
        zone_x: float,
        zone_y: float,
    ):
        """Draw a corner-angle annotation to make L-shape relationship obvious."""
        main_tops = [(p, pos) for p, pos in zip(parts, positions)
                     if p.part_type == PartType.MAIN_TOP]
        returns   = [(p, pos) for p, pos in zip(parts, positions)
                     if p.part_type in (PartType.LEFT_RETURN, PartType.RIGHT_RETURN)]

        if not main_tops or not returns:
            return

        # Draw an "L" indicator label near the corner junction
        mt_part, (mt_px, mt_py) = main_tops[0]
        rt_part, (rt_px, rt_py) = returns[0]

        # Corner x = where the return meets the main top
        corner_x = zone_x + mt_px + mt_part.dimensions.length * scale
        corner_y = zone_y + mt_py

        c.setStrokeColor(HexColor("#2c3e50"))
        c.setLineWidth(1.0)
        c.setDash(2, 2)
        # Small 90° angle marks
        arm = 10.0
        c.line(corner_x - arm, corner_y, corner_x, corner_y)
        c.line(corner_x, corner_y, corner_x, corner_y + arm)
        c.setDash(1, 0)

        c.setFillColor(HexColor("#2c3e50"))
        c.setFont("Helvetica-Bold", 6)
        c.drawString(corner_x + 2, corner_y + 2, "L-CORNER")

    # ------------------------------------------------------------------
    # Layout computation
    # ------------------------------------------------------------------

    def _compute_layout(
        self, parts: List[Part], zone_w: float, zone_h: float
    ) -> dict:
        """
        Standard single-row layout for assemblies without separate splash parts,
        OR for small assemblies (< 3 parts).

        Scale = min(width_scale, height_scale) — fits parts in both dimensions.
        """
        n = len(parts)
        total_raw_w = sum(p.dimensions.length for p in parts)
        max_raw_h   = max(p.dimensions.depth  for p in parts)

        dim_margin_w = _DIM_OFFSET + 20.0
        dim_margin_h = _DIM_OFFSET + 15.0

        avail_w = zone_w - dim_margin_w - _PART_GAP * max(n - 1, 0) - _SPLASH_W * 2
        avail_h = zone_h - dim_margin_h - _SPLASH_W * 2 - 30.0

        avail_w = max(avail_w, 20.0)
        avail_h = max(avail_h, 20.0)

        scale_w = avail_w / max(total_raw_w, 0.1)
        scale_h = avail_h / max(max_raw_h,   0.1)
        # Cap raised to 12 so single-piece assemblies (vanity, island) fill
        # the drawing zone better when width is not the constraining dimension.
        scale   = min(scale_w, scale_h, 12.0)
        scale   = max(scale, 0.5)

        positions = []
        cursor_x  = _SPLASH_W + 4.0

        # Vertically centre parts within the available height
        actual_h = max_raw_h * scale
        base_y   = dim_margin_h + _SPLASH_W + max(0, (avail_h - actual_h) / 2)

        for part in parts:
            positions.append((cursor_x, base_y))
            cursor_x += part.dimensions.length * scale + _PART_GAP

        total_height = base_y + max_raw_h * scale + _SPLASH_W + 30.0
        return {"scale": scale, "positions": positions, "total_height": total_height}

    def _compute_shop_sheet_layout(
        self, parts: List[Part], zone_w: float, zone_h: float
    ) -> dict:
        """
        Two-zone geometry-aware layout (Virgin Surfaces shop drawing style).

        Thin parts  (depth ≤ 5.5") → TOP zone   (backsplash / side splash pieces).
        Deep parts  (depth >  5.5") → BOTTOM zone (main countertop pieces).

        Horizontal alignment:
          Each splash piece is x-centred above the main top with the
          closest matching width.  Unmatched splashes are placed after
          all matched ones in the top zone.

        Scale:
          Uses min(w_scale, h_scale) computed from the main-top row,
          then verified against the splash row.  Both rows share the
          same scale so proportions are consistent.
        """
        splashes = [p for p in parts if _is_splash_part(p)]
        mains    = [p for p in parts if not _is_splash_part(p)]

        # Dimension / margin constants
        dim_margin_h = _DIM_OFFSET + 20.0   # below the bottom (main-top) row
        dim_margin_w = _DIM_OFFSET + 16.0   # right side of last part

        # ── 1. Compute scale from the main-top row ─────────────────────────
        if mains:
            n_mains      = len(mains)
            total_main_w = sum(p.dimensions.length for p in mains)
            max_main_h   = max(p.dimensions.depth  for p in mains)
            max_splash_h = max((p.dimensions.depth for p in splashes), default=0.0)

            avail_w = zone_w - dim_margin_w - _PART_GAP * max(n_mains - 1, 0) - _PART_GAP
            # Reserve height for both rows + gap + dim space.
            # max_splash_h is in inches; use a fixed 32pt budget for the splash
            # row height (it's thin — typically 4-6") so scale drives upward.
            avail_h = (zone_h
                       - dim_margin_h   # below main row (pts)
                       - _ROW_GAP       # gap between rows (pts)
                       - 32.0           # splash row budget (pts, ~4-5" at typical scale)
                       - 20.0)          # top pad (pts)

            avail_w = max(avail_w, 20.0)
            avail_h = max(avail_h, 20.0)

            scale_w = avail_w / max(total_main_w, 0.1)
            scale_h = avail_h / max(max_main_h, 0.1)
            scale   = min(scale_w, scale_h, 12.0)
            scale   = max(scale, 0.5)
        else:
            # All parts are splash pieces — just lay them out normally
            return self._compute_layout(parts, zone_w, zone_h)

        # ── 2. Position main tops in the BOTTOM zone ───────────────────────
        main_base_y = dim_margin_h + 8.0
        main_pos_map: dict = {}        # id(part) → (x, y)
        cursor_x = _PART_GAP
        for part in mains:
            main_pos_map[id(part)] = (cursor_x, main_base_y)
            cursor_x += part.dimensions.length * scale + _PART_GAP

        # ── 3. Position splash pieces in the TOP zone ──────────────────────
        max_main_h_pts  = max(p.dimensions.depth for p in mains) * scale
        splash_base_y   = main_base_y + max_main_h_pts + _ROW_GAP

        # Match each splash to the main top with closest width (greedy).
        remaining_mains = list(mains)
        matched_pairs: list = []   # [(splash, main_or_None)]
        unmatched_splashes: list = []

        for sp in splashes:
            if not remaining_mains:
                unmatched_splashes.append(sp)
                continue

            best = min(remaining_mains,
                       key=lambda m: abs(m.dimensions.length - sp.dimensions.length))
            diff = abs(best.dimensions.length - sp.dimensions.length)
            # Accept match if within 50 % of the splash width
            if diff <= sp.dimensions.length * 0.5:
                matched_pairs.append((sp, best))
                remaining_mains.remove(best)
            else:
                unmatched_splashes.append(sp)

        splash_pos_map: dict = {}    # id(part) → (x, y)

        for sp, main in matched_pairs:
            mx, _  = main_pos_map[id(main)]
            mpw    = main.dimensions.length * scale
            spw    = sp.dimensions.length * scale
            # Centre splash above its matching main top
            sx     = mx + (mpw - spw) / 2
            splash_pos_map[id(sp)] = (sx, splash_base_y)

        # Unmatched splashes: place to the right of all matched splashes
        if unmatched_splashes:
            occupied_rights = [
                splash_pos_map[id(sp)][0] + sp.dimensions.length * scale
                for sp, _ in matched_pairs
                if id(sp) in splash_pos_map
            ]
            ux = (max(occupied_rights) + _PART_GAP * 2) if occupied_rights else _PART_GAP
            for sp in unmatched_splashes:
                splash_pos_map[id(sp)] = (ux, splash_base_y)
                ux += sp.dimensions.length * scale + _PART_GAP

        # ── 4. Assemble positions list in original parts order ─────────────
        positions = []
        for part in parts:
            pos = main_pos_map.get(id(part)) or splash_pos_map.get(id(part))
            positions.append(pos or (_PART_GAP, main_base_y))

        max_splash_h_pts = (
            max(p.dimensions.depth for p in splashes) * scale if splashes else 0.0
        )
        total_height = splash_base_y + max_splash_h_pts + 24.0

        return {
            "scale":        scale,
            "positions":    positions,
            "total_height": total_height,
        }

    def _mirror_positions(
        self,
        positions: List[Tuple[float, float]],
        parts: List[Part],
        scale: float,
        zone_w: float,
    ) -> List[Tuple[float, float]]:
        """Flip X coordinates for MIR assemblies."""
        mirrored = []
        for (px, py), part in zip(positions, parts):
            pw = part.dimensions.length * scale
            mirrored.append((zone_w - px - pw, py))
        combined = sorted(zip(mirrored, parts), key=lambda item: item[0][0])
        return [pos for pos, _ in combined]

    # ------------------------------------------------------------------
    # Fallback
    # ------------------------------------------------------------------

    def _draw_no_parts_message(
        self, c: rl_canvas.Canvas,
        x: float, y: float, w: float, h: float,
    ):
        c.setFillColor(HexColor("#eeeeee"))
        c.rect(x, y, w, h, fill=1, stroke=0)
        c.setFillColor(HexColor("#888888"))
        c.setFont("Helvetica", 10)
        c.drawCentredString(x + w / 2, y + h / 2,
                            "No parts defined for this assembly.")
