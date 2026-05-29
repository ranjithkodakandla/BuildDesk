"""
Package PDF Exporter  (Phase 3)
=================================
Generates the full multi-page fabrication package PDF using ReportLab.

Page structure:
    Page 1:   Cover      — project name, client, material, address, issue date, version
    Pages 2+: Type Sheet — per UnitType: code, qty, unit list, assembly types
    Pages N+: Assembly Drawing — per assembly type per unit type: parts, dims, cutouts, holes
    Last:     Summary    — piece counts, assembly counts, sq ft totals

Reuse analysis:
    KEEP:  geometry/primitives.py     (Point, Rectangle, etc. — used for part drawing)
    WRAP:  exporters/pdf_exporter.py  (PdfExporter used for single-part geometry rendering)
    NEW:   PackagePdfExporter         (multi-page, project-level orchestration)
"""

from __future__ import annotations

import io
from datetime import datetime
from typing import Dict, List, Optional

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from app.models.hierarchy import Project, UnitType
from app.models.fabrication import Assembly, Part, AssemblyType
from app.models.project_package import PackageSummary, UnitTypeGroup


# ---------------------------------------------------------------------------
# Colour palette — print-safe, professional
# ---------------------------------------------------------------------------
_C_DARK   = HexColor("#1a2332")   # navy  — headings, borders
_C_MID    = HexColor("#4a7fb5")   # blue  — subheadings, dimension lines
_C_LIGHT  = HexColor("#f0f4f8")   # light — part fill
_C_WHITE  = HexColor("#ffffff")
_C_GREY   = HexColor("#888888")   # meta text
_C_RED    = HexColor("#c0392b")   # critical notes
_C_GREEN  = HexColor("#27ae60")   # ADA / special variant indicator
_C_ACCENT = HexColor("#e8f4fd")   # type sheet background

_PAGE  = landscape(letter)        # 11 × 8.5 in → 792 × 612 pts
_W, _H = _PAGE
_M     = 0.45 * inch              # margin


