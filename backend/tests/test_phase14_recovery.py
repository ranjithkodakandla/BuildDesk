"""
Phase 14 recovery tests.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_tenant, require_active_user
from app.db.base import Base
from app.db.models import (
    AssemblyRecord,
    BuildingRecord,
    CutoutRecord,
    EdgeTreatmentRecord,
    FabricationNoteRecord,
    FloorRecord,
    GeometryRecord,
    HoleRecord,
    PackagePageRecord,
    PartRecord,
    ProjectPackageRecord,
    ProjectRecord,
    RFIRecord,
    SplashRecord,
    TenantRecord,
    UnitRecord,
    UnitTypeRecord,
    UserRecord,
)
from app.dependencies import get_db
from app.main import create_app
from app.models.hierarchy import UnitStatus, UnitVariant
from app.models.user import User
from app.repositories.hierarchy_repository import ProjectHierarchyRepository
from app.services.hierarchy_service import HierarchyService


TENANT_A = uuid.UUID("11111111-1111-1111-1111-111111111111")
TENANT_B = uuid.UUID("22222222-2222-2222-2222-222222222222")


@pytest.fixture(scope="function")
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def client(db_session: Session):
    app = create_app()

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_tenant] = lambda: TENANT_A
    app.dependency_overrides[require_active_user] = lambda: User(
        tenant_id=TENANT_A,
        email="ops@example.com",
        hashed_password="test",
        role="admin",
    )
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _seed_hierarchy(db_session: Session):
    db_session.add_all([
        TenantRecord(id=str(TENANT_A), name="Tenant A"),
        TenantRecord(id=str(TENANT_B), name="Tenant B"),
    ])
    db_session.commit()
    svc = HierarchyService(ProjectHierarchyRepository(db_session))
    project = svc.create_project(
        TENANT_A,
        "Canyon Tower",
        client_name="Apex Builders",
        material="Quartz 3cm",
        has_buildings=True,
        has_floors=True,
    )
    building = svc.add_building(TENANT_A, project.project_id, "Tower A", code="A")
    floor = svc.add_floor(TENANT_A, project.project_id, building.building_id, "Level 2", number=2)
    unit_type = svc.add_unit_type(TENANT_A, project.project_id, "A1", "Type A1")
    units = [
        svc.add_unit(
            TENANT_A,
            project.project_id,
            f"Unit {200 + index}",
            str(200 + index),
            building_id=building.building_id,
            floor_id=floor.floor_id,
            unit_type_id=unit_type.unit_type_id,
            sort_order=index,
        )
        for index in range(1, 6)
    ]
    other = svc.create_project(TENANT_B, "Other Tenant Project")
    svc.add_unit(TENANT_B, other.project_id, "Unit 999", "999")
    return svc, project, building, floor, unit_type, units


def test_search_filters_all_operational_entities_and_tenant_isolation(client, db_session):
    _svc, project, building, floor, unit_type, units = _seed_hierarchy(db_session)
    now = datetime.now(timezone.utc)
    package_id = uuid.uuid4()
    assembly_id = uuid.uuid4()
    db_session.add_all([
        AssemblyRecord(
            id=str(assembly_id),
            project_id=str(project.project_id),
            tenant_id=str(TENANT_A),
            unit_id=str(units[0].unit_id),
            unit_type_id=str(unit_type.unit_type_id),
            name="Kitchen A1",
            assembly_type="kitchen",
            variant="standard",
            created_at=now,
            updated_at=now,
        ),
        ProjectPackageRecord(
            id=str(package_id),
            project_id=str(project.project_id),
            tenant_id=str(TENANT_A),
            version="Rev A",
            status="approved",
            page_count=12,
            created_at=now,
            updated_at=now,
        ),
        RFIRecord(
            id=str(uuid.uuid4()),
            project_id=str(project.project_id),
            tenant_id=str(TENANT_A),
            number=1,
            title="Sink clarification",
            question="Confirm sink model",
            status="open",
            created_by="ops@example.com",
            created_at=now,
            updated_at=now,
        ),
        RFIRecord(
            id=str(uuid.uuid4()),
            project_id=str(project.project_id),
            tenant_id=str(TENANT_B),
            number=99,
            title="Other tenant RFI",
            question="Should never appear",
            status="open",
            created_by="ops@example.com",
            created_at=now,
            updated_at=now,
        ),
    ])
    db_session.commit()

    response = client.post("/api/v1/search", json={
        "query": "",
        "entity_types": ["units", "assemblies"],
        "project_id": str(project.project_id),
        "building_id": str(building.building_id),
        "floor_id": str(floor.floor_id),
        "unit_type_id": str(unit_type.unit_type_id),
    })
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total_count"] >= 2
    assert {item["entity_type"] for item in body["results"]} == {"unit", "assembly"}
    assert all(item["project_id"] == str(project.project_id) for item in body["results"])

    package_response = client.post("/api/v1/search", json={
        "entity_types": ["packages", "rfis"],
        "status": "approved",
        "date_from": (now - timedelta(days=1)).isoformat(),
        "date_to": (now + timedelta(days=1)).isoformat(),
    })
    assert package_response.status_code == 200, package_response.text
    package_body = package_response.json()
    assert [item["entity_type"] for item in package_body["results"]] == ["package"]

    empty_response = client.post("/api/v1/search", json={
        "entity_types": ["rfis"],
        "date_from": (now + timedelta(days=1)).isoformat(),
    })
    assert empty_response.status_code == 200
    assert empty_response.json()["total_count"] == 0


def test_bulk_unit_api_assigns_type_and_archives_at_multifamily_scale(client, db_session):
    _svc, project, _building, _floor, unit_type, units = _seed_hierarchy(db_session)

    response = client.put(f"/api/v1/projects/{project.project_id}/units/bulk", json={
        "unit_ids": [str(unit.unit_id) for unit in units],
        "unit_type_id": str(unit_type.unit_type_id),
        "variant": UnitVariant.MIRROR.value,
        "status": UnitStatus.ARCHIVED.value,
    })
    assert response.status_code == 200, response.text
    assert response.json()["updated_count"] == len(units)

    records = db_session.query(UnitRecord).filter(UnitRecord.tenant_id == str(TENANT_A)).all()
    assert len(records) == 5
    assert all(record.status == "archived" for record in records)
    assert all(record.variant == "MIR" for record in records)

    other_records = db_session.query(UnitRecord).filter(UnitRecord.tenant_id == str(TENANT_B)).all()
    assert len(other_records) == 1
    assert other_records[0].status == "active"


def test_tenant_profile_api_persists_branding_configuration(client, db_session):
    db_session.add(TenantRecord(id=str(TENANT_A), name="Tenant A"))
    db_session.commit()

    response = client.put("/api/v1/tenant/profile", json={
        "company_name": "Canyon Surfaces",
        "logo_url": "placeholder://canyon",
        "default_footer": "FIELD VERIFY ALL DIMENSIONS",
        "standard_notes": "Confirm sink templates\nReview seam layout",
    })
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["company_name"] == "Canyon Surfaces"
    assert body["logo_url"] == "placeholder://canyon"

    get_response = client.get("/api/v1/tenant/profile")
    assert get_response.status_code == 200
    assert get_response.json()["default_footer"] == "FIELD VERIFY ALL DIMENSIONS"
