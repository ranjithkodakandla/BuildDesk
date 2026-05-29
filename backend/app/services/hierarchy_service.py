"""
Hierarchy Service
=================
Domain service for managing the flexible project hierarchy:
    Project → Building (opt) → Floor (opt) → UnitType → Unit

Responsibilities:
- Validate hierarchy config consistency
- Enforce: floors require buildings, buildings require project
- Build full project tree view
- Provide unit counts per type (for package generation)

This service is pure domain logic — no HTTP, no DB I/O.
It receives a repo and coordinates domain operations through it.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import List, Optional

from app.models.hierarchy import (
    Building,
    Floor,
    HierarchyConfig,
    Project,
    ProjectStatus,
    Unit,
    UnitType,
    UnitVariant,
)
from app.repositories.hierarchy_repository import ProjectHierarchyRepository


# ---------------------------------------------------------------------------
# Tree view data structures (for API responses)
# ---------------------------------------------------------------------------

@dataclass
class UnitTypeWithUnits:
    unit_type: UnitType
    units: List[Unit] = field(default_factory=list)

    @property
    def quantity(self) -> int:
        return len(self.units)


@dataclass
class FloorWithUnits:
    floor: Floor
    units: List[Unit] = field(default_factory=list)


@dataclass
class BuildingWithFloors:
    building: Building
    floors: List[FloorWithUnits] = field(default_factory=list)
    units: List[Unit] = field(default_factory=list)  # units directly on building (no floor)


@dataclass
class ProjectTree:
    """Full hierarchical view of a project — used by package generator."""
    project: Project
    buildings: List[BuildingWithFloors] = field(default_factory=list)
    unit_types: List[UnitTypeWithUnits] = field(default_factory=list)
    units: List[Unit] = field(default_factory=list)  # flat units (no building/floor)

    @property
    def total_units(self) -> int:
        return len(self.units) + sum(
            len(b.units) + sum(len(f.units) for f in b.floors)
            for b in self.buildings
        )


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class HierarchyService:
    """
    Stateless service coordinating project hierarchy operations.
    Instantiate per request; pass the repo from the DI container.
    """

    def __init__(self, repo: ProjectHierarchyRepository) -> None:
        self._repo = repo

    # ── Projects ───────────────────────────────────────────────────────────

    def create_project(
        self,
        tenant_id: uuid.UUID,
        name: str,
        *,
        client_name: Optional[str] = None,
        material: Optional[str] = None,
        description: Optional[str] = None,
        address: Optional[str] = None,
        has_buildings: bool = False,
        has_floors: bool = False,
        has_unit_types: bool = True,
    ) -> Project:
        if has_floors and not has_buildings:
            raise ValueError("has_floors=True requires has_buildings=True")

        project = Project(
            tenant_id=tenant_id,
            name=name,
            client_name=client_name,
            material=material,
            description=description,
            address=address,
            status=ProjectStatus.draft,
            hierarchy_config=HierarchyConfig(
                has_buildings=has_buildings,
                has_floors=has_floors,
                has_unit_types=has_unit_types,
            ),
        )
        return self._repo.create_project(project)

    def get_project(self, tenant_id: uuid.UUID, project_id: uuid.UUID) -> Optional[Project]:
        return self._repo.get_project(tenant_id, project_id)

    def list_projects(self, tenant_id: uuid.UUID) -> List[Project]:
        return self._repo.list_projects(tenant_id)

    # ── Buildings ──────────────────────────────────────────────────────────

    def add_building(
        self,
        tenant_id: uuid.UUID,
        project_id: uuid.UUID,
        name: str,
        code: Optional[str] = None,
        sort_order: int = 0,
    ) -> Building:
        project = self._require_project(tenant_id, project_id)
        if not project.hierarchy_config.has_buildings:
            raise ValueError(
                f"Project '{project.name}' does not use buildings. "
                "Enable has_buildings in hierarchy_config first."
            )
        building = Building(
            project_id=project_id,
            tenant_id=tenant_id,
            name=name,
            code=code,
            sort_order=sort_order,
        )
        return self._repo.create_building(building)

    def list_buildings(self, tenant_id: uuid.UUID, project_id: uuid.UUID) -> List[Building]:
        return self._repo.list_buildings(tenant_id, project_id)

    # ── Floors ─────────────────────────────────────────────────────────────

    def add_floor(
        self,
        tenant_id: uuid.UUID,
        project_id: uuid.UUID,
        building_id: uuid.UUID,
        name: str,
        number: Optional[int] = None,
        sort_order: int = 0,
    ) -> Floor:
        project = self._require_project(tenant_id, project_id)
        if not project.hierarchy_config.has_floors:
            raise ValueError(
                f"Project '{project.name}' does not use floors. "
                "Enable has_floors in hierarchy_config first."
            )
        building = self._repo.get_building(tenant_id, building_id)
        if not building:
            raise ValueError(f"Building {building_id} not found in this project/tenant.")

        floor = Floor(
            project_id=project_id,
            building_id=building_id,
            tenant_id=tenant_id,
            name=name,
            number=number,
            sort_order=sort_order,
        )
        return self._repo.create_floor(floor)

    def list_floors(self, tenant_id: uuid.UUID, building_id: uuid.UUID) -> List[Floor]:
        return self._repo.list_floors(tenant_id, building_id)

    # ── UnitTypes ──────────────────────────────────────────────────────────

    def add_unit_type(
        self,
        tenant_id: uuid.UUID,
        project_id: uuid.UUID,
        code: str,
        name: str,
        *,
        description: Optional[str] = None,
        is_mirror: bool = False,
        is_ada: bool = False,
        base_type_id: Optional[uuid.UUID] = None,
        sort_order: int = 0,
    ) -> UnitType:
        self._require_project(tenant_id, project_id)
        if base_type_id:
            base = self._repo.get_unit_type(tenant_id, base_type_id)
            if not base:
                raise ValueError(f"Base unit type {base_type_id} not found.")

        unit_type = UnitType(
            project_id=project_id,
            tenant_id=tenant_id,
            code=code,
            name=name,
            description=description,
            is_mirror=is_mirror,
            is_ada=is_ada,
            base_type_id=base_type_id,
            sort_order=sort_order,
        )
        return self._repo.create_unit_type(unit_type)

    def list_unit_types(self, tenant_id: uuid.UUID, project_id: uuid.UUID) -> List[UnitType]:
        return self._repo.list_unit_types(tenant_id, project_id)

    # ── Units ──────────────────────────────────────────────────────────────

    def add_unit(
        self,
        tenant_id: uuid.UUID,
        project_id: uuid.UUID,
        name: str,
        code: str,
        *,
        building_id: Optional[uuid.UUID] = None,
        floor_id: Optional[uuid.UUID] = None,
        unit_type_id: Optional[uuid.UUID] = None,
        variant: UnitVariant = UnitVariant.STANDARD,
        notes: Optional[str] = None,
        sort_order: int = 0,
    ) -> Unit:
        project = self._require_project(tenant_id, project_id)
        cfg = project.hierarchy_config

        # Validate hierarchy config consistency
        if building_id and not cfg.has_buildings:
            raise ValueError("building_id supplied but project does not use buildings.")
        if floor_id and not cfg.has_floors:
            raise ValueError("floor_id supplied but project does not use floors.")
        if floor_id and not building_id:
            raise ValueError("floor_id requires building_id.")

        # Validate FK existence
        if building_id:
            if not self._repo.get_building(tenant_id, building_id):
                raise ValueError(f"Building {building_id} not found.")
        if unit_type_id:
            if not self._repo.get_unit_type(tenant_id, unit_type_id):
                raise ValueError(f"UnitType {unit_type_id} not found.")

        unit = Unit(
            project_id=project_id,
            tenant_id=tenant_id,
            building_id=building_id,
            floor_id=floor_id,
            unit_type_id=unit_type_id,
            name=name,
            code=code,
            variant=variant,
            notes=notes,
            sort_order=sort_order,
        )
        return self._repo.create_unit(unit)

    def list_units(self, tenant_id: uuid.UUID, project_id: uuid.UUID) -> List[Unit]:
        return self._repo.list_units(tenant_id, project_id)

    def get_unit(self, tenant_id: uuid.UUID, unit_id: uuid.UUID) -> Optional[Unit]:
        return self._repo.get_unit(tenant_id, unit_id)

    # ── Project Tree ───────────────────────────────────────────────────────

    def build_project_tree(self, tenant_id: uuid.UUID, project_id: uuid.UUID) -> Optional[ProjectTree]:
        """
        Constructs the full project hierarchy tree.
        Used by PackageGeneratorService to know which type sheets to generate.
        """
        project = self._repo.get_project(tenant_id, project_id)
        if not project:
            return None

        cfg = project.hierarchy_config
        all_units = self._repo.list_units(tenant_id, project_id)
        unit_types = self._repo.list_unit_types(tenant_id, project_id) if cfg.has_unit_types else []

        # Build unit-type groups
        type_groups: dict[str, UnitTypeWithUnits] = {}
        for ut in unit_types:
            type_groups[str(ut.unit_type_id)] = UnitTypeWithUnits(unit_type=ut)

        for unit in all_units:
            if unit.unit_type_id and str(unit.unit_type_id) in type_groups:
                type_groups[str(unit.unit_type_id)].units.append(unit)

        tree = ProjectTree(
            project=project,
            unit_types=list(type_groups.values()),
            units=all_units if not cfg.has_buildings else [],
        )

        if cfg.has_buildings:
            buildings = self._repo.list_buildings(tenant_id, project_id)
            for b in buildings:
                bwf = BuildingWithFloors(building=b)
                if cfg.has_floors:
                    floors = self._repo.list_floors(tenant_id, b.building_id)
                    for f in floors:
                        floor_units = [u for u in all_units if u.floor_id == f.floor_id]
                        bwf.floors.append(FloorWithUnits(floor=f, units=floor_units))
                else:
                    bwf.units = [u for u in all_units if u.building_id == b.building_id]
                tree.buildings.append(bwf)

        return tree

    # ── Helpers ────────────────────────────────────────────────────────────

    def _require_project(self, tenant_id: uuid.UUID, project_id: uuid.UUID) -> Project:
        project = self._repo.get_project(tenant_id, project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found for this tenant.")
        return project
