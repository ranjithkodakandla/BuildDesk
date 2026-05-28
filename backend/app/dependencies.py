import os
from typing import Generator
from fastapi import Depends
from sqlalchemy.orm import Session

from app.repositories.geometry_repository import GeometryRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.tenant_repository import TenantRepository
from app.repositories.in_memory import (
    InMemoryGeometryRepository,
    InMemoryProjectRepository,
    InMemoryTenantRepository,
)
from app.db.session import SessionLocal, init_db
from app.repositories.sqlalchemy_repo import (
    SQLGeometryRepository,
    SQLProjectRepository,
    SQLTenantRepository,
)

# Initialize DB on load for dev purposes
init_db()

# Global singleton instances for in-memory repositories
_geometry_repo = InMemoryGeometryRepository()
_project_repo = InMemoryProjectRepository()
_tenant_repo = InMemoryTenantRepository()

USE_SQL_REPOSITORY = os.getenv("USE_SQL_REPOSITORY", "false").lower() == "true"

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_geometry_repository(db: Session = Depends(get_db)) -> GeometryRepository:
    """Dependency provider for GeometryRepository."""
    if USE_SQL_REPOSITORY:
        return SQLGeometryRepository(db)
    return _geometry_repo

def get_project_repository(db: Session = Depends(get_db)) -> ProjectRepository:
    """Dependency provider for ProjectRepository."""
    if USE_SQL_REPOSITORY:
        return SQLProjectRepository(db)
    return _project_repo

def get_tenant_repository(db: Session = Depends(get_db)) -> TenantRepository:
    """Dependency provider for TenantRepository."""
    if USE_SQL_REPOSITORY:
        return SQLTenantRepository(db)
    return _tenant_repo
