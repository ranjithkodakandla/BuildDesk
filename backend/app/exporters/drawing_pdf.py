"""
generate_drawing_pdf — Industry-standard fabrication shop drawing PDF.

Verified against Virgin Surfaces reference PDFs:
  Concord North, Haven On Main, Deforest Yards, Bulls Outdoor, Saltwell Springs

Layout: A4 landscape (841.89 × 595.28 pts)
  Left  (x 0–580):   Drawing canvas — parts, splashes, dimensions, edge codes
  Right (x 580–842): Title block — 11 sections

Key rendering rules from reference PDFs:
  - Backsplash = separate rectangle ABOVE the main part (not a hatch overlay)
  - Side splash = separate rectangle to LEFT or RIGHT of main part
  - All splash pieces: X on 3 exposed edges, no code on wall edge
  - Dimension format: "55 in [1397 mm]" — strip trailing zeros
  - Sink cutout: dashed rectangle, model number centred inside
  - Faucet: small circle with crosshair + diameter label
  - Corner radius: "R.5 in [R13 mm]" diagonal out from each corner
  - Edge codes drawn ON the edge line, white background box
"""

from __future__ import annotations

import io
import math
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas as rl_canvas

PAGE_W, PAGE_H = landscape(A4)   # 841.89 × 595.28 pts

# ── Line weight constants ────────────────────────────────────────────────────
LW_SHAPE  = 1.5
LW_DIM    = 0.5
LW_DASH   = 0.75
LW_BORDER = 0.75
LW_HATCH  = 0.3

DASH_CUTOUT = [3, 2]
DASH_SEAM   = [4, 2]

# ── Edge codes ───────────────────────────────────────────────────────────────
EDGE_CODES: Dict[str, str] = {
    "eased":              "X",
    "polished":           "X",
    "bullnose":           "B",
    "laminated_bullnose": "LB",
    "laminated_eased":    "LE",
    "flat":               "F",
    "raw":                "RAW",
    "seam":               "S",
    "miter":              "M",
}

# ── Zone constants ───────────────────────────────────────────────────────────
DIVIDER_X   = 580.0
TB_X        = 580.0
TB_W        = PAGE_W - TB_X          # ~261.89 pts
TB_TXT_X    = TB_X + 6.0

CANVAS_LEFT   = 15.0
CANVAS_RIGHT  = 565.0
CANVAS_BOTTOM = 15.0
CANVAS_TOP    = PAGE_H - 60.0
CANVAS_W      = CANVAS_RIGHT - CANVAS_LEFT   # 550 pts
CANVAS_H      = CANVAS_TOP   - CANVAS_BOTTOM # ~520 pts

DIM_OFFSET = 22.0   # pts gap: part edge → dim line
DIM_GAP    = 7.0    # pts: dim line → text
TICK_LEN   = 4.0    # pts half-tick
PART_GAP   = 8.0    # pts between adjacent parts when seamed


# ════════════════════════════════════════════════════════════════════════════
# Dimension formatters — match reference PDF exactly
# ════════════════════════════════════════════════════════════════════════════

def fmt_dim(inches: float) -> str:
    """
    "55 in [1397 mm]" — whole numbers show no decimal.
    "22.5 in [572 mm]" — strip trailing zeros.
    "54.875 in [1394 mm]" — keep needed decimals.
    """
    mm = round(inches * 25.4)
    # Format with up to 3 decimal places, strip trailing zeros
    val = f"{inches:.3f}".rstrip("0").rstrip(".")
    return f"{val} in [{mm} mm]"


def fmt_hole(inches: float) -> str:
    """Ø1.5 in [Ø38 mm]"""
    mm = round(inches * 25.4)
    val = f"{inches:.3f}".rstrip("0").rstrip(".")
    return f"Ø{val} in [Ø{mm} mm]"


def fmt_radius(inches: float) -> str:
    """R.5 in [R13 mm]"""
    mm = round(inches * 25.4)
    val = f"{inches:.3f}".rstrip("0").rstrip(".")
    # Drop leading zero for sub-1" radii: ".5" not "0.5"
    val = val.lstrip("0") or "0"
    return f"R{val} in [R{mm} mm]"


def fmt_date(raw: Any) -> str:
    if not raw:
        return ""
    try:
        if isinstance(raw, str):
            dt = datetime.fromisoformat(raw.replace("Z", ""))
            return f"{dt.month}-{dt.day}-{str(dt.year)[2:]}"
        return str(raw)
    except Exception:
        return str(raw)


# ════════════════════════════════════════════════════════════════════════════
# Layout helpers
# ════════════════════════════════════════════════════════════════════════════

def _best_scale(parts: List[dict], splashes_per_part: List[List[dict]],
                canvas_w: float, canvas_h: float) -> float:
    """
    Compute pts-per-inch scale so the whole composition fits in the canvas
    at ~72% fill, leaving room for dimension lines.
    """
    if not parts:
        return 1.0

    # Total layout width = sum of part widths (parts touch at seams)
    total_w = sum(p["width"] for p in parts)

    # Maximum height = tallest part + tallest backsplash above it
    max_h = 0.0
    for i, p in enumerate(parts):
        part_h = p["depth"]
        # Add backsplash height above this part
        bs_h = max(
            (sp["height"] for sp in splashes_per_part[i] if sp.get("side") == "back"),
            default=0.0,
        )
        # Add left/right splash width beside this part
        ss_w = sum(
            sp["height"] for sp in splashes_per_part[i]
            if sp.get("side") in ("left", "right")
        )
        part_h = p["depth"] + bs_h
        max_h = max(max_h, part_h)
        total_w = total_w + ss_w  # side splashes add to horizontal footprint

    dim_margin_w = DIM_OFFSET * 2 + 30
    dim_margin_h = DIM_OFFSET * 2 + 30
    avail_w = (canvas_w - dim_margin_w) * 0.72
    avail_h = (canvas_h - dim_margin_h) * 0.72

    sw = avail_w / max(total_w, 0.001)
    sh = avail_h / max(max_h, 0.001)
    return max(min(sw, sh), 0.5)


