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

# Phase 17 — drawing-first assembly sheets (full width)
_ASM_STRIP_H = 0.30 * inch
_ASM_TABLE_H = 0.95 * inch
_ASM_NOTES_H = 0.24 * inch

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

        # Metadata table (left column)
        meta = [
            ("Project",     project.name),
            ("Client",      project.client_name or "—"),
            ("Material",    project.material    or "—"),
            ("Address",     project.address     or "—"),
            ("Issue Date",  project.issue_date.strftime("%B %d, %Y") if project.issue_date else package.generated_at.strftime("%B %d, %Y") if package.generated_at else "—"),
            ("Proj Status", project.status.value.replace("_", " ").title()),
            ("Pkg Status",  package.status.value.replace("_", " ").upper()),
            ("Prepared By", getattr(package, "issued_by", None) or "—"),
        ]
        if package.revision_notes:
            meta.append(("Rev Notes", package.revision_notes))
            
        if getattr(package, "approved_by", None):
            meta.append(("Approved By", package.approved_by))
            if getattr(package, "approved_at", None):
                meta.append(("Approved At", package.approved_at.strftime("%B %d, %Y")))
            
        y = _H - 2.45 * inch
        for label, value in meta:
            c.setFont("Helvetica-Bold", 9)
            c.setFillColor(_C_DARK)
            c.drawString(_M, y, f"{label}:")
            c.setFont("Helvetica", 9)
            c.drawString(_M + 1.05 * inch, y, str(value)[:100])
            y -= 0.27 * inch

        # Stats band
        y -= 0.1 * inch
        bh = 0.58 * inch
        c.setFillColor(_C_ACCENT)
        c.rect(_M, y - bh, _W - 2 * _M, bh, fill=1, stroke=0)
        stats = [
            ("Total Units",       str(summary.total_units)),
            ("Total Assemblies",  str(summary.total_assemblies)),
            ("Total Parts",       str(summary.total_parts)),
            ("Total Sq Ft",       f"{summary.total_area_sqft:.1f}"),
            ("Unit Types",        str(len(summary.unit_type_counts))),
            ("Total Sheets",      str(self._total_pages)),
        ]
        cw = (_W - 2 * _M) / len(stats)
        for i, (lbl, val) in enumerate(stats):
            cx = _M + i * cw + cw / 2
            c.setFont("Helvetica-Bold", 13)
            c.setFillColor(_C_DARK)
            c.drawCentredString(cx, y - bh * 0.45, val)
            c.setFont("Helvetica", 7)
            c.setFillColor(_C_GREY)
            c.drawCentredString(cx, y - bh * 0.78, lbl)

        # Standard fabrication notes
        notes_y = y - bh - 0.5 * inch
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(_C_DARK)
        c.drawString(_M, notes_y, "STANDARD FABRICATION & INSTALLATION NOTES:")
        c.setFont("Helvetica", 8)
        c.setFillColor(_C_GREY)
        std_notes = tenant.standard_notes.split("\n") if tenant.standard_notes else [
            "1. Field verify all dimensions prior to fabrication.",
            "2. Ensure all substrate surfaces are level and capable of supporting countertop weight.",
            "3. Seam locations shown are suggested; actual locations to be determined by fabricator based on slab sizes.",
            "4. All exposed edges to be polished unless otherwise noted.",
            "5. Sink/cooktop cutouts must be verified against actual appliance/fixture templates.",
            "6. Support brackets required for overhangs exceeding 10 inches."
        ]
        ny = notes_y - 0.25 * inch
        for note in std_notes:
            if note.strip():
                c.drawString(_M + 0.1 * inch, ny, note.strip())
                ny -= 0.2 * inch

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

        # Stats row
        total_sqft = sum(
            p.dimensions.length * p.dimensions.depth / 144.0
            for a in assemblies for p in a.parts
        )
        part_count = sum(len(a.parts) for a in assemblies)
        c.setFont("Helvetica", 9)
        c.setFillColor(_C_GREY)
        c.drawString(_M, y,
                     f"Assemblies: {len(assemblies)}  ·  "
                     f"Parts (pieces): {part_count}  ·  "
                     f"Stone area: {total_sqft:.1f} sq ft")
        y -= 0.3 * inch

        # Unit list
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(_C_DARK)
        c.drawString(_M, y, f"Units ({group.unit_count}):")
        y -= 0.22 * inch
        max_w = _W - 2 * _M
        line = ""
        for code in group.unit_codes:
            test = line + ("" if not line else ",  ") + code
            if c.stringWidth(test, "Helvetica", 8) < max_w:
                line = test
            else:
                c.setFont("Helvetica", 8)
                c.setFillColor(_C_GREY)
                c.drawString(_M + 6, y, line + ",")
                y -= 0.18 * inch
                line = code
        if line:
            c.setFont("Helvetica", 8)
            c.setFillColor(_C_GREY)
            c.drawString(_M + 6, y, line)
            y -= 0.25 * inch

        # Assembly types
        y -= 0.08 * inch
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(_C_DARK)
        c.drawString(_M, y, "Assembly Types:")
        y -= 0.22 * inch
        for atype in group.assembly_types:
            c.setFont("Helvetica", 9)
            c.drawString(_M + 8, y, f"·  {atype.replace('_', ' ').title()}")
            y -= 0.2 * inch
        if not group.assembly_types:
            c.setFont("Helvetica", 9)
            c.setFillColor(_C_GREY)
            c.drawString(_M + 8, y, "No assemblies assigned yet.")

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

        draw_x = _M
        draw_w = _W - 2 * _M
        draw_h = strip_y - draw_bot - 8

        c.setFillColor(HexColor("#fafbfc"))
        c.setStrokeColor(HexColor("#cbd5e1"))
        c.setLineWidth(0.6)
        c.rect(draw_x, draw_bot, draw_w, draw_h, fill=1, stroke=1)

        inner_x, inner_y = draw_x + 8, draw_bot + 8
        inner_w, inner_h = draw_w - 16, draw_h - 16

        legend_h = self._engine.draw_granite_quartz_key_notes(
            c, inner_x + inner_w - 148, inner_y + inner_h - 2, w=140
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

        self._draw_compact_fab_table(c, asm, draw_x, table_top, draw_w, _ASM_TABLE_H)
        self._draw_short_notes(c, asm, draw_x, body_bot, draw_w)
        self._footer(c, project.name, version, tenant)

    def _draw_assembly_title_strip(
        self, c, project, group, asm, version, label, variant, strip_y, body_top
    ):
        c.setFillColor(HexColor("#1a2332"))
        c.rect(_M, strip_y, _W - 2 * _M, _ASM_STRIP_H, fill=1, stroke=0)
        c.setFillColor(_C_WHITE)
        c.setFont("Helvetica-Bold", 8)
        fields = [
            project.name[:22],
            f"TYPE {group.unit_type_code}",
            (project.material or "—")[:16],
            f"QTY {group.unit_count}",
            f"Rev {version}",
            f"Sheet {self._page_num}/{self._total_pages}",
        ]
        x = _M + 8
        for i, txt in enumerate(fields):
            c.drawString(x, strip_y + 9, txt)
            x += c.stringWidth(txt, "Helvetica-Bold", 8) + 14
            if i < len(fields) - 1:
                c.setFillColor(_C_MID)
                c.drawString(x - 7, strip_y + 9, "|")
                c.setFillColor(_C_WHITE)
        c.setFont("Helvetica", 7)
        c.drawString(_M + 8, strip_y - 2, f"{label}{variant}  ·  {asm.name[:50]}")

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

        # Stats grid
        bh = 0.62 * inch
        c.setFillColor(_C_ACCENT)
        c.rect(_M, y - bh, _W - 2 * _M, bh, fill=1, stroke=0)
        totals = [
            ("Total Units",       str(summary.total_units)),
            ("Total Assemblies",  str(summary.total_assemblies)),
            ("Total Parts",       str(summary.total_parts)),
            ("Stone Area (sq ft)", f"{summary.total_area_sqft:.2f}"),
            ("Stone Area (sq in)", f"{summary.total_area_sqin:.0f}"),
        ]
        cw = (_W - 2 * _M) / len(totals)
        for i, (lbl, val) in enumerate(totals):
            cx = _M + i * cw + cw / 2
            c.setFont("Helvetica-Bold", 17)
            c.setFillColor(_C_DARK)
            c.drawCentredString(cx, y - bh * 0.44, val)
            c.setFont("Helvetica", 7)
            c.setFillColor(_C_GREY)
            c.drawCentredString(cx, y - bh * 0.77, lbl)
        y -= bh + 0.18 * inch

        # Three columns: assembly types | unit types | part types
        col_w = (_W - 2 * _M) / 3
        cols = [
            ("Assembly Breakdown",
             [(k.replace("_", " ").title(), v)
              for k, v in sorted(summary.assembly_counts.items())]),
            ("Unit Type Breakdown",
             [(f"Type {k}", v) for k, v in sorted(summary.unit_type_counts.items())]),
            ("Part Type Breakdown",
             [(k.replace("_", " ").title(), v)
              for k, v in sorted(summary.part_counts_by_type.items())]),
        ]
        for ci, (heading, rows) in enumerate(cols):
            cx = _M + ci * col_w
            c.setFont("Helvetica-Bold", 9)
            c.setFillColor(_C_DARK)
            c.drawString(cx, y, heading)
            ry = y - 0.2 * inch
            for label, cnt in rows:
                c.setFont("Helvetica", 8)
                c.drawString(cx + 5, ry, f"·  {label}: {cnt}")
                ry -= 0.18 * inch

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
