"""
Phase 15 — Package generation reliability tests.
"""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_tenant, require_active_user
from app.db.base import Base
from app.db.models import TenantRecord
from app.dependencies import get_db, get_tenant_repository
from app.exporters.package_pdf_exporter import PackagePdfExporter
from app.main import create_app
from app.models.fabrication import Assembly, AssemblyType, Dimensions, Part, PartType
from app.models.hierarchy import UnitVariant
from app.models.project_package import ProjectPackageStatus
from app.models.user import User
from app.repositories.fabrication_repository import FabricationRepository
from app.repositories.hierarchy_repository import ProjectHierarchyRepository
from app.repositories.sqlalchemy_repo import SQLTenantRepository
from app.services.fabrication_service import FabricationService
from app.services.hierarchy_service import HierarchyService
from app.tasks import package_generation as gen_module


TENANT_A = uuid.UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _seed(db_session):
    db_session.add(TenantRecord(id=str(TENANT_A), name="Tenant A"))
    db_session.commit()
    hierarchy_repo = ProjectHierarchyRepository(db_session)
    hierarchy_svc = HierarchyService(hierarchy_repo)
    fab_svc = FabricationService(FabricationRepository(db_session), hierarchy_repo)
    project = hierarchy_svc.create_project(TENANT_A, "Tower")
    unit_type = hierarchy_svc.add_unit_type(TENANT_A, project.project_id, "A1", "Type A1")
    hierarchy_svc.add_unit(TENANT_A, project.project_id, "101", "101", unit_type_id=unit_type.unit_type_id)
    assembly_id = uuid.uuid4()
    fab_svc.create_assembly(
        Assembly(
            assembly_id=assembly_id,
            project_id=project.project_id,
            tenant_id=TENANT_A,
            unit_type_id=unit_type.unit_type_id,
            name="Kitchen",
            assembly_type=AssemblyType.KITCHEN,
            variant=UnitVariant.STANDARD,
            parts=[
                Part(
                    part_id=uuid.uuid4(),
                    assembly_id=assembly_id,
                    part_type=PartType.MAIN_TOP,
                    name="Top",
                    dimensions=Dimensions(length=96.0, depth=25.5, thickness=1.25),
                )
            ],
        )
    )
    return project


def _client(db_session):
    app = create_app()

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_tenant_repository] = lambda: SQLTenantRepository(db_session)
    app.dependency_overrides[get_current_tenant] = lambda: TENANT_A
    app.dependency_overrides[require_active_user] = lambda: User(
        tenant_id=TENANT_A,
        email="ops@example.com",
        hashed_password="test",
        role="admin",
    )
    return app


def test_generation_failure_records_error_and_retry_succeeds(db_session, sessionmaker_bind=None):
    project = _seed(db_session)
    session_factory = sessionmaker(bind=db_session.get_bind())
    app = _client(db_session)

    call_count = {"n": 0}
    original_once = gen_module._generate_pdf_once

    def flaky_once(tenant_id, project_id, package_id):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("Simulated PDF render failure")
        return original_once(tenant_id, project_id, package_id)

    with (
        patch.object(gen_module, "SessionLocal", session_factory),
        patch.object(gen_module, "_generate_pdf_once", side_effect=flaky_once),
        TestClient(app) as client,
    ):
        gen = client.post(
            f"/api/v1/projects/{project.project_id}/package/generate",
            json={"version": "1.0"},
        )
        assert gen.status_code == 200
        package_id = gen.json()["package_id"]

        status = client.get(f"/api/v1/projects/{project.project_id}/package/status")
        assert status.status_code == 200
        body = status.json()
        assert body["status"] == "ready"
        assert body["generation_attempts"] == 2
        assert body["generation_error"] is None

    app.dependency_overrides.clear()


def test_generation_failure_after_max_attempts(db_session):
    project = _seed(db_session)
    session_factory = sessionmaker(bind=db_session.get_bind())
    app = _client(db_session)

    with (
        patch.object(gen_module, "SessionLocal", session_factory),
        patch.object(
            gen_module,
            "_generate_pdf_once",
            side_effect=RuntimeError("Permanent failure"),
        ),
        TestClient(app) as client,
    ):
        gen = client.post(
            f"/api/v1/projects/{project.project_id}/package/generate",
            json={"version": "fail-test"},
        )
        package_id = gen.json()["package_id"]
        status = client.get(f"/api/v1/projects/{project.project_id}/package/status")
        assert status.json()["status"] == "generation_failed"
        assert "Permanent failure" in (status.json()["generation_error"] or "")
        assert status.json()["generation_attempts"] == gen_module.MAX_GENERATION_ATTEMPTS

        pdf = client.get(f"/api/v1/projects/{project.project_id}/package/pdf")
        assert pdf.status_code == 409

        retry = client.post(
            f"/api/v1/projects/{project.project_id}/packages/{package_id}/retry-generation",
        )
        assert retry.status_code == 200
        assert retry.json()["status"] == "generating"

    app.dependency_overrides.clear()