def _compute_positions(parts: List[dict], splashes_per_part: List[List[dict]],
                       scale: float, canvas_w: float, canvas_h: float
                       ) -> List[Tuple[float, float]]:
    """
    Return (px, py) in canvas-local coordinates for each MAIN PART.
    All parts align on their bottom edge. Left-to-right, no gaps (seamed).
    """
    n = len(parts)
    if n == 0:
        return []

    # Total horizontal span (including side splashes beside outermost parts)
    left_ss_w  = max(
        (sp["height"] for sp in splashes_per_part[0] if sp.get("side") == "left"),
        default=0.0,
    ) * scale
    right_ss_w = max(
        (sp["height"] for sp in splashes_per_part[-1] if sp.get("side") == "right"),
        default=0.0,
    ) * scale

    total_parts_w = sum(p["width"] * scale for p in parts)
    total_draw_w  = left_ss_w + total_parts_w + right_ss_w

    # Max height block = tallest part + its backsplash
    max_h_pts = 0.0
    for i, p in enumerate(parts):
        bs_h = max(
            (sp["height"] for sp in splashes_per_part[i] if sp.get("side") == "back"),
            default=0.0,
        ) * scale
        max_h_pts = max(max_h_pts, p["depth"] * scale + bs_h)

    # Centre the entire composition in the canvas
    start_x = CANVAS_LEFT + (canvas_w - total_draw_w) / 2 + left_ss_w
    base_y   = CANVAS_BOTTOM + (canvas_h - max_h_pts) / 2

    positions = []
    cx = start_x
    for p in parts:
        positions.append((cx, base_y))
        cx += p["width"] * scale

    return positions


# ════════════════════════════════════════════════════════════════════════════
# Main entry point
# ════════════════════════════════════════════════════════════════════════════

def generate_drawing_pdf(drawing: dict, project: dict) -> bytes:
    """
    Returns one A4-landscape PDF page as bytes.
    ONE page per drawing regardless of unit count.
    """
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=(PAGE_W, PAGE_H))
    _draw_page(c, drawing, project)
    c.showPage()
    c.save()
    return buf.getvalue()


# ════════════════════════════════════════════════════════════════════════════
# Page skeleton
# ════════════════════════════════════════════════════════════════════════════

def _draw_page(c: rl_canvas.Canvas, drawing: dict, project: dict):
    _set_bw(c)
    # Vertical divider
    c.setLineWidth(LW_BORDER)
    c.line(DIVIDER_X, 0, DIVIDER_X, PAGE_H)
    _draw_left_zone(c, drawing, project)
    _draw_right_zone(c, drawing, project)


def _set_bw(c: rl_canvas.Canvas):
    c.setStrokeColorRGB(0, 0, 0)
    c.setFillColorRGB(0, 0, 0)
    c.setDash(1, 0)


# ════════════════════════════════════════════════════════════════════════════
# LEFT ZONE
# ════════════════════════════════════════════════════════════════════════════

def _draw_left_zone(c: rl_canvas.Canvas, drawing: dict, project: dict):
    _draw_edge_legend_strip(c, project)
    _draw_parts_composition(c, drawing)
    _draw_unit_distribution_table(c, project)


# ── A. Edge legend strip (top 45 pts) ────────────────────────────────────────

def _draw_edge_legend_strip(c: rl_canvas.Canvas, project: dict):
    strip_bottom = PAGE_H - 55
    c.setLineWidth(0.5)
    c.setStrokeColorRGB(0, 0, 0)
    c.line(0, strip_bottom, DIVIDER_X, strip_bottom)

    thickness = project.get("thickness", "3CM")

    # Left side: edge detail label
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 7)
    c.drawString(15, PAGE_H - 18, "X = Edge & Sink Detail (Eased)")
    c.drawString(15, PAGE_H - 29, "X = Splash Detail (Eased)")

    # Right side: thickness note
    c.setFont("Helvetica", 7)
    x2 = 290
    if thickness == "2CM":
        c.drawString(x2, PAGE_H - 18, '2 CM = 3/4"   1/8" Radius')
    elif thickness == "3CM":
        c.drawString(x2, PAGE_H - 18, '3 CM = 1-1/4"   1/8" Radius')
    else:  # 2CM & 3CM
        c.drawString(x2, PAGE_H - 18, '3 CM = 1-1/4"   1/8" Radius')
        c.drawString(x2, PAGE_H - 29, '2 CM = 3/4"   1/8" Radius')


# ── B. Parts composition (main top + splashes) ───────────────────────────────

