"""
Assembly SVG Preview Exporter  (Phase 3)
=========================================
Generates a single-assembly SVG drawing for rapid visual validation.

Wraps the existing SvgExporter primitive renderer.
Does NOT reproduce the old shape-based workflow —
it renders from the real fabrication Assembly domain model.

Drawing content per part:
    - Part outline rectangle (to scale)
    - Part label (A, B, C …)
    - Dimension callouts (length × depth)
    - Cutout rectangles (dashed, labelled)
    - Hole markers (circle, labelled)
    - Splash indicators (labelled bracket)
    - Edge treatment annotations

Coordinate system: origin bottom-left, y-up (matches geometry primitives).
SVG renders at 4px per inch (same as SvgExporter default).
"""

from __future__ import annotations

from typing import List

from app.models.fabrication import Assembly, CutoutType, Part


_SCALE      = 4.0    # SVG px per inch
_MARGIN     = 60.0   # px around the drawing
_PART_GAP   = 20.0   # px gap between sequential parts
_FILL       = "#e8f4fd"
_STROKE     = "#1a2332"
_DIM_COL    = "#4a7fb5"
_CUTOUT_COL = "#c0392b"
_HOLE_COL   = "#27ae60"
_SPLASH_COL = "#8e44ad"
_TITLE_BG   = "#1a2332"
_TITLE_FG   = "#ffffff"


