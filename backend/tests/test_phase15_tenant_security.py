"""
Phase 15 — Tenant isolation and auth enforcement tests.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_tenant, require_active_user
from app.db.base import Base
from app.db.models import TenantRecord
from app.dependencies import get_db
from app.main import create_app
from app.models.user import User
from app.services.hierarchy_service import HierarchyService
from app.repositories.hierarchy_repository import ProjectHierarchyRepository


TENANT_A = uuid.UUID("11111111-1111-1111-1111-111111111111")
TENANT_B = uuid.UUID("22222222-2222-2222-2222-222222222222")


@pytest.fixture
def tenant_projects():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    session.add_all([
        TenantRecord(id=str(TENANT_A), name="A"),
        TenantRecord(id=str(TENANT_B), name="B"),
    ])
    session.commit()
    svc = HierarchyService(ProjectHierarchyRepository(session))
    project_a = svc.create_project(TENANT_A, "Project A")
    project_b = svc.create_project(TENANT_B, "Project B")
    yield session, project_a, project_b
    session.close()


def _client_for(session, tenant_id: uuid.UUID) -> TestClient:
    app = create_app()

    def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_tenant] = lambda: tenant_id
    app.dependency_overrides[require_active_user] = lambda: User(
        tenant_id=tenant_id,
        email="user@example.com",
        hashed_password="x",
        role="admin",
    )
    return TestClient(app)


def test_cross_tenant_project_access_denied(tenant_projects):
    session, project_a, _project_b = tenant_projects
    client_b = _client_for(session, TENANT_B)
    try:
        res = client_b.get(f"/api/v1/projects/{project_a.project_id}")
        assert res.status_code == 404
    finally:
        client_b.app.dependency_overrides.clear()


def test_legacy_geometry_requires_auth():
    app = create_app()
    with TestClient(app) as client:
        res = client.post(
            "/api/v1/geometry",
            json={
                "shape_type": "rectangle",
                "project_id": str(uuid.uuid4()),
                "dimensions": {"length": 96, "width": 26},
            },
        )
        assert res.status_code == 401


def test_health_and_demo_remain_public():
    app = create_app()
    with TestClient(app) as client:
        assert client.get("/api/v1/health").status_code == 200
        assert client.get("/api/v1/shapes").status_code == 200
        assert client.get("/api/v1/demo/rectangle").status_code == 200


def test_protected_hierarchy_requires_auth():
    app = create_app()
    with TestClient(app) as client:
        assert client.get("/api/v1/projects").status_code == 401