def _draw_parts_composition(c: rl_canvas.Canvas, drawing: dict):
    parts = drawing.get("parts", [])
    if not parts:
        c.setFont("Helvetica", 9)
        c.setFillColorRGB(0.6, 0.6, 0.6)
        c.drawCentredString(CANVAS_LEFT + CANVAS_W / 2, CANVAS_BOTTOM + CANVAS_H / 2,
                            "No parts defined")
        return

    # Group splashes per part
    splashes_per_part: List[List[dict]] = [
        list(p.get("splashes", [])) for p in parts
    ]

    scale = _best_scale(parts, splashes_per_part, CANVAS_W, CANVAS_H)
    positions = _compute_positions(parts, splashes_per_part, scale, CANVAS_W, CANVAS_H)

    for i, (part, (px, py)) in enumerate(zip(parts, positions)):
        pw = part["width"]  * scale
        ph = part["depth"]  * scale
        label = part.get("label", chr(65 + i))
        sps   = splashes_per_part[i]

        # 1. Draw backsplash ABOVE (separate rectangle, drawn first so main top overlaps border)
        for sp in sps:
            if sp.get("side") == "back":
                _draw_splash_piece(c, "back", sp, px, py, pw, ph, scale)

        # 2. Draw side splashes (left/right)
        for sp in sps:
            side = sp.get("side", "")
            if side in ("left", "right"):
                _draw_splash_piece(c, side, sp, px, py, pw, ph, scale)

        # 3. Draw main top rectangle
        _draw_part_rect(c, px, py, pw, ph, label)

        # 4. Edge codes on main top
        _draw_edge_codes_on_part(c, part, px, py, pw, ph)

        # 5. Dimension lines
        _draw_dimension_lines(c, part, px, py, pw, ph, scale, i, len(parts))

        # 6. Cutouts (sink)
        _draw_cutouts(c, part, px, py, pw, ph, scale)

        # 7. Faucet holes
        _draw_holes(c, part, px, py, pw, ph, scale)

        # 8. Corner radius labels
        _draw_corner_radius(c, part, px, py, pw, ph)

    # 9. Seam lines between adjacent main tops
    _draw_seams(c, parts, positions, scale)


def _draw_part_rect(c: rl_canvas.Canvas, px, py, pw, ph, label: str):
    _set_bw(c)
    c.setLineWidth(LW_SHAPE)
    c.setFillColorRGB(1, 1, 1)
    c.rect(px, py, pw, ph, stroke=1, fill=1)

    # "Polish" label centred inside (matches reference — large light grey text)
    fs = min(14.0, ph * 0.35, pw * 0.25)
    fs = max(fs, 7.0)
    c.setFillColorRGB(0.55, 0.55, 0.55)
    c.setFont("Helvetica", fs)
    c.drawCentredString(px + pw / 2, py + ph / 2 - fs * 0.35, "Polish")

    # Small part label (A, B, C) in corner
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(px + 3, py + 3, label)


# ── Splash piece — drawn as a CLEAN RECTANGLE (not hatched) ─────────────────

def _draw_splash_piece(c: rl_canvas.Canvas, side: str, sp: dict,
                       px, py, pw, ph, scale):
    sh = sp["height"] * scale  # the short dimension (height of splash piece)
    sl = sp.get("length", 0)

    if side == "back":
        # Backsplash: above the main top, same width as main top
        bw = (sl if sl else sp.get("width", 0)) * scale or pw
        bh = sh
        bx, by = px, py + ph

        _set_bw(c)
        c.setLineWidth(LW_SHAPE)
        c.setFillColorRGB(1, 1, 1)
        c.rect(bx, by, bw, bh, stroke=1, fill=1)

        # Edge codes: X on top, left, right; nothing on bottom (wall)
        _draw_x_on_edge(c, bx + bw / 2, by + bh, 0)    # top
        _draw_x_on_edge(c, bx, by + bh / 2, 90)         # left
        _draw_x_on_edge(c, bx + bw, by + bh / 2, 90)    # right

        # Splash dimension label (height)
        c.setFont("Helvetica", 6)
        c.setFillColorRGB(0, 0, 0)
        dim_str = fmt_dim(sp["height"])
        # Dimension line on right side of backsplash
        dim_x = bx + bw + DIM_OFFSET
        c.setLineWidth(LW_DIM)
        c.line(bx + bw, by,      dim_x, by)
        c.line(bx + bw, by + bh, dim_x, by + bh)
        c.line(dim_x, by, dim_x, by + bh)
        c.line(dim_x - TICK_LEN, by,      dim_x + TICK_LEN, by)
        c.line(dim_x - TICK_LEN, by + bh, dim_x + TICK_LEN, by + bh)
        c.saveState()
        c.translate(dim_x + DIM_GAP + 4, by + bh / 2)
        c.rotate(90)
        c.drawCentredString(0, 0, dim_str)
        c.restoreState()

    elif side == "left":
        # Left side splash: to the left of the main top
        ss_w = sh   # splash width on page = splash height in inches × scale
        ss_h = (sl if sl else sp.get("length", 0)) * scale or ph
        bx, by = px - ss_w, py

        _set_bw(c)
        c.setLineWidth(LW_SHAPE)
        c.setFillColorRGB(1, 1, 1)
        c.rect(bx, by, ss_w, ss_h, stroke=1, fill=1)

        # Edge codes: X on top, bottom, left; nothing on right (wall)
        _draw_x_on_edge(c, bx + ss_w / 2, by + ss_h, 0)   # top
        _draw_x_on_edge(c, bx + ss_w / 2, by, 0)           # bottom
        _draw_x_on_edge(c, bx, by + ss_h / 2, 90)          # left

        # Height dimension on left
        dim_x = bx - DIM_OFFSET
        c.setLineWidth(LW_DIM)
        c.line(bx, by,       dim_x, by)
        c.line(bx, by + ss_h, dim_x, by + ss_h)
        c.line(dim_x, by, dim_x, by + ss_h)
        c.line(dim_x - TICK_LEN, by,       dim_x + TICK_LEN, by)
        c.line(dim_x - TICK_LEN, by + ss_h, dim_x + TICK_LEN, by + ss_h)
        c.saveState()
        c.translate(dim_x - DIM_GAP - 4, by + ss_h / 2)
        c.rotate(90)
        c.setFont("Helvetica", 6)
        c.drawCentredString(0, 0, fmt_dim(sp.get("length", sp.get("height", 0))))
        c.restoreState()
        # Width dim above
        dim_y2 = by + ss_h + DIM_OFFSET
        c.line(bx,        by + ss_h, bx,        dim_y2)
        c.line(bx + ss_w, by + ss_h, bx + ss_w, dim_y2)
        c.line(bx, dim_y2, bx + ss_w, dim_y2)
        c.line(bx, dim_y2 - TICK_LEN, bx, dim_y2 + TICK_LEN)
        c.line(bx + ss_w, dim_y2 - TICK_LEN, bx + ss_w, dim_y2 + TICK_LEN)
        c.setFont("Helvetica", 6)
        c.drawCentredString(bx + ss_w / 2, dim_y2 + DIM_GAP, fmt_dim(sp["height"]))

    else:  # right
        ss_w = sh
        ss_h = (sl if sl else sp.get("length", 0)) * scale or ph
        bx, by = px + pw, py

        _set_bw(c)
        c.setLineWidth(LW_SHAPE)
        c.setFillColorRGB(1, 1, 1)
        c.rect(bx, by, ss_w, ss_h, stroke=1, fill=1)

        # Edge codes: X on top, bottom, right; nothing on left (wall)
        _draw_x_on_edge(c, bx + ss_w / 2, by + ss_h, 0)   # top
        _draw_x_on_edge(c, bx + ss_w / 2, by, 0)           # bottom
        _draw_x_on_edge(c, bx + ss_w, by + ss_h / 2, 90)   # right

        # Height dimension on right
        dim_x = bx + ss_w + DIM_OFFSET
        c.setLineWidth(LW_DIM)
        c.line(bx + ss_w, by,        dim_x, by)
        c.line(bx + ss_w, by + ss_h, dim_x, by + ss_h)
        c.line(dim_x, by, dim_x, by + ss_h)
        c.line(dim_x - TICK_LEN, by,        dim_x + TICK_LEN, by)
        c.line(dim_x - TICK_LEN, by + ss_h, dim_x + TICK_LEN, by + ss_h)
        c.saveState()
        c.translate(dim_x + DIM_GAP + 4, by + ss_h / 2)
        c.rotate(90)
        c.setFont("Helvetica", 6)
        c.drawCentredString(0, 0, fmt_dim(sp.get("length", sp.get("height", 0))))
        c.restoreState()
        # Width dim above
        dim_y2 = by + ss_h + DIM_OFFSET
        c.line(bx,        by + ss_h, bx,        dim_y2)
        c.line(bx + ss_w, by + ss_h, bx + ss_w, dim_y2)
        c.line(bx, dim_y2, bx + ss_w, dim_y2)
        c.line(bx, dim_y2 - TICK_LEN, bx, dim_y2 + TICK_LEN)
        c.line(bx + ss_w, dim_y2 - TICK_LEN, bx + ss_w, dim_y2 + TICK_LEN)
        c.setFont("Helvetica", 6)
        c.drawCentredString(bx + ss_w / 2, dim_y2 + DIM_GAP, fmt_dim(sp["height"]))


