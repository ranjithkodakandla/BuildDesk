"""
Assembly SVG Preview Exporter  (Phase 4)
=========================================
Upgraded to match PDF drawing fidelity:
  - Scaled part outlines
  - Edge visual differentiation (stroke colour + width + dash)
  - Cutout overlays (dashed rect, rounded for sinks, mount annotation)
  - Hole circles with crosshair and Ø label
  - Splash bands along correct edges
  - Seam lines between adjacent parts
  - Dimension callout lines
  - Part label, name, area
  - Edge legend block
  - Assembly title bar with variant badge
"""

from __future__ import annotations
from typing import List

from app.models.fabrication import (
    Assembly, CutoutType, EdgeType, MountType, Part, Position, SplashType,
)
from app.models.hierarchy import UnitVariant

_SCALE  = 4.5     # SVG px per inch (display scale — not print scale)
_MARGIN = 55.0
_GAP    = 22.0    # gap between parts

# Colours (SVG hex)
_PART_FILL   = "#f0f4f8"
_PART_STR    = "#1a2332"
_POLISHED    = "#1a2332"   # thick solid — polished/exposed
_EASED       = "#4a7fb5"   # medium blue — eased
_MITER       = "#e67e22"   # orange — miter
_FINISHED    = "#27ae60"   # green — finished
_RAW         = "#aaaaaa"   # grey dashed — raw/wall
_UNFINISHED  = "#888888"   # light dashed
_BULLNOSE    = "#9b59b6"   # purple
_CUTOUT_STR  = "#c0392b"
_HOLE_COL    = "#8e44ad"
_SPLASH_COL  = "#3498db"
_SPLASH_FILL = "#d6eaf8"
_SEAM_COL    = "#e74c3c"
_DIM_COL     = "#4a7fb5"
_TITLE_BG    = "#1a2332"
_TITLE_FG    = "#ffffff"

_EDGE_STYLES = {
    "polished":     (_POLISHED,  3.0, "none"),
    "eased":        (_EASED,     2.0, "none"),
    "miter":        (_MITER,     2.5, "4,2"),
    "finished":     (_FINISHED,  2.0, "none"),
    "raw":          (_RAW,       1.0, "3,2"),
    "unfinished":   (_UNFINISHED,1.0, "3,2"),
    "bullnose":     (_BULLNOSE,  2.0, "none"),
    "half_bullnose":(_BULLNOSE,  1.5, "2,1"),
    "bevel":        (_EASED,     1.5, "none"),
    "ogee":         (_POLISHED,  2.0, "2,1"),
    "laminated":    (_PART_STR,  2.0, "none"),
    "flat":         (_PART_STR,  1.5, "none"),
}
_SPLASH_W = 9.0  # px band width


