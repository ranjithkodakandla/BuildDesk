import uuid
from typing import List, Optional
from sqlalchemy.orm import Session

from app.api.schemas import GeometryResponse
from app.models.project import Project
from app.models.tenant import Tenant

from app.db.models import GeometryRecord, ProjectRecord, TenantRecord


class SQLGeometryRepository:
    def __init__(self, session: Session):
        self.session = session

    def save(self, geometry: GeometryResponse) -> None:
        geom_id = str(geometry.geometry_id)
        
        shape_type = geometry.shape_type
        
        existing = self.session.query(GeometryRecord).filter(GeometryRecord.id == geom_id).first()
        if existing:
            existing.payload = geometry.model_dump(mode="json")
            existing.shape_type = shape_type
        else:
            record = GeometryRecord(
                id=geom_id,
                project_id=str(geometry.project_id),
                tenant_id=str(geometry.tenant_id),
                shape_type=shape_type,
                payload=geometry.model_dump(mode="json")
            )
            self.session.add(record)
        self.session.commit()

    def get_by_id(self, geometry_id: uuid.UUID) -> Optional[GeometryResponse]:
        record = self.session.query(GeometryRecord).filter(GeometryRecord.id == str(geometry_id)).first()
        if not record:
            return None
        return GeometryResponse.model_validate(record.payload)

    def list_by_project(self, project_id: uuid.UUID) -> List[GeometryResponse]:
        records = self.session.query(GeometryRecord).filter(GeometryRecord.project_id == str(project_id)).all()
        return [GeometryResponse.model_validate(r.payload) for r in records]


class SQLProjectRepository:
    def __init__(self, session: Session):
        self.session = session

    def save(self, project: Project) -> None:
        existing = self.session.query(ProjectRecord).filter(ProjectRecord.id == str(project.id)).first()
        if existing:
            existing.name = project.name
        else:
            record = ProjectRecord(
                id=str(project.id),
                tenant_id=str(project.tenant_id),
                name=project.name
            )
            self.session.add(record)
        self.session.commit()

    def get_by_id(self, project_id: uuid.UUID) -> Optional[Project]:
        record = self.session.query(ProjectRecord).filter(ProjectRecord.id == str(project_id)).first()
        if not record:
            return None
        return Project(id=uuid.UUID(record.id), tenant_id=uuid.UUID(record.tenant_id), name=record.name)

    def list_by_tenant(self, tenant_id: uuid.UUID) -> List[Project]:
        records = self.session.query(ProjectRecord).filter(ProjectRecord.tenant_id == str(tenant_id)).all()
        return [Project(id=uuid.UUID(r.id), tenant_id=uuid.UUID(r.tenant_id), name=r.name) for r in records]


class SQLTenantRepository:
    def __init__(self, session: Session):
        self.session = session

    def save(self, tenant: Tenant) -> None:
        existing = self.session.query(TenantRecord).filter(TenantRecord.id == str(tenant.id)).first()
        if existing:
            existing.name = tenant.name
        else:
            record = TenantRecord(
                id=str(tenant.id),
                name=tenant.name
            )
            self.session.add(record)
        self.session.commit()

    def get_by_id(self, tenant_id: uuid.UUID) -> Optional[Tenant]:
        record = self.session.query(TenantRecord).filter(TenantRecord.id == str(tenant_id)).first()
        if not record:
            return None
        return Tenant(id=uuid.UUID(record.id), name=record.name)