def _draw_x_on_edge(c: rl_canvas.Canvas, tx: float, ty: float, angle: float):
    """Draw an X code directly on an edge line with white background."""
    c.setFont("Helvetica-Bold", 7)
    tw = c.stringWidth("X", "Helvetica-Bold", 7) + 4
    bh = 9.0
    c.setFillColorRGB(1, 1, 1)
    c.setLineWidth(0)
    c.rect(tx - tw / 2, ty - bh / 2, tw, bh, stroke=0, fill=1)
    c.setFillColorRGB(0, 0, 0)
    c.drawCentredString(tx, ty - 2.5, "X")


# ── Edge codes for main top ───────────────────────────────────────────────────

def _draw_edge_codes_on_part(c: rl_canvas.Canvas, part: dict,
                              px, py, pw, ph):
    edges = part.get("edges", {})
    sides = [
        ("front", px + pw / 2, py,       0),
        ("back",  px + pw / 2, py + ph,  0),
        ("left",  px,          py + ph / 2, 90),
        ("right", px + pw,     py + ph / 2, 90),
    ]
    for edge_key, tx, ty, angle in sides:
        etype = edges.get(edge_key, "eased")
        code  = EDGE_CODES.get(etype, "X")
        if code == "RAW":
            continue  # raw/wall edges get no code marker on the drawing
        _draw_edge_code_label(c, code, tx, ty)


def _draw_edge_code_label(c: rl_canvas.Canvas, code: str, tx: float, ty: float):
    c.setFont("Helvetica-Bold", 7)
    tw = c.stringWidth(code, "Helvetica-Bold", 7) + 4
    bh = 9.0
    c.setFillColorRGB(1, 1, 1)
    c.setLineWidth(0)
    c.rect(tx - tw / 2, ty - bh / 2, tw, bh, stroke=0, fill=1)
    c.setFillColorRGB(0, 0, 0)
    c.drawCentredString(tx, ty - 2.5, code)


# ── Dimension lines ───────────────────────────────────────────────────────────

def _draw_dimension_lines(c: rl_canvas.Canvas, part: dict,
                           px, py, pw, ph, scale, part_idx: int, n_parts: int):
    _set_bw(c)
    c.setLineWidth(LW_DIM)
    c.setFont("Helvetica", 6)

    # Width — below part
    dim_y = py - DIM_OFFSET
    c.line(px,      py, px,      dim_y)
    c.line(px + pw, py, px + pw, dim_y)
    c.line(px, dim_y, px + pw, dim_y)
    c.line(px,      dim_y - TICK_LEN, px,      dim_y + TICK_LEN)
    c.line(px + pw, dim_y - TICK_LEN, px + pw, dim_y + TICK_LEN)
    c.setFillColorRGB(0, 0, 0)
    c.drawCentredString(px + pw / 2, dim_y - DIM_GAP - 6, fmt_dim(part["width"]))

    # Depth — right of last part only (avoids overlap)
    if part_idx == n_parts - 1:
        dim_x = px + pw + DIM_OFFSET
        c.line(px + pw, py,      dim_x, py)
        c.line(px + pw, py + ph, dim_x, py + ph)
        c.line(dim_x, py, dim_x, py + ph)
        c.line(dim_x - TICK_LEN, py,      dim_x + TICK_LEN, py)
        c.line(dim_x - TICK_LEN, py + ph, dim_x + TICK_LEN, py + ph)
        c.saveState()
        c.translate(dim_x + DIM_GAP + 6, py + ph / 2)
        c.rotate(90)
        c.drawCentredString(0, 0, fmt_dim(part["depth"]))
        c.restoreState()


