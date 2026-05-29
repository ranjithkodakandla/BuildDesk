"""
Phase 1 Hierarchy Tests
========================
Unit tests for HierarchyService domain logic.
Uses an in-memory SQLite database via SQLAlchemy.

Coverage:
    - HierarchyConfig validation
    - Project creation
    - Building lifecycle (create, list, config guard)
    - Floor lifecycle (floor requires building)
    - UnitType creation (standard + derived types)
    - Unit creation with all hierarchy levels
    - Variant assignment (MIR, ADA, etc.)
    - ProjectTree construction
    - Tenant isolation assertions
    - Error cases (missing FK, invalid config)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.models import (  # import all to register with Base metadata
    BuildingRecord,
    FloorRecord,
    GeometryRecord,
    ProjectRecord,
    TenantRecord,
    UnitRecord,
    UnitTypeRecord,
    UserRecord,
)
from app.models.hierarchy import UnitVariant
from app.repositories.hierarchy_repository import ProjectHierarchyRepository
from app.services.hierarchy_service import HierarchyService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def db_session():
    """In-memory SQLite session for each test function."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def service(db_session: Session) -> HierarchyService:
    repo = ProjectHierarchyRepository(db_session)
    return HierarchyService(repo)


@pytest.fixture
def tenant_id() -> uuid.UUID:
    return uuid.UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture
def other_tenant_id() -> uuid.UUID:
    return uuid.UUID("22222222-2222-2222-2222-222222222222")


# ---------------------------------------------------------------------------
# Project tests
# ---------------------------------------------------------------------------

class TestProjectCreation:
    def test_create_simple_project(self, service, tenant_id):
        """Flat project with no buildings/floors."""
        project = service.create_project(
            tenant_id=tenant_id,
            name="Elm Street Condos",
            client_name="Apex Builders",
            material="Taj Mahal 3cm",
            has_buildings=False,
            has_floors=False,
        )
        assert project.name == "Elm Street Condos"
        assert project.client_name == "Apex Builders"
        assert project.material == "Taj Mahal 3cm"
        assert project.hierarchy_config.has_buildings is False
        assert project.hierarchy_config.has_floors is False
        assert project.tenant_id == tenant_id
        assert project.project_id is not None

    def test_create_project_with_buildings(self, service, tenant_id):
        project = service.create_project(tenant_id, "Tower Project", has_buildings=True)
        assert project.hierarchy_config.has_buildings is True

    def test_create_project_with_full_hierarchy(self, service, tenant_id):
        project = service.create_project(
            tenant_id, "Riverside Towers", has_buildings=True, has_floors=True
        )
        assert project.hierarchy_config.has_buildings is True
        assert project.hierarchy_config.has_floors is True

    def test_floors_without_buildings_raises(self, service, tenant_id):
        with pytest.raises(ValueError, match="has_floors=True requires has_buildings=True"):
            service.create_project(tenant_id, "Bad Config", has_buildings=False, has_floors=True)

    def test_list_projects_by_tenant(self, service, tenant_id, other_tenant_id):
        service.create_project(tenant_id, "Project A")
        service.create_project(tenant_id, "Project B")
        service.create_project(other_tenant_id, "Other Tenant Project")

        projects = service.list_projects(tenant_id)
        assert len(projects) == 2
        names = {p.name for p in projects}
        assert "Project A" in names
        assert "Project B" in names

    def test_get_project_tenant_isolation(self, service, tenant_id, other_tenant_id):
        project = service.create_project(tenant_id, "Isolated")
        result = service.get_project(other_tenant_id, project.project_id)
        assert result is None


# ---------------------------------------------------------------------------
# Building tests
# ---------------------------------------------------------------------------

class TestBuildings:
    def _project_with_buildings(self, service, tenant_id):
        return service.create_project(tenant_id, "With Buildings", has_buildings=True)

    def test_add_building(self, service, tenant_id):
        project = self._project_with_buildings(service, tenant_id)
        building = service.add_building(tenant_id, project.project_id, "Building A", code="A")
        assert building.name == "Building A"
        assert building.code == "A"
        assert building.project_id == project.project_id

    def test_add_building_without_config_raises(self, service, tenant_id):
        project = service.create_project(tenant_id, "No Buildings", has_buildings=False)
        with pytest.raises(ValueError, match="does not use buildings"):
            service.add_building(tenant_id, project.project_id, "Building A")

    def test_list_buildings(self, service, tenant_id):
        project = self._project_with_buildings(service, tenant_id)
        service.add_building(tenant_id, project.project_id, "Building A", sort_order=0)
        service.add_building(tenant_id, project.project_id, "Building B", sort_order=1)
        buildings = service.list_buildings(tenant_id, project.project_id)
        assert len(buildings) == 2

    def test_add_building_wrong_project_raises(self, service, tenant_id):
        with pytest.raises(ValueError, match="not found"):
            service.add_building(tenant_id, uuid.uuid4(), "Building X")


