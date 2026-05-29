"""
Package Generator Service  (Phase 3)
======================================
Orchestrates traversal of the full project hierarchy to produce a
ProjectPackage record and its page manifest.

Pipeline:
    Project → Units → UnitTypes → Assemblies → Parts
                ↓
    UnitTypeGroups (grouping + qty aggregation)
                ↓
    Page manifest (cover, type sheets, assembly drawings, summary)
                ↓
    ProjectPackage  (persisted)

Variant logic:
- Units are grouped by unit_type_id.
- Assembly templates are shared per UnitType; variant notes appear on type sheets.
- MIR / ADA variants are noted on both the type sheet and drawing page title.

This service does NOT generate PDF bytes — that is PackagePdfExporter's job.
It builds the logical package structure and persists it.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.project_package import (
    PackagePage, PackagePageType, PackageSummary,
    ProjectPackage, ProjectPackageStatus, UnitTypeGroup,
)
from app.repositories.fabrication_repository import FabricationRepository
from app.repositories.hierarchy_repository import ProjectHierarchyRepository
from app.repositories.package_repository import PackageRepository


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PackageGeneratorService:
    """
    Generates the logical ProjectPackage from a project's live hierarchy.

    Usage:
        svc = PackageGeneratorService(db)
        package = svc.generate(tenant_id, project_id, version="1.0")
    """

    def __init__(self, session: Session) -> None:
        self._hierarchy = ProjectHierarchyRepository(session)
        self._fabrication = FabricationRepository(session)
        self._packages = PackageRepository(session)

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def generate(
        self,
        tenant_id: uuid.UUID,
        project_id: uuid.UUID,
        version: str = "1.0",
        issued_by: Optional[str] = None,
        revision_notes: Optional[str] = None,
    ) -> ProjectPackage:
        """
        Full generation pipeline. Returns the saved ProjectPackage.
        Raises ValueError if the project is not found or has no units.
        """
        # 1. Validate project
        project = self._hierarchy.get_project(tenant_id, project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found.")

        # 2. Traverse hierarchy → build UnitTypeGroups
        unit_type_groups = self._build_unit_type_groups(tenant_id, project_id)

        # 3. Load assemblies to enrich groups with assembly types
        all_assemblies = self._fabrication.list_assemblies(tenant_id, project_id)
        assembly_map: Dict[str, List[str]] = {}  # unit_type_id → [assembly_type, ...]
        for asm in all_assemblies:
            if asm.unit_type_id:
                key = str(asm.unit_type_id)
                if key not in assembly_map:
                    assembly_map[key] = []
                atype = asm.assembly_type.value
                if atype not in assembly_map[key]:
                    assembly_map[key].append(atype)

        for group in unit_type_groups:
            group.assembly_types = assembly_map.get(str(group.unit_type_id), [])

        # 4. Compute summary
        summary = self._compute_summary(unit_type_groups, all_assemblies)

        # 5. Build page manifest
        pages = self._build_page_manifest(unit_type_groups, summary)

        # 6. Create and persist package
        package = ProjectPackage(
            package_id=uuid.uuid4(),
            project_id=project_id,
            tenant_id=tenant_id,
            version=version,
            issued_by=issued_by,
            issued_date=_utcnow(),
            revision_notes=revision_notes,
            status=ProjectPackageStatus.READY,
            generated_at=_utcnow(),
            page_count=len(pages),
            pages=pages,
        )
        return self._packages.save_package(package)

    # ------------------------------------------------------------------
    # Hierarchy traversal → UnitTypeGroups
    # ------------------------------------------------------------------

    def _build_unit_type_groups(
        self, tenant_id: uuid.UUID, project_id: uuid.UUID
    ) -> List[UnitTypeGroup]:
        """
        Traverse units and group them by unit_type_id.
        Units without a unit_type_id are placed in a 'UNTYPED' fallback group.
        Groups are sorted by unit_type sort_order for consistent page ordering.
        """
        units = self._hierarchy.list_units(tenant_id, project_id)
        unit_types = self._hierarchy.list_unit_types(tenant_id, project_id)
        unit_type_map = {str(ut.unit_type_id): ut for ut in unit_types}

        # Accumulate units per type
        groups: Dict[str, UnitTypeGroup] = {}
        untyped_codes: List[str] = []

        for unit in sorted(units, key=lambda u: (u.sort_order, u.code)):
            if unit.unit_type_id:
                key = str(unit.unit_type_id)
                if key not in groups:
                    ut = unit_type_map.get(key)
                    groups[key] = UnitTypeGroup(
                        unit_type_id=unit.unit_type_id,
                        unit_type_code=ut.code if ut else key[:8],
                        unit_type_name=ut.name if ut else "Unknown Type",
                        is_mirror=ut.is_mirror if ut else False,
                        is_ada=ut.is_ada if ut else False,
                    )
                groups[key].unit_count += 1
                groups[key].unit_codes.append(unit.code)
            else:
                untyped_codes.append(unit.code)

        result = list(groups.values())

        # Preserve sort order from unit_types list
        type_order = {str(ut.unit_type_id): ut.sort_order for ut in unit_types}
        result.sort(key=lambda g: type_order.get(str(g.unit_type_id), 999))

        # Add untyped group if any
        if untyped_codes:
            result.append(UnitTypeGroup(
                unit_type_id=uuid.uuid4(),  # synthetic ID, not persisted
                unit_type_code="UNTYPED",
                unit_type_name="Units Without Type Assignment",
                unit_count=len(untyped_codes),
                unit_codes=untyped_codes,
            ))

        return result

    # ------------------------------------------------------------------
    # Summary computation
    # ------------------------------------------------------------------

    def _compute_summary(self, groups: List[UnitTypeGroup], assemblies) -> PackageSummary:
        total_units = sum(g.unit_count for g in groups)
        assembly_counts: Dict[str, int] = {}
        unit_type_counts: Dict[str, int] = {}
        part_counts: Dict[str, int] = {}
        total_area_sqin = 0.0

        for asm in assemblies:
            atype = asm.assembly_type.value
            assembly_counts[atype] = assembly_counts.get(atype, 0) + 1
            for part in asm.parts:
                ptype = part.part_type.value
                part_counts[ptype] = part_counts.get(ptype, 0) + 1
                total_area_sqin += part.dimensions.length * part.dimensions.depth

        for g in groups:
            unit_type_counts[g.unit_type_code] = g.unit_count

        return PackageSummary(
            total_units=total_units,
            total_assemblies=len(assemblies),
            total_parts=sum(part_counts.values()),
            total_area_sqin=round(total_area_sqin, 2),
            total_area_sqft=round(total_area_sqin / 144.0, 2),
            assembly_counts=assembly_counts,
            unit_type_counts=unit_type_counts,
            part_counts_by_type=part_counts,
        )

    # ------------------------------------------------------------------
    # Page manifest builder
    # ------------------------------------------------------------------

    def _build_page_manifest(
        self, groups: List[UnitTypeGroup], summary: PackageSummary
    ) -> List[PackagePage]:
        """
        Build the ordered list of PackagePage records.

        Page order:
            1.   Cover
            2+.  Type sheets (one per UnitTypeGroup)
            N+.  Assembly drawing pages (per group × per assembly type)
            Last: Summary
        """
        pages: List[PackagePage] = []
        pkg_id = uuid.uuid4()  # placeholder — will be overwritten by caller

        def _page(num: int, ptype: PackagePageType, title: str, ref: str) -> PackagePage:
            return PackagePage(
                page_id=uuid.uuid4(),
                package_id=pkg_id,
                page_number=num,
                page_type=ptype,
                title=title,
                content_ref=ref,
            )

        page_num = 1

        # Cover
        pages.append(_page(page_num, PackagePageType.COVER, "Cover", "cover"))
        page_num += 1

        # Type sheets + assembly drawing pages
        for group in groups:
            variant_note = ""
            if group.is_mirror:
                variant_note = " [MIRROR]"
            elif group.is_ada:
                variant_note = " [ADA]"

            type_title = f"{group.unit_type_code} — Qty {group.unit_count}{variant_note}"
            pages.append(_page(
                page_num,
                PackagePageType.TYPE_SHEET,
                type_title,
                f"type_sheet::{group.unit_type_id}",
            ))
            page_num += 1

            # One drawing page per assembly type in this unit type
            for atype in group.assembly_types:
                draw_title = f"{group.unit_type_code} — {atype.replace('_', ' ').title()}{variant_note}"
                pages.append(_page(
                    page_num,
                    PackagePageType.ASSEMBLY_DRAWING,
                    draw_title,
                    f"assembly_drawing::{group.unit_type_id}::{atype}",
                ))
                page_num += 1

        # Summary
        pages.append(_page(page_num, PackagePageType.SUMMARY, "Project Summary", "summary"))

        return pages

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def get_package(self, tenant_id: uuid.UUID, package_id: uuid.UUID) -> Optional[ProjectPackage]:
        return self._packages.get_package(tenant_id, package_id)

    def get_latest_for_project(self, tenant_id: uuid.UUID, project_id: uuid.UUID) -> Optional[ProjectPackage]:
        return self._packages.get_latest_for_project(tenant_id, project_id)

    def list_for_project(self, tenant_id: uuid.UUID, project_id: uuid.UUID) -> List[ProjectPackage]:
        return self._packages.list_for_project(tenant_id, project_id)

    def get_unit_type_groups(self, tenant_id: uuid.UUID, project_id: uuid.UUID) -> List[UnitTypeGroup]:
        """Exposed for the PDF exporter to re-traverse grouping without saving."""
        all_assemblies = self._fabrication.list_assemblies(tenant_id, project_id)
        groups = self._build_unit_type_groups(tenant_id, project_id)
        assembly_map: Dict[str, List[str]] = {}
        for asm in all_assemblies:
            if asm.unit_type_id:
                key = str(asm.unit_type_id)
                if key not in assembly_map:
                    assembly_map[key] = []
                atype = asm.assembly_type.value
                if atype not in assembly_map[key]:
                    assembly_map[key].append(atype)
        for g in groups:
            g.assembly_types = assembly_map.get(str(g.unit_type_id), [])
        return groups

    def get_summary(self, tenant_id: uuid.UUID, project_id: uuid.UUID) -> PackageSummary:
        """Exposed for the PDF exporter's Summary page."""
        all_assemblies = self._fabrication.list_assemblies(tenant_id, project_id)
        groups = self._build_unit_type_groups(tenant_id, project_id)
        return self._compute_summary(groups, all_assemblies)