# ── Corner radius ─────────────────────────────────────────────────────────────

def _draw_corner_radius(c: rl_canvas.Canvas, part: dict, px, py, pw, ph):
    r = part.get("cornerRadius", 0)
    if not r:
        return
    label = fmt_radius(r)
    c.setFont("Helvetica", 6)
    c.setFillColorRGB(0, 0, 0)
    off = 12.0
    corners = [
        (px - off, py - off),
        (px + pw + off, py - off),
    ]
    for cx2, cy2 in corners:
        c.drawCentredString(cx2, cy2, label)


# ── Cutouts (sink) ────────────────────────────────────────────────────────────

def _draw_cutouts(c: rl_canvas.Canvas, part: dict, px, py, pw, ph, scale):
    for co in part.get("cutouts", []):
        cw = co["width"]  * scale
        ch = co["height"] * scale
        cx = px + co.get("xOffset", (part["width"] - co["width"]) / 2) * scale
        cy = py + co.get("yOffset", (part["depth"] - co["height"]) / 2) * scale

        # Dashed rectangle
        _set_bw(c)
        c.setLineWidth(LW_DASH)
        c.setDash(*DASH_CUTOUT)
        c.setFillColorRGB(1, 1, 1)
        c.rect(cx, cy, cw, ch, stroke=1, fill=1)
        c.setDash(1, 0)

        # Model number inside the cutout
        model = co.get("modelNumber", "")
        sink_label = co.get("sinkType", "").replace("_", " ").title()
        c.setFont("Helvetica", 6)
        c.setFillColorRGB(0, 0, 0)
        if model and ch > 12:
            c.drawCentredString(cx + cw / 2, cy + ch / 2 + 2, model)
        if sink_label and ch > 20:
            c.setFont("Helvetica", 5)
            c.drawCentredString(cx + cw / 2, cy + ch / 2 - 8, sink_label)

        # Offset dimensions: distance from left edge to cutout center
        center_x_in = co.get("xOffset", (part["width"] - co["width"]) / 2) + co["width"] / 2
        center_from_right = part["width"] - center_x_in
        # From left
        dim_y_off = py - DIM_OFFSET * 2 - 4
        mid_cx = px + center_x_in * scale
        c.setLineWidth(LW_DIM)
        c.setFont("Helvetica", 5.5)
        c.line(px, dim_y_off, mid_cx, dim_y_off)
        c.line(px,    dim_y_off - TICK_LEN, px,    dim_y_off + TICK_LEN)
        c.line(mid_cx, dim_y_off - TICK_LEN, mid_cx, dim_y_off + TICK_LEN)
        c.drawCentredString((px + mid_cx) / 2, dim_y_off - DIM_GAP - 3,
                            fmt_dim(center_x_in))
        # From right
        c.line(mid_cx, dim_y_off, px + pw, dim_y_off)
        c.line(px + pw, dim_y_off - TICK_LEN, px + pw, dim_y_off + TICK_LEN)
        c.drawCentredString((mid_cx + px + pw) / 2, dim_y_off - DIM_GAP - 3,
                            fmt_dim(center_from_right))


# ── Faucet holes ──────────────────────────────────────────────────────────────

def _draw_holes(c: rl_canvas.Canvas, part: dict, px, py, pw, ph, scale):
    for h in part.get("holes", []):
        hx = px + h["x"] * scale
        hy = py + h["y"] * scale
        r  = 4.0

        _set_bw(c)
        c.setLineWidth(1.0)
        c.setFillColorRGB(1, 1, 1)
        c.circle(hx, hy, r, stroke=1, fill=1)

        # Crosshair inside circle
        c.setLineWidth(0.5)
        c.line(hx - r * 0.7, hy, hx + r * 0.7, hy)
        c.line(hx, hy - r * 0.7, hx, hy + r * 0.7)

        # Label to the right
        diam = h.get("diameter", 1.5)
        c.setFont("Helvetica", 6)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(hx + r + 3, hy - 2, fmt_hole(diam))

        # Offset dimension from back edge
        from_back = part["depth"] - h["y"]
        dim_x2 = px - DIM_OFFSET
        c.setLineWidth(LW_DIM)
        c.line(px, hy, dim_x2, hy)
        c.line(px, py + ph, dim_x2, py + ph)
        c.line(dim_x2, hy, dim_x2, py + ph)
        c.setFont("Helvetica", 5)
        c.saveState()
        c.translate(dim_x2 - 4, (hy + py + ph) / 2)
        c.rotate(90)
        c.drawCentredString(0, 0, fmt_dim(from_back))
        c.restoreState()


# ── Seam lines ────────────────────────────────────────────────────────────────

def _draw_seams(c: rl_canvas.Canvas, parts, positions, scale):
    if len(positions) < 2:
        return
    _set_bw(c)
    c.setLineWidth(LW_DASH)
    c.setDash(*DASH_SEAM)
    for i in range(len(positions) - 1):
        px1, py1 = positions[i]
        pw1 = parts[i]["width"] * scale
        ph1 = parts[i]["depth"] * scale
        seam_x = px1 + pw1
        c.line(seam_x, py1, seam_x, py1 + ph1)
        _draw_edge_code_label(c, "S", seam_x, py1 + ph1 / 2)
    c.setDash(1, 0)