class PackagePdfExporter:
    """
    Produces a complete multi-page fabrication PDF for one project.

    Usage:
        exporter = PackagePdfExporter()
        pdf_bytes = exporter.export(
            project=project,
            unit_type_groups=groups,
            assemblies_by_type=assemblies_map,
            summary=summary,
            version="1.0",
        )
    """

    def export(
        self,
        project: Project,
        unit_type_groups: List[UnitTypeGroup],
        assemblies_by_type: Dict[str, List[Assembly]],  # unit_type_id::assembly_type → [Assembly]
        summary: PackageSummary,
        version: str = "1.0",
    ) -> bytes:
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=_PAGE)
        c.setTitle(f"BuildDesk — {project.name} — {version}")

        # Page 1: Cover
        self._draw_cover(c, project, version, summary)
        c.showPage()

        # Pages 2+: Type Sheets + Assembly Drawing Pages
        for group in unit_type_groups:
            self._draw_type_sheet(c, project, group)
            c.showPage()

            for atype in group.assembly_types:
                key = f"{group.unit_type_id}::{atype}"
                assemblies = assemblies_by_type.get(key, [])
                self._draw_assembly_page(c, project, group, atype, assemblies)
                c.showPage()

        # Last page: Summary
        self._draw_summary(c, project, summary, version)
        c.showPage()

        c.save()
        return buf.getvalue()

    # ------------------------------------------------------------------
    # Cover Page
    # ------------------------------------------------------------------

    def _draw_cover(self, c: canvas.Canvas, project: Project, version: str, summary: PackageSummary):
        # Full dark header band
        c.setFillColor(_C_DARK)
        c.rect(0, _H - 2.2 * inch, _W, 2.2 * inch, fill=1, stroke=0)

        # Company / app name
        c.setFillColor(_C_MID)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(_M, _H - _M - 6, "BUILDDESK  ·  FABRICATION PACKAGE")

        # Project name
        c.setFillColor(_C_WHITE)
        c.setFont("Helvetica-Bold", 28)
        c.drawString(_M, _H - 1.1 * inch, project.name)

        # Version badge (top-right)
        c.setFillColor(_C_MID)
        c.roundRect(_W - 1.6 * inch, _H - 0.75 * inch, 1.2 * inch, 0.38 * inch, 4, fill=1, stroke=0)
        c.setFillColor(_C_WHITE)
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(_W - inch, _H - 0.52 * inch, version)

        # Metadata block
        y = _H - 2.6 * inch
        meta = [
            ("Client",    project.client_name or "—"),
            ("Material",  project.material    or "—"),
            ("Address",   project.address     or "—"),
            ("Issue Date",
             project.issue_date.strftime("%B %d, %Y") if project.issue_date else "—"),
            ("Status",    project.status.value.replace("_", " ").title()),
        ]
        for label, value in meta:
            c.setFont("Helvetica-Bold", 10)
            c.setFillColor(_C_DARK)
            c.drawString(_M, y, f"{label}:")
            c.setFont("Helvetica", 10)
            c.drawString(_M + 1.1 * inch, y, value)
            y -= 0.3 * inch

        # Stats band
        y -= 0.15 * inch
        c.setFillColor(_C_ACCENT)
        c.rect(_M, y - 0.6 * inch, _W - 2 * _M, 0.6 * inch, fill=1, stroke=0)
        c.setFillColor(_C_DARK)
        c.setFont("Helvetica-Bold", 10)
        stats = [
            ("Total Units",      str(summary.total_units)),
            ("Total Assemblies", str(summary.total_assemblies)),
            ("Total Parts",      str(summary.total_parts)),
            ("Total Sq Ft",      f"{summary.total_area_sqft:.1f}"),
            ("Unit Types",       str(len(summary.unit_type_counts))),
        ]
        col_w = (_W - 2 * _M) / len(stats)
        for i, (lbl, val) in enumerate(stats):
            cx = _M + i * col_w + col_w / 2
            c.setFont("Helvetica-Bold", 14)
            c.drawCentredString(cx, y - 0.28 * inch, val)
            c.setFont("Helvetica", 8)
            c.setFillColor(_C_GREY)
            c.drawCentredString(cx, y - 0.48 * inch, lbl)
            c.setFillColor(_C_DARK)

        # Footer
        self._footer(c, 1, project.name, version)

    # ------------------------------------------------------------------
    # Type Sheet
    # ------------------------------------------------------------------

    def _draw_type_sheet(self, c: canvas.Canvas, project: Project, group: UnitTypeGroup):
        self._page_header(c, project,
                          f"TYPE  {group.unit_type_code}",
                          f"Qty: {group.unit_count}")

        y = _H - 1.35 * inch

        # Variant badges
        badge_x = _M
        if group.is_mirror:
            self._badge(c, badge_x, y, "MIRROR", _C_MID)
            badge_x += 0.85 * inch
        if group.is_ada:
            self._badge(c, badge_x, y, "ADA", _C_GREEN)
            badge_x += 0.7 * inch
        y -= 0.45 * inch

        # Full type name
        c.setFont("Helvetica-Bold", 13)
        c.setFillColor(_C_DARK)
        c.drawString(_M, y, group.unit_type_name)
        y -= 0.35 * inch

        # Unit codes list
        c.setFont("Helvetica-Bold", 10)
        c.drawString(_M, y, f"Units ({group.unit_count}):")
        y -= 0.25 * inch
        codes_text = ",  ".join(group.unit_codes)
        c.setFont("Helvetica", 9)
        c.setFillColor(_C_GREY)
        # Wrap long unit lists
        max_w = _W - 2 * _M
        words = codes_text.split(",  ")
        line = ""
        for word in words:
            test = line + ("" if not line else ",  ") + word
            if c.stringWidth(test, "Helvetica", 9) < max_w:
                line = test
            else:
                c.drawString(_M + 0.1 * inch, y, line + ",")
                y -= 0.2 * inch
                line = word
        if line:
            c.drawString(_M + 0.1 * inch, y, line)
            y -= 0.3 * inch

        # Assembly types in this unit type
        y -= 0.1 * inch
        c.setFillColor(_C_DARK)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(_M, y, "Assembly Types in this Unit Type:")
        y -= 0.25 * inch
        for atype in group.assembly_types:
            label = atype.replace("_", " ").title()
            c.setFont("Helvetica", 10)
            c.drawString(_M + 0.2 * inch, y, f"·  {label}")
            y -= 0.22 * inch
        if not group.assembly_types:
            c.setFont("Helvetica", 10)
            c.setFillColor(_C_GREY)
            c.drawString(_M + 0.2 * inch, y, "No assemblies assigned yet.")
            y -= 0.22 * inch

        self._footer(c, None, project.name, "")

    # ------------------------------------------------------------------
    # Assembly Drawing Page
    # ------------------------------------------------------------------

    def _draw_assembly_page(
        self,
        c: canvas.Canvas,
        project: Project,
        group: UnitTypeGroup,
        assembly_type: str,
        assemblies: List[Assembly],
    ):
        label = assembly_type.replace("_", " ").title()
        variant_note = " [MIRROR]" if group.is_mirror else (" [ADA]" if group.is_ada else "")
        self._page_header(
            c, project,
            f"TYPE  {group.unit_type_code}  —  {label}{variant_note}",
            f"Qty: {group.unit_count}"
        )

        y = _H - 1.35 * inch

        if not assemblies:
            c.setFont("Helvetica", 11)
            c.setFillColor(_C_GREY)
            c.drawString(_M, y, f"No assemblies of type '{label}' found for this unit type.")
            self._footer(c, None, project.name, "")
            return

        # Use first matching assembly as the representative drawing
        asm = assemblies[0]

        # Draw parts
        draw_y = y
        for i, part in enumerate(asm.parts):
            if draw_y < _M + 1.0 * inch:
                break
            draw_y = self._draw_part_block(c, part, i, draw_y)
            draw_y -= 0.15 * inch

        # Fabrication notes
        if asm.notes:
            draw_y -= 0.1 * inch
            c.setFont("Helvetica-Bold", 9)
            c.setFillColor(_C_DARK)
            c.drawString(_M, draw_y, "Fabrication Notes:")
            draw_y -= 0.2 * inch
            for note in asm.notes:
                c.setFont("Helvetica", 9)
                c.setFillColor(_C_RED)
                c.drawString(_M + 0.15 * inch, draw_y, f"! {note.content}")
                draw_y -= 0.18 * inch

        self._footer(c, None, project.name, "")

    def _draw_part_block(self, c: canvas.Canvas, part: Part, idx: int, y: float) -> float:
        """Draw one part's data block. Returns new y position after drawing."""
        part_label = chr(65 + idx)  # A, B, C, ...
        dims = part.dimensions

        # Part header band
        c.setFillColor(_C_DARK)
        c.rect(_M, y - 0.28 * inch, _W - 2 * _M, 0.28 * inch, fill=1, stroke=0)
        c.setFillColor(_C_WHITE)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(_M + 0.1 * inch, y - 0.19 * inch,
                     f"PART {part_label}  —  {part.name}  |  "
                     f"{dims.length}\" × {dims.depth}\""
                     + (f" × {dims.thickness}\"" if dims.thickness else "")
                     + f"  (Area: {dims.length * dims.depth / 144:.2f} sq ft)")
        y -= 0.32 * inch

        # Edges
        if part.edges:
            c.setFont("Helvetica-Bold", 8)
            c.setFillColor(_C_MID)
            c.drawString(_M + 0.1 * inch, y, "Edges:")
            edge_str = "  ".join(
                f"{e.position.value.upper()}: {e.edge_type.value.replace('_', ' ').title()}"
                for e in part.edges
            )
            c.setFont("Helvetica", 8)
            c.setFillColor(_C_DARK)
            c.drawString(_M + 0.65 * inch, y, edge_str)
            y -= 0.18 * inch

        # Cutouts
        for co in part.cutouts:
            c.setFont("Helvetica", 8)
            c.setFillColor(_C_DARK)
            cotype = co.cutout_type.value.replace("_", " ").title()
            mount = co.mount_type.value.replace("_", " ").title()
            c.drawString(_M + 0.1 * inch, y,
                         f"  ✂ Cutout [{cotype} / {mount}]:  "
                         f"{co.dimensions.length}\" × {co.dimensions.depth}\"  "
                         f"@ ({co.center_x}\", {co.center_y}\")")
            y -= 0.17 * inch

        # Holes
        for hole in part.holes:
            c.setFont("Helvetica", 8)
            c.drawString(_M + 0.1 * inch, y,
                         f"  ○ Hole [{hole.purpose}]:  Ø {hole.diameter}\"  "
                         f"@ ({hole.center_x}\", {hole.center_y}\")")
            y -= 0.17 * inch

        # Splashes
        for sp in part.splashes:
            c.setFont("Helvetica", 8)
            sptype = sp.splash_type.value.replace("_", " ").title()
            c.drawString(_M + 0.1 * inch, y,
                         f"  ▬ Splash [{sptype}]:  "
                         f"{sp.dimensions.length}\" × {sp.dimensions.depth}\"")
            y -= 0.17 * inch

        # Part notes
        if part.notes:
            c.setFont("Helvetica-Oblique", 8)
            c.setFillColor(_C_GREY)
            c.drawString(_M + 0.1 * inch, y, f"  Note: {part.notes}")
            y -= 0.17 * inch

        return y

    # ------------------------------------------------------------------
    # Summary Page
    # ------------------------------------------------------------------

    def _draw_summary(
        self, c: canvas.Canvas, project: Project, summary: PackageSummary, version: str
    ):
        self._page_header(c, project, "PROJECT SUMMARY", version)
        y = _H - 1.4 * inch

        # Totals grid
        totals = [
            ("Total Units",       str(summary.total_units)),
            ("Total Assemblies",  str(summary.total_assemblies)),
            ("Total Parts",       str(summary.total_parts)),
            ("Total Area (sq ft)", f"{summary.total_area_sqft:.2f}"),
            ("Total Area (sq in)", f"{summary.total_area_sqin:.0f}"),
        ]
        col_w = (_W - 2 * _M) / len(totals)
        c.setFillColor(_C_ACCENT)
        c.rect(_M, y - 0.65 * inch, _W - 2 * _M, 0.65 * inch, fill=1, stroke=0)
        for i, (lbl, val) in enumerate(totals):
            cx = _M + i * col_w + col_w / 2
            c.setFillColor(_C_DARK)
            c.setFont("Helvetica-Bold", 18)
            c.drawCentredString(cx, y - 0.32 * inch, val)
            c.setFont("Helvetica", 8)
            c.setFillColor(_C_GREY)
            c.drawCentredString(cx, y - 0.52 * inch, lbl)
        y -= 0.85 * inch

        # Assembly breakdown
        if summary.assembly_counts:
            c.setFont("Helvetica-Bold", 10)
            c.setFillColor(_C_DARK)
            c.drawString(_M, y, "Assembly Breakdown:")
            y -= 0.22 * inch
            for atype, cnt in sorted(summary.assembly_counts.items()):
                c.setFont("Helvetica", 9)
                label = atype.replace("_", " ").title()
                c.drawString(_M + 0.2 * inch, y, f"·  {label}: {cnt}")
                y -= 0.18 * inch
            y -= 0.1 * inch

        # Unit type breakdown
        if summary.unit_type_counts:
            c.setFont("Helvetica-Bold", 10)
            c.setFillColor(_C_DARK)
            c.drawString(_M, y, "Unit Type Breakdown:")
            y -= 0.22 * inch
            for code, cnt in sorted(summary.unit_type_counts.items()):
                c.setFont("Helvetica", 9)
                c.drawString(_M + 0.2 * inch, y, f"·  Type {code}: {cnt} units")
                y -= 0.18 * inch

        self._footer(c, None, project.name, version)

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _page_header(self, c: canvas.Canvas, project: Project, title: str, subtitle: str):
        c.setFillColor(_C_DARK)
        c.rect(0, _H - 0.95 * inch, _W, 0.95 * inch, fill=1, stroke=0)
        c.setFillColor(_C_WHITE)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(_M, _H - 0.42 * inch, title)
        c.setFont("Helvetica", 9)
        c.setFillColor(_C_MID)
        c.drawString(_M, _H - 0.65 * inch, project.name)
        if subtitle:
            c.setFont("Helvetica-Bold", 10)
            c.setFillColor(_C_WHITE)
            c.drawRightString(_W - _M, _H - 0.52 * inch, subtitle)
        # Divider
        c.setStrokeColor(_C_MID)
        c.setLineWidth(0.5)
        c.line(_M, _H - 0.97 * inch, _W - _M, _H - 0.97 * inch)

    def _footer(self, c: canvas.Canvas, page_num: Optional[int], project_name: str, version: str):
        c.setStrokeColor(HexColor("#cccccc"))
        c.setLineWidth(0.5)
        c.line(_M, _M + 0.25 * inch, _W - _M, _M + 0.25 * inch)
        c.setFont("Helvetica", 7)
        c.setFillColor(_C_GREY)
        c.drawString(_M, _M + 0.08 * inch, f"BuildDesk  ·  {project_name}  ·  CONFIDENTIAL")
        if version:
            c.drawRightString(_W - _M, _M + 0.08 * inch, f"Version: {version}")
        if page_num is not None:
            c.drawCentredString(_W / 2, _M + 0.08 * inch, f"Page {page_num}")

    def _badge(self, c: canvas.Canvas, x: float, y: float, text: str, color: HexColor):
        w = c.stringWidth(text, "Helvetica-Bold", 8) + 12
        c.setFillColor(color)
        c.roundRect(x, y - 0.04 * inch, w, 0.22 * inch, 3, fill=1, stroke=0)
        c.setFillColor(_C_WHITE)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(x + 6, y + 0.05 * inch, text)
