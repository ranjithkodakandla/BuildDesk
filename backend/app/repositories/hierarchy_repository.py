"""
Hierarchy Repository
====================
SQLAlchemy-backed repository for the project hierarchy domain:
    Project (extended), Building, Floor, UnitType, Unit

All methods enforce tenant_id scoping — no cross-tenant reads.
All IDs are stored as strings in DB and converted to/from uuid.UUID at the boundary.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models import (
    BuildingRecord,
    FloorRecord,
    ProjectRecord,
    UnitRecord,
    UnitTypeRecord,
)
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


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Mappers: ORM Record ↔ Domain Model
# ---------------------------------------------------------------------------

def _project_from_record(r: ProjectRecord) -> Project:
    cfg = r.hierarchy_config or {}
    return Project(
        project_id=uuid.UUID(r.id),
        tenant_id=uuid.UUID(r.tenant_id),
        name=r.name,
        client_name=r.client_name,
        material=r.material,
        issue_date=r.issue_date,
        description=r.description,
        address=r.address,
        status=ProjectStatus(r.status) if r.status else ProjectStatus.draft,
        hierarchy_config=HierarchyConfig(
            has_buildings=cfg.get("has_buildings", False),
            has_floors=cfg.get("has_floors", False),
            has_unit_types=cfg.get("has_unit_types", True),
        ),
        created_at=r.created_at,
        updated_at=r.updated_at or r.created_at,
    )


def _building_from_record(r: BuildingRecord) -> Building:
    return Building(
        building_id=uuid.UUID(r.id),
        project_id=uuid.UUID(r.project_id),
        tenant_id=uuid.UUID(r.tenant_id),
        name=r.name,
        code=r.code,
        sort_order=r.sort_order,
        created_at=r.created_at,
        updated_at=r.updated_at or r.created_at,
    )


def _floor_from_record(r: FloorRecord) -> Floor:
    return Floor(
        floor_id=uuid.UUID(r.id),
        project_id=uuid.UUID(r.project_id),
        building_id=uuid.UUID(r.building_id),
        tenant_id=uuid.UUID(r.tenant_id),
        name=r.name,
        number=r.number,
        sort_order=r.sort_order,
        created_at=r.created_at,
        updated_at=r.updated_at or r.created_at,
    )


def _unit_type_from_record(r: UnitTypeRecord) -> UnitType:
    return UnitType(
        unit_type_id=uuid.UUID(r.id),
        project_id=uuid.UUID(r.project_id),
        tenant_id=uuid.UUID(r.tenant_id),
        code=r.code,
        name=r.name,
        description=r.description,
        is_mirror=r.is_mirror,
        is_ada=r.is_ada,
        base_type_id=uuid.UUID(r.base_type_id) if r.base_type_id else None,
        sort_order=r.sort_order,
        created_at=r.created_at,
        updated_at=r.updated_at or r.created_at,
    )


def _unit_from_record(r: UnitRecord) -> Unit:
    return Unit(
        unit_id=uuid.UUID(r.id),
        project_id=uuid.UUID(r.project_id),
        tenant_id=uuid.UUID(r.tenant_id),
        building_id=uuid.UUID(r.building_id) if r.building_id else None,
        floor_id=uuid.UUID(r.floor_id) if r.floor_id else None,
        unit_type_id=uuid.UUID(r.unit_type_id) if r.unit_type_id else None,
        name=r.name,
        code=r.code,
        variant=UnitVariant(r.variant) if r.variant else UnitVariant.STANDARD,
        notes=r.notes,
        sort_order=r.sort_order,
        created_at=r.created_at,
        updated_at=r.updated_at or r.created_at,
    )


# ---------------------------------------------------------------------------
# ProjectHierarchyRepository
# ---------------------------------------------------------------------------

class ProjectHierarchyRepository:
    """
    Single repository covering the full project hierarchy.
    All operations require tenant_id for data isolation.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    # ── Project ────────────────────────────────────────────────────────────

    def create_project(self, project: Project) -> Project:
        cfg = project.hierarchy_config
        record = ProjectRecord(
            id=str(project.project_id),
            tenant_id=str(project.tenant_id),
            name=project.name,
            client_name=project.client_name,
            material=project.material,
            issue_date=project.issue_date,
            description=project.description,
            address=project.address,
            status=project.status.value,
            hierarchy_config={
                "has_buildings": cfg.has_buildings,
                "has_floors": cfg.has_floors,
                "has_unit_types": cfg.has_unit_types,
            },
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return _project_from_record(record)

    def get_project(self, tenant_id: uuid.UUID, project_id: uuid.UUID) -> Optional[Project]:
        r = self.session.query(ProjectRecord).filter(
            ProjectRecord.id == str(project_id),
            ProjectRecord.tenant_id == str(tenant_id),
        ).first()
        return _project_from_record(r) if r else None

    def list_projects(self, tenant_id: uuid.UUID) -> List[Project]:
        records = self.session.query(ProjectRecord).filter(
            ProjectRecord.tenant_id == str(tenant_id),
        ).order_by(ProjectRecord.created_at.desc()).all()
        return [_project_from_record(r) for r in records]

    def update_project(self, tenant_id: uuid.UUID, project: Project) -> Optional[Project]:
        r = self.session.query(ProjectRecord).filter(
            ProjectRecord.id == str(project.project_id),
            ProjectRecord.tenant_id == str(tenant_id),
        ).first()
        if not r:
            return None
        r.name = project.name
        r.client_name = project.client_name
        r.material = project.material
        r.issue_date = project.issue_date
        r.description = project.description
        r.address = project.address
        r.status = project.status.value
        cfg = project.hierarchy_config
        r.hierarchy_config = {
            "has_buildings": cfg.has_buildings,
            "has_floors": cfg.has_floors,
            "has_unit_types": cfg.has_unit_types,
        }
        r.updated_at = _utcnow()
        self.session.commit()
        self.session.refresh(r)
        return _project_from_record(r)

    # ── Building ───────────────────────────────────────────────────────────

    def create_building(self, building: Building) -> Building:
        record = BuildingRecord(
            id=str(building.building_id),
            project_id=str(building.project_id),
            tenant_id=str(building.tenant_id),
            name=building.name,
            code=building.code,
            sort_order=building.sort_order,
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return _building_from_record(record)

    def list_buildings(self, tenant_id: uuid.UUID, project_id: uuid.UUID) -> List[Building]:
        records = self.session.query(BuildingRecord).filter(
            BuildingRecord.project_id == str(project_id),
            BuildingRecord.tenant_id == str(tenant_id),
        ).order_by(BuildingRecord.sort_order).all()
        return [_building_from_record(r) for r in records]

    def get_building(self, tenant_id: uuid.UUID, building_id: uuid.UUID) -> Optional[Building]:
        r = self.session.query(BuildingRecord).filter(
            BuildingRecord.id == str(building_id),
            BuildingRecord.tenant_id == str(tenant_id),
        ).first()
        return _building_from_record(r) if r else None

    # ── Floor ──────────────────────────────────────────────────────────────

    def create_floor(self, floor: Floor) -> Floor:
        record = FloorRecord(
            id=str(floor.floor_id),
            project_id=str(floor.project_id),
            building_id=str(floor.building_id),
            tenant_id=str(floor.tenant_id),
            name=floor.name,
            number=floor.number,
            sort_order=floor.sort_order,
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return _floor_from_record(record)

    def list_floors(self, tenant_id: uuid.UUID, building_id: uuid.UUID) -> List[Floor]:
        records = self.session.query(FloorRecord).filter(
            FloorRecord.building_id == str(building_id),
            FloorRecord.tenant_id == str(tenant_id),
        ).order_by(FloorRecord.sort_order).all()
        return [_floor_from_record(r) for r in records]

    # ── UnitType ───────────────────────────────────────────────────────────

    def create_unit_type(self, unit_type: UnitType) -> UnitType:
        record = UnitTypeRecord(
            id=str(unit_type.unit_type_id),
            project_id=str(unit_type.project_id),
            tenant_id=str(unit_type.tenant_id),
            code=unit_type.code,
            name=unit_type.name,
            description=unit_type.description,
            is_mirror=unit_type.is_mirror,
            is_ada=unit_type.is_ada,
            base_type_id=str(unit_type.base_type_id) if unit_type.base_type_id else None,
            sort_order=unit_type.sort_order,
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return _unit_type_from_record(record)

    def list_unit_types(self, tenant_id: uuid.UUID, project_id: uuid.UUID) -> List[UnitType]:
        records = self.session.query(UnitTypeRecord).filter(
            UnitTypeRecord.project_id == str(project_id),
            UnitTypeRecord.tenant_id == str(tenant_id),
        ).order_by(UnitTypeRecord.sort_order).all()
        return [_unit_type_from_record(r) for r in records]

    def get_unit_type(self, tenant_id: uuid.UUID, unit_type_id: uuid.UUID) -> Optional[UnitType]:
        r = self.session.query(UnitTypeRecord).filter(
            UnitTypeRecord.id == str(unit_type_id),
            UnitTypeRecord.tenant_id == str(tenant_id),
        ).first()
        return _unit_type_from_record(r) if r else None

    # ── Unit ───────────────────────────────────────────────────────────────

    def create_unit(self, unit: Unit) -> Unit:
        record = UnitRecord(
            id=str(unit.unit_id),
            project_id=str(unit.project_id),
            tenant_id=str(unit.tenant_id),
            building_id=str(unit.building_id) if unit.building_id else None,
            floor_id=str(unit.floor_id) if unit.floor_id else None,
            unit_type_id=str(unit.unit_type_id) if unit.unit_type_id else None,
            name=unit.name,
            code=unit.code,
            variant=unit.variant.value,
            notes=unit.notes,
            sort_order=unit.sort_order,
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return _unit_from_record(record)

    def list_units(self, tenant_id: uuid.UUID, project_id: uuid.UUID) -> List[Unit]:
        records = self.session.query(UnitRecord).filter(
            UnitRecord.project_id == str(project_id),
            UnitRecord.tenant_id == str(tenant_id),
        ).order_by(UnitRecord.sort_order).all()
        return [_unit_from_record(r) for r in records]

    def get_unit(self, tenant_id: uuid.UUID, unit_id: uuid.UUID) -> Optional[Unit]:
        r = self.session.query(UnitRecord).filter(
            UnitRecord.id == str(unit_id),
            UnitRecord.tenant_id == str(tenant_id),
        ).first()
        return _unit_from_record(r) if r else None

    def list_units_by_type(
        self, tenant_id: uuid.UUID, project_id: uuid.UUID, unit_type_id: uuid.UUID
    ) -> List[Unit]:
        records = self.session.query(UnitRecord).filter(
            UnitRecord.project_id == str(project_id),
            UnitRecord.tenant_id == str(tenant_id),
            UnitRecord.unit_type_id == str(unit_type_id),
        ).order_by(UnitRecord.sort_order).all()
        return [_unit_from_record(r) for r in records]
