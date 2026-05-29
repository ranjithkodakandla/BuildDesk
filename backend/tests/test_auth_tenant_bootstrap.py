"""Auth must bootstrap tenant row before user insert (Cloud SQL FK)."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import TenantRecord, UserRecord
from app.auth.dependencies import get_user_repository
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


def test_register_creates_tenant_row(client):
    test_client, session = client
    tenant_id = str(uuid.uuid4())
    res = test_client.post(
        "/api/v1/auth/register",
        json={"email": "new@example.com", "password": "password123", "role": "admin"},
        headers={"X-Tenant-ID": tenant_id},
    )
    assert res.status_code == 201, res.text
    assert session.query(TenantRecord).filter(TenantRecord.id == tenant_id).count() == 1
    assert session.query(UserRecord).filter(UserRecord.tenant_id == tenant_id).count() == 1
