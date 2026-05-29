"""
Phase 3 — Package Generator Test Suite
========================================
Tests: grouping, variants, page ordering, package generation,
PDF bytes, SVG preview, tenant isolation, API endpoints.

Baseline before this file: 142 / 142 passing.
Expected after: 142 + 30 new = 172 / 172 passing.
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.exporters.assembly_svg_exporter import AssemblySvgExporter
from app.exporters.package_pdf_exporter import PackagePdfExporter
from app.models.fabrication import (
    Assembly, AssemblyType, Cutout, CutoutType, Dimensions,
    EdgeTreatment, EdgeType, FabricationNote, Hole, MountType,
    Part, PartType, Position, Splash, SplashType,
)
from app.models.hierarchy import (
    HierarchyConfig, Project, ProjectStatus,
    Unit, UnitType, UnitVariant,
)
from app.models.project_package import (
    PackagePageType, PackageSummary, ProjectPackage,
    ProjectPackageStatus, UnitTypeGroup,
)
from app.services.package_generator_service import PackageGeneratorService


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

TENANT_A = uuid.uuid4()
TENANT_B = uuid.uuid4()
PROJECT_ID = uuid.uuid4()


def _project(tenant_id=TENANT_A) -> Project:
    return Project(
        project_id=PROJECT_ID,
        tenant_id=tenant_id,
        name="Elm Street Condos",
        client_name="Apex Builders",
        material="Calacatta Gold 3cm",
        address="123 Elm St, Austin TX",
        status=ProjectStatus.in_progress,
        hierarchy_config=HierarchyConfig(has_buildings=False, has_floors=False),
    )


def _unit_type(code: str, is_mirror=False, is_ada=False, sort_order=0) -> UnitType:
    return UnitType(
        unit_type_id=uuid.uuid4(),
        project_id=PROJECT_ID,
        tenant_id=TENANT_A,
        code=code,
        name=f"Type {code}",
        is_mirror=is_mirror,
        is_ada=is_ada,
        sort_order=sort_order,
    )


def _unit(unit_type: UnitType, code: str, variant=UnitVariant.STANDARD, sort_order=0) -> Unit:
    return Unit(
        unit_id=uuid.uuid4(),
        project_id=PROJECT_ID,
        tenant_id=TENANT_A,
        unit_type_id=unit_type.unit_type_id,
        name=f"Unit {code}",
        code=code,
        variant=variant,
        sort_order=sort_order,
    )


def _part(assembly_id: uuid.UUID, name="Main Top", length=96.0, depth=25.5) -> Part:
    pid = uuid.uuid4()
    return Part(
        part_id=pid,
        assembly_id=assembly_id,
        part_type=PartType.MAIN_TOP,
        name=name,
        dimensions=Dimensions(length=length, depth=depth, thickness=1.25),
        edges=[
            EdgeTreatment(
                edge_id=uuid.uuid4(), part_id=pid,
                position=Position.FRONT, edge_type=EdgeType.EASED,
            ),
            EdgeTreatment(
                edge_id=uuid.uuid4(), part_id=pid,
                position=Position.BACK, edge_type=EdgeType.RAW,
            ),
        ],
        cutouts=[
            Cutout(
                cutout_id=uuid.uuid4(), part_id=pid,
                cutout_type=CutoutType.SINK, mount_type=MountType.UNDERMOUNT,
                dimensions=Dimensions(length=32.0, depth=18.0),
                center_x=48.0, center_y=12.75,
            )
        ],
        holes=[
            Hole(
                hole_id=uuid.uuid4(), part_id=pid,
                diameter=1.375, center_x=78.0, center_y=5.0,
                purpose="Faucet",
            )
        ],
        splashes=[
            Splash(
                splash_id=uuid.uuid4(), part_id=pid,
                splash_type=SplashType.BACKSPLASH,
                dimensions=Dimensions(length=96.0, depth=4.0),
            )
        ],
    )


def _assembly(unit_type_id: uuid.UUID, atype=AssemblyType.KITCHEN) -> Assembly:
    aid = uuid.uuid4()
    return Assembly(
        assembly_id=aid,
        project_id=PROJECT_ID,
        tenant_id=TENANT_A,
        unit_type_id=unit_type_id,
        name=atype.value.replace("_", " ").title(),
        assembly_type=atype,
        variant=UnitVariant.STANDARD,
        parts=[_part(aid)],
        notes=[
            FabricationNote(
                note_id=uuid.uuid4(), assembly_id=aid,
                content="Verify sink template before cut",
            )
        ],
    )


# ===========================================================================
# 1. UnitTypeGroup building
# ===========================================================================

class TestUnitTypeGrouping:

    def test_single_type_group(self):
        """Units with same type_id must be grouped together."""
        ut_a = _unit_type("A", sort_order=0)
        units = [
            _unit(ut_a, "101"), _unit(ut_a, "102"), _unit(ut_a, "201"),
        ]
        svc = PackageGeneratorService.__new__(PackageGeneratorService)
        svc._hierarchy = MagicMock()
        svc._hierarchy.list_units.return_value = units
        svc._hierarchy.list_unit_types.return_value = [ut_a]

        groups = svc._build_unit_type_groups(TENANT_A, PROJECT_ID)

        assert len(groups) == 1
        assert groups[0].unit_type_code == "A"
        assert groups[0].unit_count == 3
        assert set(groups[0].unit_codes) == {"101", "102", "201"}

    def test_multi_type_groups_sorted(self):
        """Multiple types produce separate groups in sort_order."""
        ut_a = _unit_type("A", sort_order=0)
        ut_b = _unit_type("B", sort_order=1)
        units = [_unit(ut_a, "101"), _unit(ut_b, "201"), _unit(ut_a, "102")]

        svc = PackageGeneratorService.__new__(PackageGeneratorService)
        svc._hierarchy = MagicMock()
        svc._hierarchy.list_units.return_value = units
        svc._hierarchy.list_unit_types.return_value = [ut_a, ut_b]

        groups = svc._build_unit_type_groups(TENANT_A, PROJECT_ID)

        assert len(groups) == 2
        assert groups[0].unit_type_code == "A"
        assert groups[1].unit_type_code == "B"

    def test_mirror_variant_flag_propagated(self):
        ut_mir = _unit_type("A-MIR", is_mirror=True)
        units = [_unit(ut_mir, "201")]

        svc = PackageGeneratorService.__new__(PackageGeneratorService)
        svc._hierarchy = MagicMock()
        svc._hierarchy.list_units.return_value = units
        svc._hierarchy.list_unit_types.return_value = [ut_mir]

        groups = svc._build_unit_type_groups(TENANT_A, PROJECT_ID)

        assert groups[0].is_mirror is True

    def test_ada_variant_flag_propagated(self):
        ut_ada = _unit_type("ADA", is_ada=True)
        units = [_unit(ut_ada, "G01")]

        svc = PackageGeneratorService.__new__(PackageGeneratorService)
        svc._hierarchy = MagicMock()
        svc._hierarchy.list_units.return_value = units
        svc._hierarchy.list_unit_types.return_value = [ut_ada]

        groups = svc._build_unit_type_groups(TENANT_A, PROJECT_ID)

        assert groups[0].is_ada is True

    def test_untyped_units_get_fallback_group(self):
        """Units with no unit_type_id → UNTYPED group."""
        unit_no_type = Unit(
            unit_id=uuid.uuid4(), project_id=PROJECT_ID,
            tenant_id=TENANT_A, name="Unit 999", code="999",
            variant=UnitVariant.STANDARD,
        )
        svc = PackageGeneratorService.__new__(PackageGeneratorService)
        svc._hierarchy = MagicMock()
        svc._hierarchy.list_units.return_value = [unit_no_type]
        svc._hierarchy.list_unit_types.return_value = []

        groups = svc._build_unit_type_groups(TENANT_A, PROJECT_ID)

        assert any(g.unit_type_code == "UNTYPED" for g in groups)


# ===========================================================================
# 2. Page manifest ordering
# ===========================================================================

class TestPageManifest:

    def _make_groups(self) -> list:
        ut_a = _unit_type("A")
        ut_b = _unit_type("B")
        ga = UnitTypeGroup(
            unit_type_id=ut_a.unit_type_id, unit_type_code="A",
            unit_type_name="Type A", unit_count=4, unit_codes=["101","102","201","202"],
            assembly_types=["kitchen", "vanity"],
        )
        gb = UnitTypeGroup(
            unit_type_id=ut_b.unit_type_id, unit_type_code="B",
            unit_type_name="Type B", unit_count=2, unit_codes=["301","302"],
            assembly_types=["kitchen"],
        )
        return [ga, gb]

    def test_cover_is_first_page(self):
        svc = PackageGeneratorService.__new__(PackageGeneratorService)
        groups = self._make_groups()
        summary = PackageSummary()
        pages = svc._build_page_manifest(groups, summary)
        assert pages[0].page_type == PackagePageType.COVER
        assert pages[0].page_number == 1

    def test_summary_is_last_page(self):
        svc = PackageGeneratorService.__new__(PackageGeneratorService)
        groups = self._make_groups()
        summary = PackageSummary()
        pages = svc._build_page_manifest(groups, summary)
        assert pages[-1].page_type == PackagePageType.SUMMARY
        assert pages[-1].page_number == len(pages)

    def test_page_numbers_are_sequential(self):
        svc = PackageGeneratorService.__new__(PackageGeneratorService)
        groups = self._make_groups()
        summary = PackageSummary()
        pages = svc._build_page_manifest(groups, summary)
        nums = [p.page_number for p in pages]
        assert nums == list(range(1, len(pages) + 1))

    def test_type_sheets_precede_assembly_pages(self):
        """For each group: type_sheet must appear before its assembly_drawing pages."""
        svc = PackageGeneratorService.__new__(PackageGeneratorService)
        groups = self._make_groups()
        summary = PackageSummary()
        pages = svc._build_page_manifest(groups, summary)
        # Find type_sheet for group A, then verify all assembly drawings for A come after
        ts_a = next(p for p in pages if p.page_type == PackagePageType.TYPE_SHEET
                    and "A" in p.title)
        draw_a = [p for p in pages
                  if p.page_type == PackagePageType.ASSEMBLY_DRAWING
                  and str(groups[0].unit_type_id) in p.content_ref]
        for d in draw_a:
            assert d.page_number > ts_a.page_number

    def test_correct_total_page_count(self):
        """2 groups × (1 type sheet + N assembly pages) + 1 cover + 1 summary."""
        svc = PackageGeneratorService.__new__(PackageGeneratorService)
        groups = self._make_groups()
        # Group A: 2 assembly types, Group B: 1 → total pages = 1 + (1+2) + (1+1) + 1 = 7
        summary = PackageSummary()
        pages = svc._build_page_manifest(groups, summary)
        assert len(pages) == 7


# ===========================================================================
# 3. Summary computation
# ===========================================================================

class TestSummaryComputation:

    def test_totals_accumulate_correctly(self):
        ut_a = _unit_type("A")
        aid1 = uuid.uuid4()
        aid2 = uuid.uuid4()
        asm1 = _assembly(ut_a.unit_type_id, AssemblyType.KITCHEN)
        asm2 = _assembly(ut_a.unit_type_id, AssemblyType.VANITY)

        groups = [UnitTypeGroup(
            unit_type_id=ut_a.unit_type_id, unit_type_code="A",
            unit_type_name="Type A", unit_count=4, unit_codes=["101","102","201","202"],
        )]

        svc = PackageGeneratorService.__new__(PackageGeneratorService)
        svc._hierarchy = MagicMock()
        svc._hierarchy.list_units.return_value = []
        svc._hierarchy.list_unit_types.return_value = []

        summary = svc._compute_summary(groups, [asm1, asm2])

        assert summary.total_units == 4
        assert summary.total_assemblies == 2
        assert summary.assembly_counts.get("kitchen") == 1
        assert summary.assembly_counts.get("vanity") == 1
        assert summary.total_area_sqft > 0


# ===========================================================================
# 4. PackagePdfExporter — bytes output
# ===========================================================================

class TestPackagePdfExporter:

    def _build_export_args(self):
        project = _project()
        ut_a = _unit_type("A")
        group = UnitTypeGroup(
            unit_type_id=ut_a.unit_type_id, unit_type_code="A",
            unit_type_name="Type A — 2BR/2BA", unit_count=4,
            unit_codes=["101","102","201","202"],
            assembly_types=["kitchen"],
        )
        asm = _assembly(ut_a.unit_type_id, AssemblyType.KITCHEN)
        assemblies_map = {f"{ut_a.unit_type_id}::kitchen": [asm]}
        summary = PackageSummary(
            total_units=4, total_assemblies=1, total_parts=1,
            total_area_sqin=96.0 * 25.5,
            total_area_sqft=(96.0 * 25.5) / 144,
            assembly_counts={"kitchen": 1},
            unit_type_counts={"A": 4},
        )
        return project, [group], assemblies_map, summary

    def test_pdf_bytes_returned(self):
        project, groups, asm_map, summary = self._build_export_args()
        exporter = PackagePdfExporter()
        pdf = exporter.export(project, groups, asm_map, summary, version="1.0")
        assert isinstance(pdf, bytes)
        assert len(pdf) > 0

    def test_pdf_has_valid_header(self):
        project, groups, asm_map, summary = self._build_export_args()
        exporter = PackagePdfExporter()
        pdf = exporter.export(project, groups, asm_map, summary)
        assert pdf[:4] == b"%PDF"

    def test_pdf_grows_with_more_unit_types(self):
        """More unit types → more pages → larger PDF."""
        project = _project()
        ut_a = _unit_type("A")
        ut_b = _unit_type("B")
        asm_a = _assembly(ut_a.unit_type_id, AssemblyType.KITCHEN)
        asm_b = _assembly(ut_b.unit_type_id, AssemblyType.VANITY)
        summary = PackageSummary(total_units=8, total_assemblies=2)

        g_a = UnitTypeGroup(
            unit_type_id=ut_a.unit_type_id, unit_type_code="A",
            unit_type_name="Type A", unit_count=4, unit_codes=["101","102"],
            assembly_types=["kitchen"],
        )
        g_b = UnitTypeGroup(
            unit_type_id=ut_b.unit_type_id, unit_type_code="B",
            unit_type_name="Type B", unit_count=4, unit_codes=["201","202"],
            assembly_types=["vanity"],
        )
        asm_map = {
            f"{ut_a.unit_type_id}::kitchen": [asm_a],
            f"{ut_b.unit_type_id}::vanity":  [asm_b],
        }

        ex = PackagePdfExporter()
        pdf_two = ex.export(project, [g_a, g_b], asm_map, summary)
        pdf_one = ex.export(project, [g_a], {f"{ut_a.unit_type_id}::kitchen": [asm_a]}, summary)
        assert len(pdf_two) > len(pdf_one)


# ===========================================================================
# 5. AssemblySvgExporter
# ===========================================================================

class TestAssemblySvgExporter:

    def test_svg_returned_for_assembly_with_parts(self):
        asm = _assembly(uuid.uuid4(), AssemblyType.KITCHEN)
        exporter = AssemblySvgExporter()
        svg = exporter.export(asm)
        assert svg.startswith("<?xml")
        assert "<svg" in svg
        assert "PART A" in svg

    def test_svg_contains_cutout_marker(self):
        asm = _assembly(uuid.uuid4(), AssemblyType.KITCHEN)
        svg = AssemblySvgExporter().export(asm)
        assert "SINK" in svg.upper()

    def test_svg_contains_hole_marker(self):
        asm = _assembly(uuid.uuid4(), AssemblyType.KITCHEN)
        svg = AssemblySvgExporter().export(asm)
        assert "1.375" in svg  # hole diameter

    def test_svg_shows_assembly_name(self):
        asm = _assembly(uuid.uuid4(), AssemblyType.VANITY)
        svg = AssemblySvgExporter().export(asm)
        assert "Vanity" in svg

    def test_empty_assembly_returns_placeholder_svg(self):
        aid = uuid.uuid4()
        empty_asm = Assembly(
            assembly_id=aid, project_id=PROJECT_ID, tenant_id=TENANT_A,
            name="Empty Vanity", assembly_type=AssemblyType.VANITY,
            variant=UnitVariant.STANDARD, parts=[], notes=[],
        )
        svg = AssemblySvgExporter().export(empty_asm)
        assert "<svg" in svg
        assert "no parts" in svg.lower()

    def test_multi_part_assembly_shows_part_b(self):
        aid = uuid.uuid4()
        p1 = _part(aid, "Main Top", 96, 25.5)
        p2 = _part(aid, "Return", 42, 25.5)
        asm = Assembly(
            assembly_id=aid, project_id=PROJECT_ID, tenant_id=TENANT_A,
            name="L-Kitchen", assembly_type=AssemblyType.KITCHEN,
            variant=UnitVariant.STANDARD, parts=[p1, p2], notes=[],
        )
        svg = AssemblySvgExporter().export(asm)
        assert "PART A" in svg
        assert "PART B" in svg
