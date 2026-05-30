"""
Package PDF Exporter  (Phase 4 — Drawing Fidelity)
====================================================
Multi-page fabrication PDF using FabricationDrawingEngine for vector drawings.

Phase 4 improvements over Phase 3:
  - Scaled vector part drawings (not text tables)
  - Two-column layout: drawing zone (left 62%) + notes column (right 38%)
  - Edge visual differentiation via FabricationDrawingEngine
  - Cutout overlays with mount annotation
  - Hole circles with Ø labels
  - Splash bands on part edges
  - Seam lines between parts
  - Dimension callout lines
  - Edge legend block
  - Fabrication title block (Sheet N of M, scale, revision)
  - Cover: issued_by block, sheet count callout
  - Type sheet: sq ft per type, part count
  - Summary: part-type breakdown, edge linear footage
"""

from __future__ import annotations

import io
from datetime import datetime
from typing import Dict, List, Optional

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from app.exporters.fabrication_drawing_engine import (
    FabricationDrawingEngine,
    format_dimension_inch_mm,
)
from app.models.fabrication import Assembly, EdgeType, Part, Position
from app.models.hierarchy import Project
from app.models.tenant import Tenant
from app.models.project_package import PackageSummary, UnitTypeGroup, ProjectPackage

# ── Palette ──────────────────────────────────────────────────────────────────
_C_DARK   = HexColor("#1a2332")
_C_MID    = HexColor("#4a7fb5")
_C_LIGHT  = HexColor("#f0f4f8")
_C_WHITE  = HexColor("#ffffff")
_C_GREY   = HexColor("#888888")
_C_RED    = HexColor("#c0392b")
_C_GREEN  = HexColor("#27ae60")
_C_ACCENT = HexColor("#e8f4fd")
_C_NOTE   = HexColor("#fff8e1")   # notes column background
_C_NOTE_B = HexColor("#f39c12")   # notes border

_PAGE = landscape(letter)         # 792 × 612 pts
_W, _H = _PAGE
_M    = 0.42 * inch               # outer margin

# Layout zones
_HEADER_H = 0.9 * inch
_FOOTER_H = 0.32 * inch
_BODY_Y   = _FOOTER_H + _M        # bottom of body zone
_BODY_H   = _H - _HEADER_H - _FOOTER_H - _M * 2

# Phase 18 — drawing-dominant assembly sheets
_ASM_STRIP_H  = 0.46 * inch   # taller title strip (was 0.30)
_ASM_TABLE_H  = 0.88 * inch   # compact fab table
_ASM_NOTES_H  = 0.22 * inch   # short notes strip
_VTITLE_W     = 0.82 * inch   # vertical title block on right margin

# Legacy two-column (cover/summary only)
_DRAW_FRAC = 0.61
_NOTE_FRAC = 0.36
_GUTTER    = _W * 0.03
_DRAW_W = _W * _DRAW_FRAC - _M
_NOTE_W = _W * _NOTE_FRAC - _M
_NOTE_X = _M + _DRAW_W + _GUTTER