# ---------------------------------------------------------------------------
# Floor tests
# ---------------------------------------------------------------------------

class TestFloors:
    def _project_with_floors(self, service, tenant_id):
        return service.create_project(tenant_id, "Full Hierarchy", has_buildings=True, has_floors=True)

    def test_add_floor(self, service, tenant_id):
        project = self._project_with_floors(service, tenant_id)
        building = service.add_building(tenant_id, project.project_id, "Tower A")
        floor = service.add_floor(
            tenant_id, project.project_id, building.building_id,
            "Floor 2", number=2
        )
        assert floor.name == "Floor 2"
        assert floor.number == 2
        assert floor.building_id == building.building_id

    def test_add_floor_without_config_raises(self, service, tenant_id):
        project = service.create_project(tenant_id, "No Floors", has_buildings=True, has_floors=False)
        building = service.add_building(tenant_id, project.project_id, "Building X")
        with pytest.raises(ValueError, match="does not use floors"):
            service.add_floor(tenant_id, project.project_id, building.building_id, "Floor 1")

    def test_add_floor_missing_building_raises(self, service, tenant_id):
        project = self._project_with_floors(service, tenant_id)
        with pytest.raises(ValueError, match="not found"):
            service.add_floor(tenant_id, project.project_id, uuid.uuid4(), "Floor X")


# ---------------------------------------------------------------------------
# UnitType tests
# ---------------------------------------------------------------------------

class TestUnitTypes:
    def test_add_unit_type_standard(self, service, tenant_id):
        project = service.create_project(tenant_id, "Types Project")
        ut = service.add_unit_type(tenant_id, project.project_id, code="A", name="Type A — 2BR/2BA")
        assert ut.code == "A"
        assert ut.name == "Type A — 2BR/2BA"
        assert ut.is_mirror is False
        assert ut.is_ada is False
        assert ut.base_type_id is None

    def test_add_unit_type_mirror_derived(self, service, tenant_id):
        project = service.create_project(tenant_id, "Mirror Test")
        base = service.add_unit_type(tenant_id, project.project_id, code="A", name="Type A")
        mirror = service.add_unit_type(
            tenant_id, project.project_id,
            code="A-MIR", name="Type A Mirror",
            is_mirror=True,
            base_type_id=base.unit_type_id,
        )
        assert mirror.is_mirror is True
        assert mirror.base_type_id == base.unit_type_id

    def test_add_unit_type_ada(self, service, tenant_id):
        project = service.create_project(tenant_id, "ADA Test")
        ada = service.add_unit_type(
            tenant_id, project.project_id,
            code="ADA", name="ADA Accessible",
            is_ada=True,
        )
        assert ada.is_ada is True

    def test_add_unit_type_invalid_base_raises(self, service, tenant_id):
        project = service.create_project(tenant_id, "Bad Base")
        with pytest.raises(ValueError, match="not found"):
            service.add_unit_type(
                tenant_id, project.project_id,
                code="A-MIR", name="Mirror",
                base_type_id=uuid.uuid4(),
            )

    def test_list_unit_types(self, service, tenant_id):
        project = service.create_project(tenant_id, "Multi Types")
        service.add_unit_type(tenant_id, project.project_id, "A", "Type A", sort_order=0)
        service.add_unit_type(tenant_id, project.project_id, "B", "Type B", sort_order=1)
        service.add_unit_type(tenant_id, project.project_id, "ADA", "ADA", sort_order=2, is_ada=True)
        types = service.list_unit_types(tenant_id, project.project_id)
        assert len(types) == 3


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

