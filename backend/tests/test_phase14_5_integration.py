"""
Phase 14.5 — Full integration: tenant profile → async package generation → branded PDF.

Uses HTTP for profile update and package enqueue, real services/repositories,
and the production background worker with SessionLocal patched to the test DB.
"""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from app.exporters.package_pdf_exporter import PackagePdfExporter
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_tenant, require_active_user
from app.db.base import Base
from app.db.models import TenantRecord
from app.dependencies import get_db, get_tenant_repository
from app.main import create_app
from app.models.fabrication import (
    Assembly,
    AssemblyType,
    Dimensions,
    Part,
    PartType,
)
from app.models.hierarchy import UnitVariant
from app.models.user import User
from app.repositories.fabrication_repository import FabricationRepository
from app.repositories.hierarchy_repository import ProjectHierarchyRepository
from app.repositories.sqlalchemy_repo import SQLTenantRepository
from app.services.fabrication_service import FabricationService
from app.services.hierarchy_service import HierarchyService


TENANT_A = uuid.UUID("11111111-1111-1111-1111-111111111111")
TENANT_B = uuid.UUID("22222222-2222-2222-2222-222222222222")

BRAND_COMPANY = "Canyon Surfaces Integration"
BRAND_FOOTER = "PHASE14-5-FOOTER-VERIFY-ALL-DIMENSIONS"
BRAND_NOTES = "PHASE14-5-STANDARD-NOTES-LINE"


@pytest.fixture(scope="function")
def db_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def session_factory(db_engine):
    return sessionmaker(bind=db_engine)


@pytest.fixture
def db_session(session_factory):
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def _make_client(db_session: Session, tenant_id: uuid.UUID) -> TestClient:
    app = create_app()

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_tenant_repository] = lambda: SQLTenantRepository(db_session)
    app.dependency_overrides[get_current_tenant] = lambda: tenant_id
    app.dependency_overrides[require_active_user] = lambda: User(
        tenant_id=tenant_id,
        email="ops@example.com",
        hashed_password="test",
        role="admin",
    )
    return app


def _seed_package_ready_project(
    db_session: Session,
    tenant_id: uuid.UUID,
    *,
    project_name: str = "Integration Tower",
):
    hierarchy_repo = ProjectHierarchyRepository(db_session)
    hierarchy_svc = HierarchyService(hierarchy_repo)
    fab_svc = FabricationService(FabricationRepository(db_session), hierarchy_repo)

    project = hierarchy_svc.create_project(
        tenant_id,
        project_name,
        client_name="Apex Builders",
        material="Quartz 3cm",
    )
    unit_type = hierarchy_svc.add_unit_type(tenant_id, project.project_id, "A1", "Type A1")
    hierarchy_svc.add_unit(
        tenant_id,
        project.project_id,
        "Unit 101",
        "101",
        unit_type_id=unit_type.unit_type_id,
    )

    assembly_id = uuid.uuid4()
    fab_svc.create_assembly(
        Assembly(
            assembly_id=assembly_id,
            project_id=project.project_id,
            tenant_id=tenant_id,
            unit_type_id=unit_type.unit_type_id,
            name="Kitchen A1",
            assembly_type=AssemblyType.KITCHEN,
            variant=UnitVariant.STANDARD,
            parts=[
                Part(
                    part_id=uuid.uuid4(),
                    assembly_id=assembly_id,
                    part_type=PartType.MAIN_TOP,
                    name="Main Top",
                    dimensions=Dimensions(length=96.0, depth=25.5, thickness=1.25),
                )
            ],
        )
    )
    return project


@pytest.fixture
def patched_background_session(session_factory):
    with patch("app.tasks.package_generation.SessionLocal", session_factory):
        yield