# ── C. Unit distribution table (bottom-left) ─────────────────────────────────

def _draw_unit_distribution_table(c: rl_canvas.Canvas, project: dict):
    unit_grid = project.get("unitGrid")
    if not unit_grid:
        return

    buildings = unit_grid.get("buildings", [])
    floors    = unit_grid.get("floors",    [])
    cells     = unit_grid.get("cells",     {})

    if not buildings or not floors:
        return

    # Table position: bottom-right of drawing area
    col_floor_w = 32.0
    col_bld_w   = 36.0
    col_tot_w   = 34.0
    row_h       = 12.0
    n_rows      = len(floors) + 2  # header + data rows + total
    table_h     = n_rows * row_h
    table_w     = col_floor_w + col_bld_w * len(buildings) + col_tot_w

    # Anchor: right-align to drawing canvas bottom-right area
    x = CANVAS_RIGHT - table_w - DIM_OFFSET
    y_top = CANVAS_BOTTOM + table_h + 10

    def _cell(cx, cy, cw, ch, text, bold=False, grey=False, fontsize=6):
        c.setLineWidth(0.5)
        c.setStrokeColorRGB(0, 0, 0)
        if grey:
            c.setFillColorRGB(0.88, 0.88, 0.88)
        else:
            c.setFillColorRGB(1, 1, 1)
        c.rect(cx, cy - ch, cw, ch, stroke=1, fill=1)
        c.setFillColorRGB(0, 0, 0)
        fn = "Helvetica-Bold" if bold else "Helvetica"
        c.setFont(fn, fontsize)
        c.drawCentredString(cx + cw / 2, cy - ch + 3, text)

    cur_y = y_top

    # Header: "Bldg #'s" spanning building columns
    bldg_span_w = col_bld_w * len(buildings)
    c.setLineWidth(0.5)
    c.setFillColorRGB(0.88, 0.88, 0.88)
    c.rect(x + col_floor_w, cur_y - row_h * 0.6, bldg_span_w, row_h * 0.6, stroke=1, fill=1)
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 5.5)
    c.drawCentredString(x + col_floor_w + bldg_span_w / 2,
                        cur_y - row_h * 0.6 + 2, "Bldg #'s")
    cur_y -= row_h * 0.6

    # Column headers
    _cell(x, cur_y, col_floor_w, row_h, "Floor", bold=True, grey=True)
    cx2 = x + col_floor_w
    for b in buildings:
        _cell(cx2, cur_y, col_bld_w, row_h, str(b), bold=True, grey=True)
        cx2 += col_bld_w
    _cell(cx2, cur_y, col_tot_w, row_h, "Total", bold=True, grey=True)
    cur_y -= row_h

    # Data rows — show unit numbers stacked in each cell
    for fl in sorted(floors):
        row_total = 0
        # Calc how many units in this floor's tallest building cell
        max_lines = max(
            len(cells.get(f"{fl}-{b}", [])) for b in buildings
        ) if buildings else 0
        max_lines = max(max_lines, 1)
        cell_h = max(row_h, max_lines * 7 + 2)

        _cell(x, cur_y, col_floor_w, cell_h, str(fl), bold=True, grey=True, fontsize=6)
        cx2 = x + col_floor_w
        for b in buildings:
            key   = f"{fl}-{b}"
            units = cells.get(key, [])
            row_total += len(units)
            # Draw cell
            c.setLineWidth(0.5)
            c.setFillColorRGB(1, 1, 1)
            c.rect(cx2, cur_y - cell_h, col_bld_w, cell_h, stroke=1, fill=1)
            c.setFillColorRGB(0, 0, 0)
            c.setFont("Helvetica", 5.5)
            for j, u in enumerate(units):
                c.drawCentredString(cx2 + col_bld_w / 2,
                                    cur_y - 7 - j * 7, u)
            cx2 += col_bld_w
        _cell(cx2, cur_y, col_tot_w, cell_h, str(row_total) if row_total else "",
              bold=True, fontsize=6)
        cur_y -= cell_h

    # Total row
    _cell(x, cur_y, col_floor_w, row_h, "Total", bold=True, grey=True)
    cx2 = x + col_floor_w
    grand_total = 0
    for b in buildings:
        col_total = sum(len(cells.get(f"{fl}-{b}", [])) for fl in floors)
        grand_total += col_total
        _cell(cx2, cur_y, col_bld_w, row_h,
              str(col_total) if col_total else "", bold=True)
        cx2 += col_bld_w
    _cell(cx2, cur_y, col_tot_w, row_h, str(grand_total), bold=True)


# ════════════════════════════════════════════════════════════════════════════
# RIGHT ZONE — Title Block (11 sections)
# ════════════════════════════════════════════════════════════════════════════