def _esc(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class AssemblySvgExporter:

    def export(self, assembly: Assembly) -> str:
        parts = assembly.parts
        if not parts:
            return self._empty_svg(assembly)

        # Compute layout
        layout = self._compute_layout(parts)
        svg_w  = layout["svg_w"]
        svg_h  = layout["svg_h"]
        items  = layout["items"]   # list of {part, x, y, pw, ph, idx}

        elems: List[str] = []

        # Background
        elems.append(f'<rect width="{svg_w:.1f}" height="{svg_h:.1f}" fill="#ffffff"/>')

        # Title bar
        variant_badge = ""
        if assembly.variant != UnitVariant.STANDARD:
            variant_badge = (
                f' <rect x="{svg_w - 75}" y="5" width="68" height="18" '
                f'rx="3" fill="#4a7fb5"/>'
                f'<text x="{svg_w - 41:.1f}" y="18" text-anchor="middle" '
                f'font-size="9" font-weight="bold" fill="white" font-family="sans-serif">'
                f'{_esc(assembly.variant.value.upper())}</text>'
            )
        title = f"{assembly.name}  —  {assembly.assembly_type.value.replace('_', ' ').title()}"
        elems.append(
            f'<rect x="0" y="0" width="{svg_w:.1f}" height="42" fill="{_TITLE_BG}"/>'
            f'{variant_badge}'
            f'<text x="12" y="16" font-size="12" font-weight="bold" fill="{_TITLE_FG}" '
            f'font-family="sans-serif" dominant-baseline="hanging">{_esc(title)}</text>'
            f'<text x="12" y="30" font-size="8" fill="#aac4e0" font-family="monospace" '
            f'dominant-baseline="hanging">BuildDesk Fabrication Preview  ·  Scale: NTS</text>'
        )

        # Draw each part
        for item in items:
            elems += self._draw_part(item)

        # Seam lines
        for i in range(len(items) - 1):
            a, b = items[i], items[i + 1]
            sx = a["x"] + a["pw"]
            y1 = min(a["y"], b["y"])
            y2 = max(a["y"] + a["ph"], b["y"] + b["ph"])
            elems.append(
                f'<line x1="{sx:.1f}" y1="{y1:.1f}" x2="{sx:.1f}" y2="{y2:.1f}" '
                f'stroke="{_SEAM_COL}" stroke-width="2" stroke-dasharray="5,3"/>'
                f'<text x="{sx:.1f}" y="{(y1+y2)/2:.1f}" '
                f'text-anchor="middle" font-size="7" fill="{_SEAM_COL}" '
                f'font-family="monospace" dominant-baseline="middle">SEAM</text>'
            )

        # Edge legend
        elems += self._draw_legend(svg_w - 175, svg_h - 120)

        # Arrow defs
        defs = (
            '<defs><marker id="arr" markerWidth="5" markerHeight="5" '
            'refX="2.5" refY="2.5" orient="auto">'
            f'<path d="M0,0 L0,5 L5,2.5 z" fill="{_DIM_COL}"/>'
            '</marker></defs>'
        )

        body = "\n  ".join(elems)
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{svg_w:.1f}" height="{svg_h:.1f}" '
            f'viewBox="0 0 {svg_w:.1f} {svg_h:.1f}">'
            f'\n  {defs}\n  {body}\n</svg>'
        )

    # ── Layout ───────────────────────────────────────────────────────────────

    def _compute_layout(self, parts: List[Part]) -> dict:
        title_h   = 42.0
        dim_space = 28.0
        splash_pad = _SPLASH_W + 4

        cursor_x = _MARGIN + splash_pad
        base_y   = title_h + _MARGIN + splash_pad
        max_ph   = 0.0
        items    = []

        for i, part in enumerate(parts):
            pw = part.dimensions.length * _SCALE
            ph = part.dimensions.depth  * _SCALE
            items.append({
                "part": part, "x": cursor_x, "y": base_y,
                "pw": pw, "ph": ph, "idx": i,
            })
            cursor_x += pw + _GAP
            max_ph = max(max_ph, ph)

        svg_w = cursor_x - _GAP + _MARGIN + dim_space + splash_pad
        svg_h = base_y + max_ph + dim_space + splash_pad + _MARGIN + 130  # 130 for legend
        return {"svg_w": svg_w, "svg_h": svg_h, "items": items}

    # ── Part drawing ──────────────────────────────────────────────────────────

    def _draw_part(self, item: dict) -> List[str]:
        part: Part = item["part"]
        x, y, pw, ph = item["x"], item["y"], item["pw"], item["ph"]
        idx = item["idx"]
        label = chr(65 + idx)
        dims = part.dimensions
        area = dims.length * dims.depth / 144
        elems: List[str] = []

        # Part fill
        elems.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{pw:.1f}" height="{ph:.1f}" '
            f'fill="{_PART_FILL}" stroke="{_PART_STR}" stroke-width="1.5"/>'
        )

        # Splash bands
        elems += self._draw_splashes(part, x, y, pw, ph)

        # Edge treatments (drawn over part outline)
        elems += self._draw_edges(part, x, y, pw, ph)

        # Cutouts
        elems += self._draw_cutouts(part, x, y, pw, ph)

        # Holes
        elems += self._draw_holes(part, x, y, pw, ph)

        # Part label
        elems.append(
            f'<text x="{x + 6:.1f}" y="{y + 15:.1f}" font-size="11" font-weight="bold" '
            f'fill="{_PART_STR}" font-family="sans-serif">PART {label}</text>'
        )
        # Name + dims + area
        name_disp = part.name[:int(pw / 5.5)] if len(part.name) * 5.5 > pw else part.name
        dim_str = f'{dims.length}" × {dims.depth}"'
        if dims.thickness:
            dim_str += f' × {dims.thickness}"'
        dim_str += f'  ({area:.2f} sqft)'
        elems.append(
            f'<text x="{x + 6:.1f}" y="{y + 27:.1f}" font-size="7.5" fill="#555" '
            f'font-family="monospace">{_esc(name_disp)}</text>'
            f'<text x="{x + 6:.1f}" y="{y + 37:.1f}" font-size="7" fill="{_DIM_COL}" '
            f'font-family="monospace">{_esc(dim_str)}</text>'
        )
        if part.notes:
            elems.append(
                f'<text x="{x + 6:.1f}" y="{y + ph - 8:.1f}" font-size="6.5" '
                f'fill="#c0392b" font-family="sans-serif" font-style="italic">'
                f'{_esc(part.notes[:50])}</text>'
            )

        # Dimension lines
        elems += self._draw_dims(x, y, pw, ph, dims.length, dims.depth)

        return elems

    def _draw_edges(self, part: Part, x: float, y: float, pw: float, ph: float) -> List[str]:
        elems = []
        side_map = {
            "front": (x, y + ph, x + pw, y + ph),        # SVG: bottom of rect = high y
            "back":  (x, y,      x + pw, y),
            "left":  (x, y,      x,      y + ph),
            "right": (x + pw, y, x + pw, y + ph),
        }
        # Note: SVG y increases downward, so "front" (fabrication bottom) = y+ph in SVG
        # Remap: fabrication front = viewer front = bottom of drawing = top in SVG y-up
        # For SVG (y-down): part top = y, part bottom = y+ph
        # Front of countertop = the exposed near edge = draw at y+ph (SVG bottom)
        svg_side_map = {
            "front": (x, y + ph, x + pw, y + ph),   # bottom of rect in SVG
            "back":  (x, y,      x + pw, y),          # top of rect in SVG
            "left":  (x, y,      x,      y + ph),
            "right": (x + pw, y, x + pw, y + ph),
        }
        for edge in part.edges:
            pos = edge.position.value.lower()
            if pos not in svg_side_map:
                continue
            x1, y1, x2, y2 = svg_side_map[pos]
            style = _EDGE_STYLES.get(edge.edge_type.value,
                                     (_PART_STR, 1.5, "none"))
            col, sw, dash = style
            dash_attr = f'stroke-dasharray="{dash}"' if dash != "none" else ""
            elems.append(
                f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                f'stroke="{col}" stroke-width="{sw}" {dash_attr}/>'
            )
            # Edge type label at midpoint
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            etype = edge.edge_type.value.replace("_", " ").title()
            elems.append(
                f'<text x="{mx:.1f}" y="{my - 4:.1f}" text-anchor="middle" '
                f'font-size="6" fill="{col}" font-family="monospace" '
                f'font-weight="bold">{_esc(etype)}</text>'
            )
        return elems

    def _draw_cutouts(self, part: Part, x: float, y: float, pw: float, ph: float) -> List[str]:
        elems = []
        for co in part.cutouts:
            scale = _SCALE
            cw = co.dimensions.length * scale
            ch = co.dimensions.depth  * scale
            cx = x + co.center_x * scale - cw / 2
            cy = y + co.center_y * scale - ch / 2
            cx = max(x, min(cx, x + pw - cw))
            cy = max(y, min(cy, y + ph - ch))
            is_sink = co.cutout_type == CutoutType.SINK
            rx = "4" if is_sink else "0"
            mount = "U/M" if co.mount_type == MountType.UNDERMOUNT else "O/M"
            ctype = co.cutout_type.value.replace("_", " ").upper()
            elems.append(
                f'<rect x="{cx:.1f}" y="{cy:.1f}" width="{cw:.1f}" height="{ch:.1f}" '
                f'rx="{rx}" fill="white" stroke="{_CUTOUT_STR}" '
                f'stroke-width="1.5" stroke-dasharray="4,2"/>'
            )
            if cw > 22 and ch > 12:
                elems.append(
                    f'<text x="{cx + cw/2:.1f}" y="{cy + ch/2 - 3:.1f}" '
                    f'text-anchor="middle" font-size="7" font-weight="bold" '
                    f'fill="{_CUTOUT_STR}" font-family="monospace">{_esc(ctype)}</text>'
                    f'<text x="{cx + cw/2:.1f}" y="{cy + ch/2 + 7:.1f}" '
                    f'text-anchor="middle" font-size="6" '
                    f'fill="{_CUTOUT_STR}" font-family="monospace">{_esc(mount)}</text>'
                )
        return elems

    def _draw_holes(self, part: Part, x: float, y: float, pw: float, ph: float) -> List[str]:
        elems = []
        for hole in part.holes:
            hx = x + hole.center_x * _SCALE
            hy = y + hole.center_y * _SCALE
            r  = max(4.0, (hole.diameter / 2) * _SCALE)
            elems.append(
                f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="{r:.1f}" '
                f'fill="white" stroke="{_HOLE_COL}" stroke-width="1.5"/>'
                f'<line x1="{hx - r*0.7:.1f}" y1="{hy:.1f}" '
                f'x2="{hx + r*0.7:.1f}" y2="{hy:.1f}" '
                f'stroke="{_HOLE_COL}" stroke-width="0.5"/>'
                f'<line x1="{hx:.1f}" y1="{hy - r*0.7:.1f}" '
                f'x2="{hx:.1f}" y2="{hy + r*0.7:.1f}" '
                f'stroke="{_HOLE_COL}" stroke-width="0.5"/>'
                f'<text x="{hx:.1f}" y="{hy - r - 3:.1f}" '
                f'text-anchor="middle" font-size="6.5" font-weight="bold" '
                f'fill="{_HOLE_COL}" font-family="monospace">Ø{hole.diameter}"</text>'
                f'<text x="{hx:.1f}" y="{hy + r + 10:.1f}" '
                f'text-anchor="middle" font-size="6" '
                f'fill="{_HOLE_COL}" font-family="monospace">{_esc(hole.purpose)}</text>'
            )
        return elems

    def _draw_splashes(self, part: Part, x: float, y: float, pw: float, ph: float) -> List[str]:
        elems = []
        for sp in part.splashes:
            stype = sp.splash_type.value.lower()
            sw = sp.dimensions.length  * _SCALE
            if "back" in stype:
                # top band (SVG y-down: top of part = y)
                bw = min(sw, pw)
                elems.append(
                    f'<rect x="{x:.1f}" y="{y - _SPLASH_W:.1f}" '
                    f'width="{bw:.1f}" height="{_SPLASH_W:.1f}" '
                    f'fill="{_SPLASH_FILL}" stroke="{_SPLASH_COL}" stroke-width="1"/>'
                    f'<text x="{x + bw/2:.1f}" y="{y - 3:.1f}" '
                    f'text-anchor="middle" font-size="6" fill="{_SPLASH_COL}" '
                    f'font-family="monospace">BSP {sp.dimensions.depth}"</text>'
                )
            elif "left" in stype:
                bh = min(sw, ph)
                elems.append(
                    f'<rect x="{x - _SPLASH_W:.1f}" y="{y:.1f}" '
                    f'width="{_SPLASH_W:.1f}" height="{bh:.1f}" '
                    f'fill="{_SPLASH_FILL}" stroke="{_SPLASH_COL}" stroke-width="1"/>'
                )
            elif "right" in stype:
                bh = min(sw, ph)
                elems.append(
                    f'<rect x="{x + pw:.1f}" y="{y:.1f}" '
                    f'width="{_SPLASH_W:.1f}" height="{bh:.1f}" '
                    f'fill="{_SPLASH_FILL}" stroke="{_SPLASH_COL}" stroke-width="1"/>'
                )
        return elems

    def _draw_dims(self, x, y, pw, ph, length, depth) -> List[str]:
        off = 22.0
        elems = []
        # Width below
        dy = y + ph + off
        elems.append(
            f'<line x1="{x:.1f}" y1="{y + ph:.1f}" x2="{x:.1f}" y2="{dy:.1f}" '
            f'stroke="{_DIM_COL}" stroke-width="0.6"/>'
            f'<line x1="{x + pw:.1f}" y1="{y + ph:.1f}" x2="{x + pw:.1f}" y2="{dy:.1f}" '
            f'stroke="{_DIM_COL}" stroke-width="0.6"/>'
            f'<line x1="{x:.1f}" y1="{dy:.1f}" x2="{x + pw:.1f}" y2="{dy:.1f}" '
            f'stroke="{_DIM_COL}" stroke-width="1.2"/>'
            f'<line x1="{x:.1f}" y1="{dy - 3:.1f}" x2="{x:.1f}" y2="{dy + 3:.1f}" '
            f'stroke="{_DIM_COL}" stroke-width="1.2"/>'
            f'<line x1="{x + pw:.1f}" y1="{dy - 3:.1f}" x2="{x + pw:.1f}" y2="{dy + 3:.1f}" '
            f'stroke="{_DIM_COL}" stroke-width="1.2"/>'
            f'<text x="{x + pw/2:.1f}" y="{dy + 12:.1f}" text-anchor="middle" '
            f'font-size="9" fill="{_DIM_COL}" font-family="monospace" '
            f'font-weight="600">{length}"</text>'
        )
        # Depth right
        rx = x + pw + off
        elems.append(
            f'<line x1="{x + pw:.1f}" y1="{y:.1f}" x2="{rx:.1f}" y2="{y:.1f}" '
            f'stroke="{_DIM_COL}" stroke-width="0.6"/>'
            f'<line x1="{x + pw:.1f}" y1="{y + ph:.1f}" x2="{rx:.1f}" y2="{y + ph:.1f}" '
            f'stroke="{_DIM_COL}" stroke-width="0.6"/>'
            f'<line x1="{rx:.1f}" y1="{y:.1f}" x2="{rx:.1f}" y2="{y + ph:.1f}" '
            f'stroke="{_DIM_COL}" stroke-width="1.2"/>'
            f'<line x1="{rx - 3:.1f}" y1="{y:.1f}" x2="{rx + 3:.1f}" y2="{y:.1f}" '
            f'stroke="{_DIM_COL}" stroke-width="1.2"/>'
            f'<line x1="{rx - 3:.1f}" y1="{y + ph:.1f}" x2="{rx + 3:.1f}" y2="{y + ph:.1f}" '
            f'stroke="{_DIM_COL}" stroke-width="1.2"/>'
            f'<text x="{rx + 12:.1f}" y="{y + ph/2:.1f}" text-anchor="middle" '
            f'font-size="9" fill="{_DIM_COL}" font-family="monospace" font-weight="600" '
            f'transform="rotate(-90 {rx + 12:.1f} {y + ph/2:.1f})">{depth}"</text>'
        )
        return elems

    def _draw_legend(self, x: float, y: float) -> List[str]:
        elems = []
        entries = [
            (_POLISHED,   3.0, "none",  "Polished"),
            (_EASED,      2.0, "none",  "Eased"),
            (_MITER,      2.5, "4,2",   "Miter"),
            (_FINISHED,   2.0, "none",  "Finished"),
            (_RAW,        1.0, "3,2",   "Raw/Wall"),
        ]
        box_h = 12 + len(entries) * 16 + 6
        box_w = 140.0
        elems.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{box_w:.1f}" height="{box_h:.1f}" '
            f'fill="#f8f9fa" stroke="#cccccc" stroke-width="0.5" rx="3"/>'
            f'<text x="{x + 6:.1f}" y="{y + 12:.1f}" font-size="8" font-weight="bold" '
            f'fill="#1a2332" font-family="sans-serif">EDGE LEGEND</text>'
        )
        ey = y + 24
        for col, sw, dash, label in entries:
            dash_attr = f'stroke-dasharray="{dash}"' if dash != "none" else ""
            elems.append(
                f'<line x1="{x + 6:.1f}" y1="{ey:.1f}" x2="{x + 36:.1f}" y2="{ey:.1f}" '
                f'stroke="{col}" stroke-width="{sw}" {dash_attr}/>'
                f'<text x="{x + 42:.1f}" y="{ey + 4:.1f}" font-size="7.5" '
                f'fill="#333" font-family="sans-serif">{_esc(label)}</text>'
            )
            ey += 16
        return elems

    def _empty_svg(self, assembly: Assembly) -> str:
        msg = f"Assembly '{assembly.name}' has no parts yet."
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="100">'
            '<rect width="400" height="100" fill="#f8f8f8" stroke="#ccc"/>'
            f'<text x="200" y="50" text-anchor="middle" dominant-baseline="middle" '
            f'font-size="12" fill="#888" font-family="sans-serif">{_esc(msg)}</text>'
            '</svg>'
        )