class TestUnits:
    def test_add_unit_flat(self, service, tenant_id):
        """Flat project — unit has no building or floor."""
        project = service.create_project(tenant_id, "Flat Project")
        unit = service.add_unit(tenant_id, project.project_id, name="Apt 101", code="101")
        assert unit.name == "Apt 101"
        assert unit.code == "101"
        assert unit.building_id is None
        assert unit.floor_id is None
        assert unit.variant == UnitVariant.STANDARD

    def test_add_unit_with_type(self, service, tenant_id):
        project = service.create_project(tenant_id, "Typed Units")
        ut = service.add_unit_type(tenant_id, project.project_id, "A", "Type A")
        unit = service.add_unit(
            tenant_id, project.project_id,
            name="Apt 201", code="201",
            unit_type_id=ut.unit_type_id,
        )
        assert unit.unit_type_id == ut.unit_type_id

    def test_add_unit_mirror_variant(self, service, tenant_id):
        project = service.create_project(tenant_id, "MIR Test")
        unit = service.add_unit(
            tenant_id, project.project_id,
            name="Apt 301-MIR", code="301",
            variant=UnitVariant.MIRROR,
        )
        assert unit.variant == UnitVariant.MIRROR

    def test_add_unit_ada_variant(self, service, tenant_id):
        project = service.create_project(tenant_id, "ADA Units")
        unit = service.add_unit(
            tenant_id, project.project_id,
            name="Apt ADA-1", code="ADA1",
            variant=UnitVariant.ADA,
        )
        assert unit.variant == UnitVariant.ADA

    def test_add_unit_with_building(self, service, tenant_id):
        project = service.create_project(tenant_id, "Building Units", has_buildings=True)
        building = service.add_building(tenant_id, project.project_id, "Building A")
        unit = service.add_unit(
            tenant_id, project.project_id,
            name="Apt A-101", code="A101",
            building_id=building.building_id,
        )
        assert unit.building_id == building.building_id

    def test_add_unit_building_without_config_raises(self, service, tenant_id):
        project = service.create_project(tenant_id, "No Buildings", has_buildings=False)
        with pytest.raises(ValueError, match="project does not use buildings"):
            service.add_unit(
                tenant_id, project.project_id,
                name="Apt 101", code="101",
                building_id=uuid.uuid4(),
            )

    def test_add_unit_floor_without_building_raises(self, service, tenant_id):
        project = service.create_project(tenant_id, "Floor Req", has_buildings=True, has_floors=True)
        with pytest.raises(ValueError, match="floor_id requires building_id"):
            service.add_unit(
                tenant_id, project.project_id,
                name="Apt 101", code="101",
                floor_id=uuid.uuid4(),
            )

    def test_list_units_tenant_scoped(self, service, tenant_id, other_tenant_id):
        project = service.create_project(tenant_id, "My Project")
        service.add_unit(tenant_id, project.project_id, "Apt 1", "1")
        service.add_unit(tenant_id, project.project_id, "Apt 2", "2")
        units = service.list_units(tenant_id, project.project_id)
        assert len(units) == 2
        # Other tenant cannot see these units
        units_other = service.list_units(other_tenant_id, project.project_id)
        assert len(units_other) == 0


# ---------------------------------------------------------------------------
# ProjectTree tests
# ---------------------------------------------------------------------------

class TestProjectTree:
    def test_project_tree_flat(self, service, tenant_id):
        project = service.create_project(tenant_id, "Flat")
        ut = service.add_unit_type(tenant_id, project.project_id, "A", "Type A")
        service.add_unit(tenant_id, project.project_id, "Apt 101", "101", unit_type_id=ut.unit_type_id)
        service.add_unit(tenant_id, project.project_id, "Apt 102", "102", unit_type_id=ut.unit_type_id)
        service.add_unit(tenant_id, project.project_id, "Apt 201", "201")

        tree = service.build_project_tree(tenant_id, project.project_id)
        assert tree is not None
        assert tree.total_units == 3
        assert len(tree.unit_types) == 1
        assert tree.unit_types[0].quantity == 2  # Type A has 2 units

    def test_project_tree_not_found_returns_none(self, service, tenant_id):
        tree = service.build_project_tree(tenant_id, uuid.uuid4())
        assert tree is None

    def test_project_tree_with_multiple_types(self, service, tenant_id):
        project = service.create_project(tenant_id, "Multi-Type")
        type_a = service.add_unit_type(tenant_id, project.project_id, "A", "Type A")
        type_b = service.add_unit_type(tenant_id, project.project_id, "B", "Type B")
        type_ada = service.add_unit_type(tenant_id, project.project_id, "ADA", "ADA", is_ada=True)

        # 3× Type A, 2× Type B, 1× ADA
        for i in range(3):
            service.add_unit(tenant_id, project.project_id, f"Apt A-{i}", f"A{i}", unit_type_id=type_a.unit_type_id)
        for i in range(2):
            service.add_unit(tenant_id, project.project_id, f"Apt B-{i}", f"B{i}", unit_type_id=type_b.unit_type_id)
        service.add_unit(tenant_id, project.project_id, "ADA-1", "ADA1", unit_type_id=type_ada.unit_type_id, variant=UnitVariant.ADA)

        tree = service.build_project_tree(tenant_id, project.project_id)
        assert tree.total_units == 6

        type_groups = {tg.unit_type.code: tg.quantity for tg in tree.unit_types}
        assert type_groups["A"] == 3
        assert type_groups["B"] == 2
        assert type_groups["ADA"] == 1