def _draw_right_zone(c: rl_canvas.Canvas, drawing: dict, project: dict):
    c.setLineWidth(LW_BORDER)
    c.setStrokeColorRGB(0, 0, 0)
    c.rect(TB_X, 0, TB_W, PAGE_H, stroke=1, fill=0)

    has_cutouts = any(
        len(p.get("cutouts", [])) > 0
        for p in drawing.get("parts", [])
    )

    # ── Section heights ───────────────────────────────────────────────────────
    # Scaled proportionally so total = PAGE_H
    BASE = {
        1:  52,   # Company header (logo + contact)
        2:  70,   # Edge key code
        3:  80,   # Material specs (thickness/color/qty in large text)
        4:  52,   # Sink info (skip if no cutouts)
        5:  88,   # Job info (project, title, date, drawn by, scale, ticket)
        6:  52,   # Schedule fields
        7:  40,   # Revisions
        8:  38,   # Units
        9:  26,   # Page / job info
        10: 70,   # Key notes
        11: 20,   # Signature
    }

    sections = list(BASE.keys())
    if not has_cutouts:
        sections.remove(4)

    raw_total = sum(BASE[s] for s in sections)
    scale_f   = PAGE_H / raw_total

    # Build top positions (from PAGE_H downward)
    sec_top: Dict[int, float] = {}
    cur_y = PAGE_H
    for s in sections:
        sec_top[s] = cur_y
        cur_y -= BASE[s] * scale_f

    def sh(s): return BASE[s] * scale_f

    def divider(y):
        c.setLineWidth(LW_BORDER)
        c.setStrokeColorRGB(0, 0, 0)
        c.line(TB_X, y, TB_X + TB_W, y)

    company    = project.get("company", {})
    issue_raw  = project.get("issueDate")

    # ── SEC 1 — Company ───────────────────────────────────────────────────────
    s1t = sec_top[1]; s1h = sh(1)
    divider(s1t - s1h)
    _tb_c(c, company.get("name",     "Your Company"),  s1t - 12, "Helvetica-Bold", 9)
    _tb_c(c, company.get("address1", ""),               s1t - 23, "Helvetica", 7)
    _tb_c(c, company.get("address2", ""),               s1t - 32, "Helvetica", 7)
    ph_str = company.get("phone", "")
    if ph_str:
        _tb_c(c, f"Ph: {ph_str}", s1t - 42, "Helvetica", 7)

    # ── SEC 2 — Edge Key Code ─────────────────────────────────────────────────
    s2t = sec_top[2]; s2h = sh(2)
    divider(s2t - s2h)
    y = s2t - 10
    c.setFont("Helvetica-Bold", 7)
    c.setFillColorRGB(0, 0, 0)
    c.drawString(TB_TXT_X, y, "Edge Type and Finish Key Code")
    _underline(c, TB_TXT_X, y, "Edge Type and Finish Key Code", "Helvetica-Bold", 7)
    entries = [
        ("X",  "= Eased & Polished"),
        ("B",  "= Full Bullnose"),
        ("LB", "= Laminated Bullnose"),
        ("LE", "= Laminated Eased & Polished"),
        ("S",  "= Seam"),
    ]
    y -= 10
    for sym, desc in entries:
        c.setFont("Helvetica-Bold", 6.5)
        c.drawString(TB_TXT_X, y, sym)
        c.setFont("Helvetica", 6.5)
        c.drawString(TB_TXT_X + 14, y, desc)
        y -= 9

    # ── SEC 3 — Material Specs ────────────────────────────────────────────────
    s3t = sec_top[3]; s3h = sh(3)
    divider(s3t - s3h)
    y = s3t - 10
    c.setFont("Helvetica-Bold", 7)
    c.setFillColorRGB(0, 0, 0)
    c.drawString(TB_TXT_X, y, "Material Thickness:")
    y -= 4
    _tb_c(c, project.get("thickness", "3CM"), y, "Helvetica-Bold", 14)
    y -= 18
    c.setFont("Helvetica-Bold", 7)
    c.drawString(TB_TXT_X, y, "Material Color:")
    y -= 4
    _tb_c(c, project.get("material", ""), y, "Helvetica-Bold", 11)
    y -= 15
    c.setFont("Helvetica-Bold", 7)
    c.drawString(TB_TXT_X, y, "Quantity:")
    y -= 4
    unit_count = len(drawing.get("units", []))
    qty_str = str(unit_count) if unit_count else "—"
    _tb_c(c, qty_str, y, "Helvetica-Bold", 16)

    # ── SEC 4 — Sink Info ─────────────────────────────────────────────────────
    if has_cutouts:
        s4t = sec_top[4]; s4h = sh(4)
        divider(s4t - s4h)
        y = s4t - 9
        c.setFont("Helvetica-Bold", 7)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(TB_TXT_X, y, "Sink Info:")
        y -= 9
        c.setFont("Helvetica", 7)
        for p in drawing.get("parts", []):
            for co in p.get("cutouts", []):
                mount = co.get("mountType", "undermount").replace("_", " ").title()
                sink_label = co.get("sinkLabel", co.get("sinkType", "").replace("_", " ").title())
                model = co.get("modelNumber", "")
                for line in [mount, sink_label, f"Model #{model}" if model else "", "Cut by Template"]:
                    if line.strip():
                        c.drawString(TB_TXT_X, y, line)
                        y -= 9

    # ── SEC 5 — Job Info ──────────────────────────────────────────────────────
    s5t = sec_top[5]; s5h = sh(5)
    divider(s5t - s5h)
    y = s5t - 9
    proj_str = project.get("name", "")
    loc_str  = project.get("location", "")
    _tb_label_value(c, "Project:", f"{proj_str}", y)
    y -= 9
    if loc_str:
        c.setFont("Helvetica", 7)
        c.drawString(TB_TXT_X + 8, y, loc_str)
        y -= 9
    _tb_label_value(c, "Title:", drawing.get("name", ""), y);          y -= 9
    _tb_label_value(c, "Date:", fmt_date(issue_raw), y);                y -= 9
    _tb_label_value(c, "Drawn By:", project.get("drawnBy", ""), y);     y -= 9
    _tb_label_value(c, "Scale:", drawing.get("scale", '3/4" = 1\'-0"'), y); y -= 9
    _tb_label_value(c, "Work Ticket#:", drawing.get("ticketNumber", ""), y)

    # ── SEC 6 — Schedule Fields ───────────────────────────────────────────────
    s6t = sec_top[6]; s6h = sh(6)
    divider(s6t - s6h)
    y = s6t - 9
    c.setFont("Helvetica", 7)
    c.setFillColorRGB(0, 0, 0)
    sched = [
        f"ORDER #  _____________",
        f"REQUESTED DATE  ___________________",
        f"SCHED DATE      ___________________",
        f"ISSUE DATE:  {fmt_date(issue_raw)}",
    ]
    for line in sched:
        c.drawString(TB_TXT_X, y, line); y -= 11

    # ── SEC 7 — Revisions ─────────────────────────────────────────────────────
    s7t = sec_top[7]; s7h = sh(7)
    divider(s7t - s7h)
    y = s7t - 9
    c.setFont("Helvetica-Bold", 7)
    c.drawString(TB_TXT_X, y, "REVISIONS:")
    y -= 10
    c.setFont("Helvetica", 7)
    c.drawString(TB_TXT_X, y, "1___  2___  3___  4___  5___")

    # ── SEC 8 — Units ─────────────────────────────────────────────────────────
    s8t = sec_top[8]; s8h = sh(8)
    divider(s8t - s8h)
    y = s8t - 9
    c.setFont("Helvetica-Bold", 7)
    c.drawString(TB_TXT_X, y, "UNITS:")
    y -= 9
    _draw_wrapped(c, ", ".join(drawing.get("units", [])),
                  TB_TXT_X, y, TB_W - 10, "Helvetica", 6.5, 8)

    # ── SEC 9 — Page / Job Info ───────────────────────────────────────────────
    s9t = sec_top[9]; s9h = sh(9)
    divider(s9t - s9h)
    y = s9t - 7
    c.setFont("Helvetica", 6.5)
    c.setFillColorRGB(0, 0, 0)
    c.drawString(TB_TXT_X, y,
                 f"PROJECT NAME: {project.get('name','')}")
    y -= 8
    c.drawString(TB_TXT_X, y,
                 f"JOB#: {project.get('jobNumber','')}   "
                 f"DRAWN BY: {project.get('drawnBy','')}   "
                 f"PAGE: {drawing.get('pageNumber', 1)}")

    # ── SEC 10 — Key Notes ────────────────────────────────────────────────────
    s10t = sec_top[10]; s10h = sh(10)
    divider(s10t - s10h)
    y = s10t - 9
    c.setFont("Helvetica-Bold", 7)
    c.drawString(TB_TXT_X, y, "GRANITE/QUARTZ KEY NOTES:")
    _underline(c, TB_TXT_X, y, "GRANITE/QUARTZ KEY NOTES:", "Helvetica-Bold", 7)
    y -= 8
    notes = [
        ("= XXX",  "GRANITE/QUARTZ"),
        ("= FLAT", "EDGE (STOVE POLISH)"),
        ("BS",     "= BACK SPLASH"),
        ("SS",     "= SIDE SPLASH"),
        ("TR",     '= 1/8" RADIUS'),
        ("RAW",    "= RAW EDGE"),
        ("=",      "OVERSIZED PART"),
        ("",       "ALL PARTS MADE TO SIZE UNLESS NOTED"),
        ("",       'WITH A "RECTANGLE" ON THE DIMENSION'),
    ]
    c.setFont("Helvetica", 6)
    for sym, desc in notes:
        if sym:
            c.setFont("Helvetica-Bold", 6)
            c.drawString(TB_TXT_X, y, sym)
            c.setFont("Helvetica", 6)
            c.drawString(TB_TXT_X + 16, y, desc)
        else:
            c.setFont("Helvetica", 6)
            c.drawString(TB_TXT_X, y, desc)
        y -= 7

    # ── SEC 11 — Signature ────────────────────────────────────────────────────
    s11t = sec_top[11]; s11h = sh(11)
    divider(s11t - s11h)
    mid_y = s11t - s11h / 2 - 3
    c.setFont("Helvetica", 7)
    _tb_c(c, "Signature of Approval _________________  Date _______", mid_y, "Helvetica", 7)

    # X marker at bottom left (matches reference)
    c.setFont("Helvetica-Bold", 12)
    c.setFillColorRGB(0, 0, 0)
    c.drawString(4, 6, "X")