def test_tenant_profile_to_async_pdf_branding_and_isolation(
    db_session,
    session_factory,
    patched_background_session,
):
    db_session.add_all([
        TenantRecord(id=str(TENANT_A), name="Tenant A"),
        TenantRecord(id=str(TENANT_B), name="Tenant B"),
    ])
    db_session.commit()

    project_a = _seed_package_ready_project(db_session, TENANT_A)
    project_b = _seed_package_ready_project(db_session, TENANT_B, project_name="Other Tower")

    export_tenants: list = []
    original_export = PackagePdfExporter.export

    def export_spy(self, project, package, tenant, unit_type_groups, assemblies_by_type, summary):
        export_tenants.append(tenant)
        return original_export(
            self, project, package, tenant, unit_type_groups, assemblies_by_type, summary
        )

    app_a = _make_client(db_session, TENANT_A)
    with (
        patch.object(PackagePdfExporter, "export", export_spy),
        TestClient(app_a) as client_a,
    ):
        profile_res = client_a.put(
            "/api/v1/tenant/profile",
            json={
                "company_name": BRAND_COMPANY,
                "logo_url": "placeholder://canyon",
                "default_footer": BRAND_FOOTER,
                "standard_notes": BRAND_NOTES,
            },
        )
        assert profile_res.status_code == 200, profile_res.text

        gen_res = client_a.post(
            f"/api/v1/projects/{project_a.project_id}/package/generate",
            json={"version": "Rev 14.5", "issued_by": "integration@test"},
        )
        assert gen_res.status_code == 200, gen_res.text
        package_id = gen_res.json()["package_id"]

        status_res = client_a.get(
            f"/api/v1/projects/{project_a.project_id}/package/status",
        )
        assert status_res.status_code == 200, status_res.text
        assert status_res.json()["status"] == "ready"

        pdf_res = client_a.get(
            f"/api/v1/projects/{project_a.project_id}/package/pdf",
        )
        assert pdf_res.status_code == 200, pdf_res.text
        assert pdf_res.content[:4] == b"%PDF"

        tenant_repo = SQLTenantRepository(db_session)
        persisted = tenant_repo.get_by_id(TENANT_A)
        assert persisted is not None
        assert persisted.company_name == BRAND_COMPANY
        assert persisted.default_footer == BRAND_FOOTER
        assert persisted.standard_notes == BRAND_NOTES

        assert len(export_tenants) == 1
        exported_tenant = export_tenants[0]
        assert exported_tenant.company_name == BRAND_COMPANY
        assert exported_tenant.default_footer == BRAND_FOOTER
        assert exported_tenant.standard_notes == BRAND_NOTES

        footer_lines: list[str] = []

        class FooterCanvas:
            def setStrokeColor(self, *_): pass
            def setLineWidth(self, *_): pass
            def line(self, *_): pass
            def setFont(self, *_): pass
            def setFillColor(self, *_): pass
            def drawString(self, *_args):
                footer_lines.append(str(_args[-1]))
            def drawRightString(self, *_): pass
            def drawCentredString(self, *_): pass

        PackagePdfExporter()._footer(
            FooterCanvas(), project_a.name, "Rev 14.5", exported_tenant
        )
        assert any(BRAND_COMPANY in line for line in footer_lines)
        assert any(BRAND_FOOTER in line for line in footer_lines)

        search_res = client_a.post(
            "/api/v1/search",
            json={"entity_types": ["packages"], "project_id": str(project_a.project_id)},
        )
        assert search_res.status_code == 200
        assert search_res.json()["total_count"] >= 1
        assert all(
            item["project_id"] == str(project_a.project_id)
            for item in search_res.json()["results"]
        )

    app_a.dependency_overrides.clear()

    export_tenants_b: list = []

    def export_spy_b(self, project, package, tenant, unit_type_groups, assemblies_by_type, summary):
        export_tenants_b.append(tenant)
        return original_export(
            self, project, package, tenant, unit_type_groups, assemblies_by_type, summary
        )

    app_b = _make_client(db_session, TENANT_B)
    with (
        patch.object(PackagePdfExporter, "export", export_spy_b),
        TestClient(app_b) as client_b,
    ):
        gen_b = client_b.post(
            f"/api/v1/projects/{project_b.project_id}/package/generate",
            json={"version": "1.0"},
        )
        assert gen_b.status_code == 200, gen_b.text

        pdf_b = client_b.get(
            f"/api/v1/projects/{project_b.project_id}/package/pdf",
        )
        assert pdf_b.status_code == 200, pdf_b.text
        assert export_tenants_b[0].company_name != BRAND_COMPANY
        assert export_tenants_b[0].default_footer != BRAND_FOOTER

        search_b = client_b.post("/api/v1/search", json={"entity_types": ["packages"]})
        assert search_b.status_code == 200
        assert all(
            item["project_id"] == str(project_b.project_id)
            for item in search_b.json()["results"]
        )
        assert str(package_id) not in {item["id"] for item in search_b.json()["results"]}

    app_b.dependency_overrides.clear()