class PackagePdfExporter:
    """
    Phase 4 multi-page fabrication PDF exporter.
    Wraps FabricationDrawingEngine for all vector drawing.
    """

    def __init__(self):
        self._engine = FabricationDrawingEngine()
        self._page_num = 0
        self._total_pages = 0

    def export(
        self,
        project: Project,
        package: ProjectPackage,
        tenant: Tenant,
        unit_type_groups: List[UnitTypeGroup],
        assemblies_by_type: Dict[str, List[Assembly]],
        summary: PackageSummary
    ) -> bytes:
        # Pre-compute total pages: 1 cover + 1 TOC + per group (1 type + N asm) + 1 summary
        tp = 2
        for g in unit_type_groups:
            tp += 1 + len(g.assembly_types)
        tp += 1
        self._total_pages = tp
        self._page_num = 0

        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=_PAGE)
        c.setTitle(f"BuildDesk — {project.name} — {package.version}")

        # Gather TOC items
        toc_items = []

        self._draw_cover(c, project, package, tenant, summary)
        c.showPage()
        
        toc_items.append(("Cover Sheet", 1))
        toc_items.append(("Table of Contents", 2))
        
        # We will draw TOC later, but we must reserve a page.
        # Actually, if we draw it now, we need to know the page numbers in advance.
        # Let's pre-calculate the page numbers for the TOC.
        current_page = 3
        for group in unit_type_groups:
            toc_items.append((f"Unit Type {group.unit_type_code} - Summary", current_page))
            current_page += 1
            for atype in group.assembly_types:
                toc_items.append((f"  {group.unit_type_code} - {atype.title()}", current_page))
                current_page += 1
        toc_items.append(("Project Summary", current_page))
        
        self._draw_toc(c, project, package.version, tenant, toc_items)
        c.showPage()

        for group in unit_type_groups:
            # Gather assemblies for this group to compute type-sheet stats
            group_assemblies: List[Assembly] = []
            for atype in group.assembly_types:
                key = f"{group.unit_type_id}::{atype}"
                group_assemblies.extend(assemblies_by_type.get(key, []))

            self._draw_type_sheet(c, project, group, group_assemblies, tenant)
            c.showPage()

            for atype in group.assembly_types:
                key = f"{group.unit_type_id}::{atype}"
                asms = assemblies_by_type.get(key, [])
                self._draw_assembly_page(c, project, group, atype, asms, package.version, tenant)
                c.showPage()

        self._draw_summary(c, project, summary, package.version, tenant)
        c.showPage()

        c.save()
        return buf.getvalue()

    # ── Cover ─────────────────────────────────────────────────────────────────

    def _draw_cover(self, c, project: Project, package: ProjectPackage, tenant: Tenant, summary: PackageSummary):
        self._page_num += 1
        # Dark header band
        c.setFillColor(_C_DARK)
        c.rect(0, _H - 2.1 * inch, _W, 2.1 * inch, fill=1, stroke=0)

        c.setFillColor(_C_MID)
        c.setFont("Helvetica-Bold", 10)
        co_name = (tenant.company_name or "BUILDDESK").upper()
        c.drawString(_M, _H - _M - 4, f"{co_name}  ·  FABRICATION DRAWING PACKAGE")

        c.setFillColor(_C_WHITE)
        c.setFont("Helvetica-Bold", 26)
        c.drawString(_M, _H - 1.05 * inch, project.name)

        # Version + sheet count badges (top-right)
        bx = _W - 1.55 * inch
        self._badge(c, bx, _H - 0.7 * inch, package.version, _C_MID)
        self._badge(c, bx, _H - 1.0 * inch,
                    f"{self._total_pages} Sheets", HexColor("#2c3e50"))

        if tenant.logo_url:
            logo_x = _W - 3.0 * inch
            logo_y = _H - 1.65 * inch
            c.setStrokeColor(_C_MID)
            c.setLineWidth(0.8)
            c.roundRect(logo_x, logo_y, 1.15 * inch, 0.42 * inch, 3, stroke=1, fill=0)
            c.setFillColor(_C_WHITE)
            c.setFont("Helvetica-Bold", 7)
            c.drawCentredString(logo_x + 0.575 * inch, logo_y + 0.25 * inch, "LOGO")
            c.setFont("Helvetica", 5.5)
            c.drawCentredString(logo_x + 0.575 * inch, logo_y + 0.11 * inch, "configured")

        # Metadata — 2-column compact grid
        meta_left = [
            ("Project",     project.name),
            ("Client",      project.client_name or "—"),
            ("Material",    project.material    or "—"),
            ("Address",     project.address     or "—"),
        ]
        meta_right = [
            ("Issue Date",  project.issue_date.strftime("%B %d, %Y") if project.issue_date else package.generated_at.strftime("%B %d, %Y") if package.generated_at else "—"),
            ("Status",      project.status.value.replace("_", " ").title()),
            ("Package",     package.status.value.replace("_", " ").upper()),
            ("Prepared By", getattr(package, "issued_by", None) or "—"),
        ]
        if package.revision_notes:
            meta_right.append(("Rev Notes", package.revision_notes[:40]))

        col_w = (_W - 2 * _M) / 2 - 0.15 * inch
        y = _H - 2.45 * inch
        row_h = 0.25 * inch
        max_rows = max(len(meta_left), len(meta_right))
        for i in range(max_rows):
            for col_idx, meta in enumerate([meta_left, meta_right]):
                if i >= len(meta):
                    continue
                lbl, val = meta[i]
                cx = _M + col_idx * (col_w + 0.3 * inch)
                c.setFont("Helvetica-Bold", 8.5)
                c.setFillColor(_C_DARK)
                c.drawString(cx, y, f"{lbl}:")
                c.setFont("Helvetica", 8.5)
                c.drawString(cx + 0.85 * inch, y, str(val)[:46])
            y -= row_h

        # Stats band — larger
        y -= 0.18 * inch
        bh = 0.72 * inch
        c.setFillColor(_C_ACCENT)
        c.rect(_M, y - bh, _W - 2 * _M, bh, fill=1, stroke=0)
        c.setStrokeColor(HexColor("#c8d8ea"))
        c.setLineWidth(0.5)
        c.rect(_M, y - bh, _W - 2 * _M, bh, fill=0, stroke=1)

        stats = [
            ("UNITS",       str(summary.total_units)),
            ("ASSEMBLIES",  str(summary.total_assemblies)),
            ("PARTS",       str(summary.total_parts)),
            ("SQ FT",       f"{summary.total_area_sqft:.1f}"),
            ("TYPES",       str(len(summary.unit_type_counts))),
            ("SHEETS",      str(self._total_pages)),
        ]
        cw = (_W - 2 * _M) / len(stats)
        for i, (lbl, val) in enumerate(stats):
            cx = _M + i * cw + cw / 2
            # divider
            if i > 0:
                c.setStrokeColor(HexColor("#c8d8ea"))
                c.setLineWidth(0.4)
                c.line(_M + i * cw, y - bh + 8, _M + i * cw, y - 8)
            c.setFont("Helvetica-Bold", 20)
            c.setFillColor(_C_DARK)
            c.drawCentredString(cx, y - bh * 0.48, val)
            c.setFont("Helvetica", 6.5)
            c.setFillColor(_C_GREY)
            c.drawCentredString(cx, y - bh + 10, lbl)

        # Standard notes — compact 2-column
        notes_y = y - bh - 0.32 * inch
        c.setFont("Helvetica-Bold", 8.5)
        c.setFillColor(_C_DARK)
        c.drawString(_M, notes_y, "STANDARD FABRICATION NOTES:")
        notes_y -= 0.18 * inch

        std_notes = tenant.standard_notes.split("\n") if tenant.standard_notes else [
            "1. Field verify all dimensions prior to fabrication.",
            "2. All substrate surfaces must be level and structurally sound.",
            "3. Seam locations are suggested; fabricator to confirm per slab size.",
            "4. All exposed edges to be polished unless otherwise noted.",
            "5. Cutouts must be verified against actual appliance templates.",
            "6. Brackets required for overhangs exceeding 10 inches.",
        ]
        # render in 2 columns
        half = (len(std_notes) + 1) // 2
        col_note_w = (_W - 2 * _M) / 2 - 0.1 * inch
        for idx, note in enumerate(std_notes):
            if not note.strip():
                continue
            col = idx // half
            row = idx % half
            cx = _M + col * (col_note_w + 0.2 * inch)
            cy = notes_y - row * 0.165 * inch
            c.setFont("Helvetica", 7.5)
            c.setFillColor(_C_GREY)
            c.drawString(cx, cy, note.strip()[:72])

        self._footer(c, project.name, package.version, tenant)

    # ── Table of Contents ─────────────────────────────────────────────────────

    def _draw_toc(self, c, project: Project, version: str, tenant: Tenant, items: List[tuple[str, int]]):
        self._page_num += 1
        
        # Header
        c.setFillColor(_C_DARK)
        c.rect(0, _H - 1.2 * inch, _W, 1.2 * inch, fill=1, stroke=0)
        c.setFillColor(_C_WHITE)
        c.setFont("Helvetica-Bold", 20)
        c.drawString(_M, _H - 0.75 * inch, "TABLE OF CONTENTS")
        
        # Items
        y = _H - 1.6 * inch
        c.setFillColor(_C_DARK)
        
        for idx, (label, pnum) in enumerate(items):
            if y < _M + 0.5 * inch:
                c.showPage()
                y = _H - 1.0 * inch
                
            is_main = not label.startswith("  ")
            
            if is_main and idx > 0:
                y -= 0.1 * inch # Extra spacing for main sections
                
            c.setFont("Helvetica-Bold" if is_main else "Helvetica", 10 if is_main else 9)
            c.drawString(_M + (0 if is_main else 0.3 * inch), y, label)
            
            # Dots
            dot_start = _M + c.stringWidth(label, "Helvetica-Bold" if is_main else "Helvetica", 10 if is_main else 9) + 10 + (0 if is_main else 0.3 * inch)
            dot_end = _W - _M - 0.5 * inch
            c.setStrokeColor(_C_GREY)
            c.setLineWidth(0.5)
            c.setDash(2, 4)
            c.line(dot_start, y + 3, dot_end, y + 3)
            c.setDash()
            
            # Page Number
            c.setFont("Helvetica", 10)
            c.drawRightString(_W - _M, y, str(pnum))
            
            y -= 0.25 * inch
            
        self._footer(c, project.name, version, tenant)

    # ── Type Sheet ────────────────────────────────────────────────────────────

    def _draw_type_sheet(
        self, c, project: Project,
        group: UnitTypeGroup, assemblies: List[Assembly], tenant: Tenant = None
    ):
        self._page_num += 1
        self._page_header(c, project,
                          f"TYPE  {group.unit_type_code}",
                          f"Qty: {group.unit_count}")

        y = _H - _HEADER_H - _M * 0.5

        # Variant badges
        bx = _M
        if group.is_mirror:
            self._badge(c, bx, y, "MIRROR", _C_MID); bx += 0.88 * inch
        if group.is_ada:
            self._badge(c, bx, y, "ADA", _C_GREEN); bx += 0.72 * inch
        y -= 0.38 * inch

        # Type name
        c.setFont("Helvetica-Bold", 13)
        c.setFillColor(_C_DARK)
        c.drawString(_M, y, group.unit_type_name)
        y -= 0.3 * inch

        # Stats strip
        total_sqft = sum(
            p.dimensions.length * p.dimensions.depth / 144.0
            for a in assemblies for p in a.parts
        )
        part_count = sum(len(a.parts) for a in assemblies)
        y -= 0.05 * inch

        stat_items = [
            ("Units",       str(group.unit_count)),
            ("Assemblies",  str(len(assemblies))),
            ("Parts",       str(part_count)),
            ("Stone Sq Ft", f"{total_sqft:.1f}"),
            ("Assembly Types", str(len(group.assembly_types))),
        ]
        stat_bh = 0.56 * inch
        c.setFillColor(_C_ACCENT)
        c.rect(_M, y - stat_bh, _W - 2 * _M, stat_bh, fill=1, stroke=0)
        scw = (_W - 2 * _M) / len(stat_items)
        for i, (slbl, sval) in enumerate(stat_items):
            scx = _M + i * scw + scw / 2
            c.setFont("Helvetica-Bold", 16)
            c.setFillColor(_C_DARK)
            c.drawCentredString(scx, y - stat_bh * 0.46, sval)
            c.setFont("Helvetica", 6.5)
            c.setFillColor(_C_GREY)
            c.drawCentredString(scx, y - stat_bh + 9, slbl.upper())
        y -= stat_bh + 0.22 * inch

        # Unit list — chip-style grid
        c.setFont("Helvetica-Bold", 8.5)
        c.setFillColor(_C_DARK)
        c.drawString(_M, y, f"UNIT NUMBERS ({group.unit_count}):")
        y -= 0.20 * inch

        chip_w, chip_h, chip_gap = 0.48 * inch, 0.18 * inch, 0.04 * inch
        cx_start, cx = _M, _M
        for code in group.unit_codes:
            if cx + chip_w > _W - _M:
                cx = cx_start
                y -= chip_h + chip_gap
            c.setFillColor(HexColor("#eef2f7"))
            c.setStrokeColor(HexColor("#94a3b8"))
            c.setLineWidth(0.3)
            c.rect(cx, y - chip_h, chip_w, chip_h, fill=1, stroke=1)
            c.setFont("Helvetica", 6.5)
            c.setFillColor(_C_DARK)
            c.drawCentredString(cx + chip_w / 2, y - chip_h + 4, code[:8])
            cx += chip_w + chip_gap
        y -= chip_h + 0.22 * inch

        # Assembly types table
        if group.assembly_types:
            c.setFont("Helvetica-Bold", 8.5)
            c.setFillColor(_C_DARK)
            c.drawString(_M, y, "ASSEMBLY TYPES ON THIS SHEET:")
            y -= 0.18 * inch
            for atype in group.assembly_types:
                c.setFont("Helvetica", 8.5)
                c.setFillColor(_C_GREY)
                c.drawString(_M + 8, y, f"→  {atype.replace('_', ' ').title()}")
                y -= 0.18 * inch
        else:
            c.setFont("Helvetica", 8.5)
            c.setFillColor(_C_GREY)
            c.drawString(_M, y, "No assemblies assigned to this unit type.")

        if tenant:
            self._footer(c, project.name, "—", tenant)
        else:
            self._footer(c, project.name, "—")

    # ── Assembly Drawing Page ─────────────────────────────────────────────────

    def _draw_assembly_page(
        self, c, project: Project,
        group: UnitTypeGroup, assembly_type: str,
        assemblies: List[Assembly], version: str, tenant: Tenant
    ):
        """Phase 17 drawing-first sheet: large canvas + compact fab table."""
        self._page_num += 1
        label = assembly_type.replace("_", " ").title()
        variant = " [MIR]" if group.is_mirror else (" [ADA]" if group.is_ada else "")

        body_top = _H - _HEADER_H - _M * 0.12
        body_bot = _BODY_Y
        table_top = body_bot + _ASM_NOTES_H
        draw_bot = table_top + _ASM_TABLE_H + 6
        strip_y = body_top - _ASM_STRIP_H

        if not assemblies:
            self._page_header(c, project, f"TYPE {group.unit_type_code}  —  {label}{variant}", "")
            c.setFont("Helvetica", 11)
            c.setFillColor(_C_GREY)
            c.drawString(_M, body_top - 0.3 * inch, f"No assemblies of type '{label}' defined.")
            self._footer(c, project.name, version, tenant)
            return

        asm = assemblies[0]
        use_shop = asm.assembly_type.value == "custom" and len(asm.parts) >= 4

        self._draw_assembly_title_strip(
            c, project, group, asm, version, label, variant, strip_y, body_top
        )

        # Drawing zone: leave right gutter for vertical title block
        vtitle_x = _W - _M - _VTITLE_W
        draw_x   = _M
        draw_w   = vtitle_x - _M - 4   # 4pt gap before title block
        draw_h   = strip_y - draw_bot - 8

        c.setFillColor(HexColor("#fafbfc"))
        c.setStrokeColor(HexColor("#cbd5e1"))
        c.setLineWidth(0.6)
        c.rect(draw_x, draw_bot, draw_w, draw_h, fill=1, stroke=1)

        inner_x, inner_y = draw_x + 8, draw_bot + 8
        inner_w, inner_h = draw_w - 16, draw_h - 16

        legend_h = self._engine.draw_granite_quartz_key_notes(
            c, inner_x + inner_w - 142, inner_y + inner_h - 2, w=134
        )

        c.setFillColor(_C_DARK)
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(inner_x + inner_w / 2, inner_y + inner_h - 12, f"QTY={group.unit_count}")

        self._engine.draw_assembly(
            c=c,
            assembly=asm,
            zone_x=inner_x,
            zone_y=inner_y,
            zone_w=inner_w,
            zone_h=max(inner_h - legend_h - 22, 80),
            is_mirror=group.is_mirror,
            shop_sheet_layout=use_shop,
        )

        c.setFont("Helvetica-Oblique", 6)
        c.setFillColor(_C_GREY)
        c.drawString(draw_x, draw_bot - 6, "Scale: NTS  |  Dimensions in inch [mm]")

        # Vertical title block (Virgin Surfaces shop-drawing style)
        self._draw_vertical_title_block(
            c, project, group, asm, version, tenant,
            package_qty=group.unit_count,
            sheet_id=f"{self._page_num}/{self._total_pages}",
            x=vtitle_x,
            y=draw_bot,
            h=draw_h + 8,
        )

        self._draw_compact_fab_table(c, asm, draw_x, table_top, draw_w + _VTITLE_W + 4, _ASM_TABLE_H)
        self._draw_short_notes(c, asm, draw_x, body_bot, draw_w + _VTITLE_W + 4)
        self._footer(c, project.name, version, tenant)

    def _draw_assembly_title_strip(
        self, c, project, group, asm, version, label, variant, strip_y, body_top
    ):
        # Background
        c.setFillColor(HexColor("#1a2332"))
        c.rect(_M, strip_y, _W - 2 * _M, _ASM_STRIP_H, fill=1, stroke=0)

        # Top row: primary identifier fields
        top_y = strip_y + _ASM_STRIP_H * 0.62
        c.setFillColor(_C_WHITE)
        c.setFont("Helvetica-Bold", 10)
        fields = [
            project.name[:24],
            f"TYPE {group.unit_type_code}",
            (project.material or "—")[:18],
            f"QTY {group.unit_count}",
            f"Rev {version}",
            f"Sheet {self._page_num}/{self._total_pages}",
        ]
        x = _M + 10
        for i, txt in enumerate(fields):
            c.drawString(x, top_y, txt)
            x += c.stringWidth(txt, "Helvetica-Bold", 10) + 16
            if i < len(fields) - 1:
                c.setFillColor(_C_MID)
                c.drawString(x - 9, top_y, "|")
                c.setFillColor(_C_WHITE)

        # Bottom row: assembly name + type
        bot_y = strip_y + _ASM_STRIP_H * 0.20
        c.setFillColor(HexColor("#7aadcf"))
        c.setFont("Helvetica", 8)
        c.drawString(_M + 10, bot_y, f"{label}{variant}  ·  {asm.name[:60]}")

    @staticmethod
    def _edge_letter(edge_type: EdgeType) -> str:
        return {
            EdgeType.POLISHED: "P",
            EdgeType.RAW: "R",
            EdgeType.EASED: "E",
            EdgeType.FINISHED: "F",
            EdgeType.MITER: "M",
        }.get(edge_type, "-")

    def _edge_compact(self, part: Part) -> str:
        em = {e.position: e.edge_type for e in part.edges}
        parts = []
        for pos, letter in (
            (Position.BACK, "B"),
            (Position.FRONT, "F"),
            (Position.LEFT, "L"),
            (Position.RIGHT, "R"),
        ):
            et = em.get(pos)
            parts.append(f"{letter}={self._edge_letter(et) if et else '-'}")
        return " ".join(parts)

    def _cutout_compact(self, part: Part) -> str:
        if not part.cutouts:
            return "—"
        co = part.cutouts[0]
        ctype = co.cutout_type.value.replace("_", " ").title()
        return f"{ctype[:8]} {co.dimensions.length:.0f}x{co.dimensions.depth:.0f}"

    def _draw_compact_fab_table(
        self, c, asm: Assembly, x: float, y: float, w: float, h: float
    ):
        c.setFillColor(HexColor("#eef2f7"))
        c.setStrokeColor(HexColor("#94a3b8"))
        c.setLineWidth(0.5)
        c.rect(x, y, w, h, fill=1, stroke=1)

        cols = [("PART", 28), ("SIZE", 118), ("EDGE", 200), ("CUTOUT", 90), ("SQFT", 42)]
        cx = x + 4
        ty = y + h - 12
        c.setFillColor(_C_DARK)
        c.setFont("Helvetica-Bold", 6.5)
        for title, cw in cols:
            c.drawString(cx, ty, title)
            cx += cw

        row_y = ty - 10
        c.setFont("Helvetica", 6)
        for i, part in enumerate(asm.parts[:8]):
            if row_y < y + 6:
                break
            pl = chr(65 + i)
            dims = part.dimensions
            area = dims.length * dims.depth / 144.0
            dim_s = f'{format_dimension_inch_mm(dims.length)} x {format_dimension_inch_mm(dims.depth)}'
            vals = [pl, dim_s, self._edge_compact(part), self._cutout_compact(part), f"{area:.1f}"]
            cx = x + 4
            for (_, cw), val in zip(cols, vals):
                c.drawString(cx, row_y, str(val)[: int(cw / 4.5)])
                cx += cw
            row_y -= 9

    def _draw_short_notes(self, c, asm: Assembly, x: float, y: float, w: float):
        c.setFont("Helvetica", 6)
        c.setFillColor(_C_GREY)
        note = ""
        if asm.notes:
            note = asm.notes[0].content[:120]
        c.drawString(x + 4, y + 8, f"NOTES: {note or 'Verify field dimensions before fabrication.'}")

    def _draw_notes_column(
        self, c, asm: Assembly, top_y: float, avail_h: float
    ) -> float:
        """Render parts table + fabrication notes in right column."""
        y = top_y
        # Column background
        c.setFillColor(_C_NOTE)
        c.setStrokeColor(_C_NOTE_B)
        c.setLineWidth(0.5)
        col_bot = top_y - avail_h
        c.rect(_NOTE_X, col_bot, _NOTE_W, avail_h, fill=1, stroke=1)

        y -= 0.12 * inch
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(_C_DARK)
        c.drawString(_NOTE_X + 5, y, "ASSEMBLY DETAILS")
        y -= 0.22 * inch

        c.setFont("Helvetica", 7.5)
        c.setFillColor(_C_GREY)
        c.drawString(_NOTE_X + 5, y, f"Assembly: {asm.name}")
        y -= 0.17 * inch
        c.drawString(_NOTE_X + 5, y,
                     f"Type: {asm.assembly_type.value.title()}  |  "
                     f"Variant: {asm.variant.value.upper()}")
        y -= 0.22 * inch
        
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(_C_DARK)
        c.drawString(_NOTE_X + 5, y, "FIELD / INSTALLER READINESS")
        y -= 0.17 * inch
        c.setFont("Helvetica", 7)
        c.setFillColor(_C_GREY)
        c.drawString(_NOTE_X + 5, y, "Tag: ASSEMBLE-ON-SITE")
        y -= 0.17 * inch
        c.drawString(_NOTE_X + 5, y, "Loc: Coordinate with Site Super")
        y -= 0.22 * inch

        # Per-part details
        for i, part in enumerate(asm.parts):
            if y < col_bot + 0.3 * inch:
                break
            pl = chr(65 + i)
            dims = part.dimensions
            area = dims.length * dims.depth / 144

            # Part header
            c.setFillColor(_C_DARK)
            c.rect(_NOTE_X + 3, y - 14, _NOTE_W - 6, 14, fill=1, stroke=0)
            c.setFillColor(_C_WHITE)
            c.setFont("Helvetica-Bold", 7.5)
            c.drawString(_NOTE_X + 6, y - 11,
                         f"PART {pl} — {part.name[:28]}")
            y -= 17

            c.setFillColor(_C_DARK)
            c.setFont("Helvetica", 7)
            dim_l = format_dimension_inch_mm(dims.length)
            dim_d = format_dimension_inch_mm(dims.depth)
            c.drawString(
                _NOTE_X + 6,
                y,
                f"  {dim_l} × {dim_d}"
                + (f" × {dims.thickness}\"" if dims.thickness else "")
                + f"  =  {area:.2f} sq ft",
            )
            y -= 12

            # Tables
            if part.edges:
                c.setFont("Helvetica-Bold", 6.5)
                c.setFillColor(_C_DARK)
                c.drawString(_NOTE_X + 8, y, "EDGE SCHEDULE:")
                y -= 9
                for e in part.edges:
                    etype = e.edge_type.value.replace("_", " ").title()
                    epos  = e.position.value.upper()
                    c.setFont("Helvetica", 6.5)
                    c.drawString(_NOTE_X + 12, y, f"· {epos}: {etype}")
                    y -= 9

            if part.cutouts:
                c.setFont("Helvetica-Bold", 6.5)
                c.setFillColor(_C_DARK)
                c.drawString(_NOTE_X + 8, y, "CUTOUT SCHEDULE:")
                y -= 9
                for co in part.cutouts:
                    ctype = co.cutout_type.value.replace("_", " ").title()
                    mount = co.mount_type.value.replace("_", " ").title()
                    c.setFont("Helvetica", 6.5)
                    c.drawString(_NOTE_X + 12, y, f"· {ctype} ({mount}) — {co.dimensions.length}\"×{co.dimensions.depth}\" @ X:{co.center_x}\", Y:{co.center_y}\"")
                    y -= 9

            if part.holes:
                c.setFont("Helvetica-Bold", 6.5)
                c.setFillColor(_C_DARK)
                c.drawString(_NOTE_X + 8, y, "HOLE SCHEDULE:")
                y -= 9
                for h in part.holes:
                    c.setFont("Helvetica", 6.5)
                    c.drawString(_NOTE_X + 12, y, f"· {h.purpose}: Ø{h.diameter}\" @ X:{h.center_x}\", Y:{h.center_y}\"")
                    y -= 9

            if part.splashes:
                c.setFont("Helvetica-Bold", 6.5)
                c.setFillColor(_C_DARK)
                c.drawString(_NOTE_X + 8, y, "SPLASH SCHEDULE:")
                y -= 9
                for sp in part.splashes:
                    st = sp.splash_type.value.replace("_", " ").title()
                    c.setFont("Helvetica", 6.5)
                    c.drawString(_NOTE_X + 12, y, f"· {st} — {sp.dimensions.length}\"×{sp.dimensions.depth}\"")
                    y -= 9

            if part.notes:
                c.setFillColor(_C_RED)
                c.setFont("Helvetica-Bold", 6.5)
                c.drawString(_NOTE_X + 8, y, f"Note: {part.notes[:70]}")
                c.setFillColor(_C_DARK)
                y -= 11
            y -= 5

        # Fabrication notes box
        if asm.notes and y > col_bot + 0.5 * inch:
            y -= 5
            c.setFillColor(_C_RED)
            c.setFont("Helvetica-Bold", 7.5)
            c.drawString(_NOTE_X + 5, y, "FABRICATION NOTES:")
            y -= 12
            for note in asm.notes:
                if y < col_bot + 0.2 * inch:
                    break
                # Note box
                c.setStrokeColor(_C_RED)
                c.setFillColor(HexColor("#fff0f0"))
                c.setLineWidth(0.5)
                txt = note.content[:80]
                # Wrap
                lines = self._wrap_text(txt, 38)
                box_h = len(lines) * 10 + 6
                c.rect(_NOTE_X + 3, y - box_h, _NOTE_W - 6, box_h, fill=1, stroke=1)
                c.setFillColor(_C_RED)
                c.setFont("Helvetica", 6.5)
                ly = y - 9
                for ln in lines:
                    c.drawString(_NOTE_X + 6, ly, ln)
                    ly -= 10
                y -= box_h + 4

        return y

    # ── Summary ───────────────────────────────────────────────────────────────

    def _draw_summary(self, c, project: Project, summary: PackageSummary, version: str, tenant: Tenant):
        self._page_num += 1
        self._page_header(c, project, "PROJECT SUMMARY", version)
        y = _H - _HEADER_H - _M * 0.5

        # Key stats band
        bh = 0.72 * inch
        c.setFillColor(_C_ACCENT)
        c.rect(_M, y - bh, _W - 2 * _M, bh, fill=1, stroke=0)
        c.setStrokeColor(HexColor("#c8d8ea"))
        c.setLineWidth(0.5)
        c.rect(_M, y - bh, _W - 2 * _M, bh, fill=0, stroke=1)

        totals = [
            ("UNITS",       str(summary.total_units)),
            ("ASSEMBLIES",  str(summary.total_assemblies)),
            ("PARTS",       str(summary.total_parts)),
            ("SQ FT",       f"{summary.total_area_sqft:.2f}"),
            ("SQ IN",       f"{summary.total_area_sqin:.0f}"),
        ]
        cw = (_W - 2 * _M) / len(totals)
        for i, (lbl, val) in enumerate(totals):
            cx = _M + i * cw + cw / 2
            if i > 0:
                c.setStrokeColor(HexColor("#c8d8ea"))
                c.setLineWidth(0.4)
                c.line(_M + i * cw, y - bh + 10, _M + i * cw, y - 10)
            c.setFont("Helvetica-Bold", 20)
            c.setFillColor(_C_DARK)
            c.drawCentredString(cx, y - bh * 0.48, val)
            c.setFont("Helvetica", 6.5)
            c.setFillColor(_C_GREY)
            c.drawCentredString(cx, y - bh + 11, lbl)

        y -= bh + 0.28 * inch

        # Three breakdown tables side-by-side
        col_w = (_W - 2 * _M) / 3 - 0.08 * inch
        col_gap = 0.12 * inch

        breakdown_cols = [
            ("ASSEMBLY BREAKDOWN",   sorted(summary.assembly_counts.items()),   "Assembly Type",  "Count"),
            ("UNIT TYPE BREAKDOWN",  sorted(summary.unit_type_counts.items()),   "Unit Type",      "Count"),
            ("PART TYPE BREAKDOWN",  sorted(summary.part_counts_by_type.items()), "Part Type",    "Count"),
        ]

        for ci, (heading, rows, col1_hdr, col2_hdr) in enumerate(breakdown_cols):
            cx = _M + ci * (col_w + col_gap)
            th = 0.24 * inch

            # Table header
            c.setFillColor(_C_DARK)
            c.rect(cx, y - th, col_w, th, fill=1, stroke=0)
            c.setFillColor(_C_WHITE)
            c.setFont("Helvetica-Bold", 8)
            c.drawString(cx + 5, y - th + 8, heading)

            # Column sub-headers
            row_h = 0.185 * inch
            sub_y = y - th - row_h
            c.setFillColor(HexColor("#eef2f7"))
            c.rect(cx, sub_y, col_w, row_h, fill=1, stroke=0)
            c.setFillColor(_C_DARK)
            c.setFont("Helvetica-Bold", 7)
            c.drawString(cx + 5, sub_y + 5, col1_hdr)
            c.drawRightString(cx + col_w - 5, sub_y + 5, col2_hdr)

            # Data rows
            ry = sub_y - row_h
            for i, (k, v) in enumerate(rows):
                label = k.replace("_", " ").title()
                if label.lower().startswith("type ") is False and ci == 1:
                    label = f"Type {k}"
                bg = HexColor("#fafbfc") if i % 2 == 0 else _C_WHITE
                c.setFillColor(bg)
                c.rect(cx, ry, col_w, row_h, fill=1, stroke=0)
                c.setStrokeColor(HexColor("#e2e8f0"))
                c.setLineWidth(0.3)
                c.line(cx, ry, cx + col_w, ry)
                c.setFillColor(_C_DARK)
                c.setFont("Helvetica", 7.5)
                c.drawString(cx + 5, ry + 5, label[:32])
                c.setFont("Helvetica-Bold", 7.5)
                c.drawRightString(cx + col_w - 5, ry + 5, str(v))
                ry -= row_h
                if ry < _M + 0.5 * inch:
                    break

            # Outer border
            table_h = y - th - ry
            c.setStrokeColor(HexColor("#94a3b8"))
            c.setLineWidth(0.5)
            c.rect(cx, ry, col_w, table_h, fill=0, stroke=1)

        self._footer(c, project.name, version, tenant)

    # ── Shared helpers ────────────────────────────────────────────────────────

    def _page_header(self, c, project: Project, title: str, subtitle: str):
        c.setFillColor(_C_DARK)
        c.rect(0, _H - _HEADER_H, _W, _HEADER_H, fill=1, stroke=0)
        c.setFillColor(_C_WHITE)
        c.setFont("Helvetica-Bold", 13)
        c.drawString(_M, _H - 0.38 * inch, title)
        c.setFont("Helvetica", 8)
        c.setFillColor(_C_MID)
        c.drawString(_M, _H - 0.6 * inch, project.name)
        if subtitle:
            c.setFont("Helvetica-Bold", 10)
            c.setFillColor(_C_WHITE)
            c.drawRightString(_W - _M, _H - 0.48 * inch, subtitle)
        # Sheet counter
        c.setFont("Helvetica", 7)
        c.setFillColor(_C_MID)
        c.drawRightString(_W - _M, _H - 0.7 * inch,
                          f"Sheet {self._page_num} of {self._total_pages}")
        # Divider
        c.setStrokeColor(_C_MID)
        c.setLineWidth(0.5)
        c.line(_M, _H - _HEADER_H + 1, _W - _M, _H - _HEADER_H + 1)

    def _footer(self, c, project_name: str, version: str, tenant: Tenant = None):
        c.setStrokeColor(HexColor("#cccccc"))
        c.setLineWidth(0.5)
        c.line(_M, _M + 0.2 * inch, _W - _M, _M + 0.2 * inch)
        c.setFont("Helvetica", 6.5)
        c.setFillColor(_C_GREY)
        
        co_name = "BuildDesk"
        footer_text = "CONFIDENTIAL AND PROPRIETARY"
        if tenant:
            if tenant.company_name:
                co_name = tenant.company_name
            if tenant.default_footer:
                footer_text = tenant.default_footer
        
        c.drawString(_M, _M + 0.05 * inch,
                     f"{co_name}  ·  {project_name}  ·  {footer_text}")
        if version:
            c.drawRightString(_W - _M, _M + 0.05 * inch, f"Rev: {version}")
        c.drawCentredString(_W / 2, _M + 0.05 * inch,
                            f"Page {self._page_num} of {self._total_pages}")

    def _badge(self, c, x: float, y: float, text: str, color: HexColor):
        w = c.stringWidth(text, "Helvetica-Bold", 8) + 14
        c.setFillColor(color)
        c.roundRect(x, y - 0.04 * inch, w, 0.22 * inch, 3, fill=1, stroke=0)
        c.setFillColor(_C_WHITE)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(x + 7, y + 0.04 * inch, text)

    def _draw_vertical_title_block(
        self,
        c,
        project: Project,
        group: UnitTypeGroup,
        asm: Assembly,
        version: str,
        tenant: Tenant,
        *,
        package_qty: int,
        sheet_id: str,
        x: float,
        y: float,
        h: float,
    ) -> None:
        """Virgin-style vertical title strip on the right margin of drawing pages."""
        w = 0.82 * inch
        c.setFillColor(HexColor("#f4f6f8"))
        c.setStrokeColor(HexColor("#999999"))
        c.setLineWidth(0.75)
        c.rect(x, y, w, h, fill=1, stroke=1)

        cx = x + w / 2
        material = project.material or "3CM GRANITE"
        co = (tenant.company_name or "Virgin Surfaces").upper()[:28]

        c.saveState()
        c.translate(cx, y + h - 14)
        c.rotate(90)
        c.setFillColor(_C_DARK)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(0, 0, co)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(0, -12, material[:36])
        c.drawString(0, -24, (project.client_name or project.name)[:40])
        c.drawString(0, -36, f"TYPE {group.unit_type_code}  ·  QTY={package_qty}")
        c.setFont("Helvetica", 6)
        c.drawString(0, -50, f"Sheet {sheet_id}  ·  Rev {version}")
        if project.issue_date:
            c.drawString(0, -62, project.issue_date.strftime("%m/%d/%Y"))
        c.setFont("Helvetica-Bold", 7)
        c.drawString(0, -78, "ITEM # 16360")
        c.setFont("Helvetica", 5.5)
        c.drawString(0, -92, asm.name[:44])
        c.restoreState()

        c.setFillColor(_C_DARK)
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(cx, y + 10, sheet_id[:12])

    def _wrap_text(self, text: str, max_chars: int) -> List[str]:
        words = text.split()
        lines, line = [], ""
        for w in words:
            if len(line) + len(w) + 1 <= max_chars:
                line = (line + " " + w).strip()
            else:
                if line:
                    lines.append(line)
                line = w
        if line:
            lines.append(line)
        return lines or [""]