# ── Title block helpers ───────────────────────────────────────────────────────

def _tb_c(c: rl_canvas.Canvas, text: str, y: float, font: str, size: float):
    """Draw text centred in the title block."""
    c.setFont(font, size)
    c.setFillColorRGB(0, 0, 0)
    c.drawCentredString(TB_X + TB_W / 2, y, text)


def _tb_label_value(c: rl_canvas.Canvas, label: str, value: str, y: float):
    c.setFont("Helvetica-Bold", 7)
    c.setFillColorRGB(0, 0, 0)
    c.drawString(TB_TXT_X, y, label)
    c.setFont("Helvetica", 7)
    lw = c.stringWidth(label, "Helvetica-Bold", 7)
    _draw_wrapped(c, value, TB_TXT_X + lw + 2, y, TB_W - lw - 10,
                  "Helvetica", 7, 8)


def _underline(c: rl_canvas.Canvas, x: float, y: float, text: str,
               font: str, size: float):
    tw = c.stringWidth(text, font, size)
    c.setLineWidth(0.4)
    c.line(x, y - 1, x + tw, y - 1)


def _draw_wrapped(c: rl_canvas.Canvas, text: str, x: float, y: float,
                  max_w: float, font: str, size: float, line_h: float):
    if not text:
        return
    c.setFont(font, size)
    c.setFillColorRGB(0, 0, 0)
    words = text.split()
    line  = ""
    for word in words:
        test = (line + " " + word).strip()
        if c.stringWidth(test, font, size) <= max_w:
            line = test
        else:
            if line:
                c.drawString(x, y, line)
                y -= line_h
            line = word
    if line:
        c.drawString(x, y, line)
