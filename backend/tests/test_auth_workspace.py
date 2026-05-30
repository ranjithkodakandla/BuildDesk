"""Workspace registration and password-only login."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_user_repository
from app.db.base import Base
from app.db.models import TenantRecord, UserRecord
from app.dependencies import get_db, get_tenant_repository
from app.main import create_app
from app.repositories.sql_user_repo import SQLUserRepository
from app.repositories.sqlalchemy_repo import SQLTenantRepository


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    app = create_app()

    def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_tenant_repository] = lambda: SQLTenantRepository(session)
    app.dependency_overrides[get_user_repository] = lambda: SQLUserRepository(session)
    with TestClient(app) as test_client:
        yield test_client, session
    app.dependency_overrides.clear()
    session.close()


def test_register_workspace_no_tenant_header(client):
    test_client, session = client
    res = test_client.post(
        "/api/v1/auth/register",
        json={
            "workspace_name": "Virgin Surfaces Plant 1",
            "email": "ops@virgin.builddesk.accept",
            "password": "password123",
        },
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["email"] == "ops@virgin.builddesk.accept"
    assert session.query(TenantRecord).count() == 1
    assert session.query(UserRecord).count() == 1


def test_login_without_tenant_header(client):
    test_client, session = client
    test_client.post(
        "/api/v1/auth/register",
        json={
            "workspace_name": "Test Shop",
            "email": "fab@test.shop",
            "password": "password123",
        },
    )
    res = test_client.post(
        "/api/v1/auth/login",
        json={"email": "fab@test.shop", "password": "password123"},
    )
    assert res.status_code == 200, res.text
    assert "access_token" in res.json()


def test_legacy_register_with_tenant_header(client):
    test_client, session = client
    tenant_id = str(uuid.uuid4())
    res = test_client.post(
        "/api/v1/auth/register",
        json={"email": "legacy@test.com", "password": "password123"},
        headers={"X-Tenant-ID": tenant_id},
    )
    assert res.status_code == 201, res.text
    assert session.query(TenantRecord).filter(TenantRecord.id == tenant_id).count() == 1
