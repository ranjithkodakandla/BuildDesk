import uuid
from typing import Dict, List, Optional

from app.api.schemas import GeometryResponse
from app.models.project import Project
from app.models.tenant import Tenant
from app.repositories.geometry_repository import GeometryRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.tenant_repository import TenantRepository


class InMemoryGeometryRepository(GeometryRepository):
    def __init__(self):
        self._store: Dict[uuid.UUID, GeometryResponse] = {}

    def save(self, geometry: GeometryResponse) -> None:
        self._store[geometry.geometry_id] = geometry

    def get_by_id(self, geometry_id: uuid.UUID) -> Optional[GeometryResponse]:
        return self._store.get(geometry_id)

    def list_by_project(self, project_id: uuid.UUID) -> List[GeometryResponse]:
        return [g for g in self._store.values() if g.project_id == project_id]


class InMemoryProjectRepository(ProjectRepository):
    def __init__(self):
        self._store: Dict[uuid.UUID, Project] = {}

    def save(self, project: Project) -> None:
        self._store[project.project_id] = project

    def get_by_id(self, project_id: uuid.UUID) -> Optional[Project]:
        return self._store.get(project_id)


class InMemoryTenantRepository(TenantRepository):
    def __init__(self):
        self._store: Dict[uuid.UUID, Tenant] = {}

    def save(self, tenant: Tenant) -> None:
        self._store[tenant.tenant_id] = tenant

    def get_by_id(self, tenant_id: uuid.UUID) -> Optional[Tenant]:
        return self._store.get(tenant_id)
