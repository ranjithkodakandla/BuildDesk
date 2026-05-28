from app.repositories.geometry_repository import GeometryRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.tenant_repository import TenantRepository
from app.repositories.in_memory import (
    InMemoryGeometryRepository,
    InMemoryProjectRepository,
    InMemoryTenantRepository,
)

# Global singleton instances for in-memory repositories
_geometry_repo = InMemoryGeometryRepository()
_project_repo = InMemoryProjectRepository()
_tenant_repo = InMemoryTenantRepository()

def get_geometry_repository() -> GeometryRepository:
    """Dependency provider for GeometryRepository."""
    return _geometry_repo

def get_project_repository() -> ProjectRepository:
    """Dependency provider for ProjectRepository."""
    return _project_repo

def get_tenant_repository() -> TenantRepository:
    """Dependency provider for TenantRepository."""
    return _tenant_repo