def _esc(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class AssemblySvgExporter:
    """
    Produces a self-contained SVG string for one Assembly.
    Parts are laid out left-to-right with a gap between them.
    """

    def export(self, assembly: Assembly) -> str:
        parts = assembly.parts
        if not parts:
            return self._empty_svg(assembly)

        # Layout: place parts left-to-right
        # Each part occupies length × depth inches → scaled to SVG px
        layout: List[dict] = []
        cursor_x = _MARGIN
        max_h = 0.0

        for i, part in enumerate(parts):
            pw = part.dimensions.length * _SCALE
            ph = part.dimensions.depth  * _SCALE
            layout.append({"part": part, "x": cursor_x, "y": _MARGIN + 50, "w": pw, "h": ph, "idx": i})
            cursor_x += pw + _PART_GAP
            max_h = max(max_h, ph)

        svg_w = cursor_x - _PART_GAP + _MARGIN
        svg_h = max_h + _MARGIN * 2 + 80  # 80 = title bar

        elems: List[str] = []

        # Background
        elems.append(f'<rect x="0" y="0" width="{svg_w:.1f}" height="{svg_h:.1f}" fill="#ffffff"/>')

        # Title bar
        title = f"{assembly.name}  —  {assembly.assembly_type.value.replace('_',' ').title()}"
        if assembly.variant.value != "standard":
            title += f"  [{assembly.variant.value}]"
        elems.append(
            f'<rect x="0" y="0" width="{svg_w:.1f}" height="44" fill="{_TITLE_BG}"/>'
            f'<text x="14" y="16" font-size="13" font-weight="bold" fill="{_TITLE_FG}" '
            f'font-family="sans-serif" dominant-baseline="hanging">{_esc(title)}</text>'
            f'<text x="14" y="32" font-size="9" fill="#aac4e0" font-family="monospace" '
            f'dominant-baseline="hanging">BuildDesk Assembly Preview</text>'
        )

        # Draw each part
        for item in layout:
            elems += self._draw_part(item, svg_h)

        # Arrow defs
        defs = (
            '<defs><marker id="arr" markerWidth="6" markerHeight="6" '
            'refX="3" refY="3" orient="auto" markerUnits="strokeWidth">'
            f'<path d="M0,0 L0,6 L6,3 z" fill="{_DIM_COL}"/>'
            '</marker></defs>'
        )

        body = "\n  ".join(elems)
        return (
            f'<?xml version="1.0" encoding="UTF-8"?>'
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{svg_w:.1f}" height="{svg_h:.1f}" '
            f'viewBox="0 0 {svg_w:.1f} {svg_h:.1f}">'
            f'\n  {defs}\n  {body}\n</svg>'
        )

    # ------------------------------------------------------------------
    # Part drawing helpers
    # ------------------------------------------------------------------

    def _draw_part(self, item: dict, svg_h: float) -> List[str]:
        part: Part = item["part"]
        px, py, pw, ph = item["x"], item["y"], item["w"], item["h"]
        idx: int = item["idx"]
        label = chr(65 + idx)
        elems: List[str] = []

        # Flip y for SVG (y-down). Part top-left in SVG = py (already offset from top).
        # We treat py as the SVG top-left of the part box.
        svg_py = py  # direct top-left

        # Part rectangle
        elems.append(
            f'<rect x="{px:.1f}" y="{svg_py:.1f}" width="{pw:.1f}" height="{ph:.1f}" '
            f'fill="{_FILL}" stroke="{_STROKE}" stroke-width="2" rx="2"/>'
        )

        # Part label (top-left corner)
        elems.append(
            f'<text x="{px + 6:.1f}" y="{svg_py + 16:.1f}" '
            f'font-size="14" font-weight="bold" fill="{_STROKE}" font-family="sans-serif">'
            f'PART {label}</text>'
        )
        elems.append(
            f'<text x="{px + 6:.1f}" y="{svg_py + 30:.1f}" '
            f'font-size="9" fill="#555" font-family="monospace">'
            f'{_esc(part.name)}  |  {part.dimensions.length}" × {part.dimensions.depth}"'
            + (f' × {part.dimensions.thickness}"' if part.dimensions.thickness else "")
            + '</text>'
        )

        # Dimension callouts
        dim_off = 22.0  # px below the part
        # Width dim (horizontal below)
        dx1, dy1 = px, svg_py + ph + dim_off
        dx2, dy2 = px + pw, svg_py + ph + dim_off
        tx, ty = (dx1 + dx2) / 2, dy1 - 5
        elems.append(
            f'<line x1="{dx1:.1f}" y1="{svg_py + ph:.1f}" x2="{dx1:.1f}" y2="{dy1:.1f}" '
            f'stroke="{_DIM_COL}" stroke-width="1"/>'
            f'<line x1="{dx2:.1f}" y1="{svg_py + ph:.1f}" x2="{dx2:.1f}" y2="{dy2:.1f}" '
            f'stroke="{_DIM_COL}" stroke-width="1"/>'
            f'<line x1="{dx1:.1f}" y1="{dy1:.1f}" x2="{dx2:.1f}" y2="{dy2:.1f}" '
            f'stroke="{_DIM_COL}" stroke-width="1.5" '
            f'marker-start="url(#arr)" marker-end="url(#arr)"/>'
            f'<text x="{tx:.1f}" y="{ty:.1f}" text-anchor="middle" font-size="10" '
            f'fill="{_DIM_COL}" font-family="monospace" font-weight="600">'
            f'{part.dimensions.length}"</text>'
        )
        # Depth dim (vertical right)
        rx1, ry1 = px + pw + dim_off, svg_py
        rx2, ry2 = px + pw + dim_off, svg_py + ph
        rtx, rty = rx1 + 5, (ry1 + ry2) / 2
        elems.append(
            f'<line x1="{px + pw:.1f}" y1="{ry1:.1f}" x2="{rx1:.1f}" y2="{ry1:.1f}" '
            f'stroke="{_DIM_COL}" stroke-width="1"/>'
            f'<line x1="{px + pw:.1f}" y1="{ry2:.1f}" x2="{rx1:.1f}" y2="{ry2:.1f}" '
            f'stroke="{_DIM_COL}" stroke-width="1"/>'
            f'<line x1="{rx1:.1f}" y1="{ry1:.1f}" x2="{rx2:.1f}" y2="{ry2:.1f}" '
            f'stroke="{_DIM_COL}" stroke-width="1.5" '
            f'marker-start="url(#arr)" marker-end="url(#arr)"/>'
            f'<text x="{rtx:.1f}" y="{rty:.1f}" font-size="10" fill="{_DIM_COL}" '
            f'font-family="monospace" font-weight="600" '
            f'transform="rotate(90,{rtx:.1f},{rty:.1f})" text-anchor="middle">'
            f'{part.dimensions.depth}"</text>'
        )

        # Cutouts
        for co in part.cutouts:
            # Center-to-corner conversion (SVG uses top-left)
            cox = px + co.center_x * _SCALE - (co.dimensions.length * _SCALE / 2)
            coy = svg_py + co.center_y * _SCALE - (co.dimensions.depth * _SCALE / 2)
            cow = co.dimensions.length * _SCALE
            coh = co.dimensions.depth  * _SCALE
            elems.append(
                f'<rect x="{cox:.1f}" y="{coy:.1f}" width="{cow:.1f}" height="{coh:.1f}" '
                f'fill="none" stroke="{_CUTOUT_COL}" stroke-width="1.5" '
                f'stroke-dasharray="5,3"/>'
            )
            ctype = co.cutout_type.value.replace("_", " ").upper()
            elems.append(
                f'<text x="{cox + cow/2:.1f}" y="{coy + coh/2:.1f}" '
                f'text-anchor="middle" dominant-baseline="middle" '
                f'font-size="8" fill="{_CUTOUT_COL}" font-family="monospace">'
                f'{_esc(ctype)}</text>'
            )

        # Holes
        for hole in part.holes:
            hx = px + hole.center_x * _SCALE
            hy = svg_py + hole.center_y * _SCALE
            hr = hole.diameter * _SCALE / 2
            elems.append(
                f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="{hr:.1f}" '
                f'fill="none" stroke="{_HOLE_COL}" stroke-width="1.5"/>'
            )
            elems.append(
                f'<text x="{hx:.1f}" y="{hy + hr + 10:.1f}" '
                f'text-anchor="middle" font-size="7" fill="{_HOLE_COL}" font-family="monospace">'
                f'Ø{hole.diameter}"</text>'
            )

        # Splashes (shown as labelled bands along edges)
        for sp in part.splashes:
            stype = sp.splash_type.value
            if "back" in stype:
                sx, sy = px, svg_py - 8
                sw, sh = pw, 8
                elems.append(
                    f'<rect x="{sx:.1f}" y="{sy:.1f}" width="{sw:.1f}" height="{sh:.1f}" '
                    f'fill="{_SPLASH_COL}" opacity="0.3" stroke="{_SPLASH_COL}" stroke-width="1"/>'
                    f'<text x="{sx + sw/2:.1f}" y="{sy + 6:.1f}" '
                    f'text-anchor="middle" font-size="6" fill="{_SPLASH_COL}" font-family="monospace">'
                    f'SPLASH</text>'
                )
            elif "left" in stype:
                elems.append(
                    f'<rect x="{px - 8:.1f}" y="{svg_py:.1f}" width="8" height="{ph:.1f}" '
                    f'fill="{_SPLASH_COL}" opacity="0.3" stroke="{_SPLASH_COL}" stroke-width="1"/>'
                )
            elif "right" in stype:
                elems.append(
                    f'<rect x="{px + pw:.1f}" y="{svg_py:.1f}" width="8" height="{ph:.1f}" '
                    f'fill="{_SPLASH_COL}" opacity="0.3" stroke="{_SPLASH_COL}" stroke-width="1"/>'
                )

        return elems

    def _empty_svg(self, assembly: Assembly) -> str:
        msg = f"Assembly '{assembly.name}' has no parts yet."
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="100">'
            f'<rect width="400" height="100" fill="#f8f8f8" stroke="#ccc"/>'
            f'<text x="200" y="50" text-anchor="middle" dominant-baseline="middle" '
            f'font-size="12" fill="#888" font-family="sans-serif">{_esc(msg)}</text>'
            '</svg>'
        )
