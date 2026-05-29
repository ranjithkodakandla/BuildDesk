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

    def get_by_id(self, tenant_id: uuid.UUID, geometry_id: uuid.UUID) -> Optional[GeometryResponse]:
        record = self.session.query(GeometryRecord).filter(
            GeometryRecord.id == str(geometry_id),
            GeometryRecord.tenant_id == str(tenant_id)
        ).first()
        if not record:
            return None
        return GeometryResponse.model_validate(record.payload)

    def list_by_project(self, tenant_id: uuid.UUID, project_id: uuid.UUID) -> List[GeometryResponse]:
        records = self.session.query(GeometryRecord).filter(
            GeometryRecord.project_id == str(project_id),
            GeometryRecord.tenant_id == str(tenant_id)
        ).all()
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
        tid = str(tenant.tenant_id)
        existing = self.session.query(TenantRecord).filter(TenantRecord.id == tid).first()
        if existing:
            existing.name = tenant.name
            existing.company_name = tenant.company_name
            existing.logo_url = tenant.logo_url
            existing.default_footer = tenant.default_footer
            existing.standard_notes = tenant.standard_notes
        else:
            record = TenantRecord(
                id=tid,
                name=tenant.name,
                company_name=tenant.company_name,
                logo_url=tenant.logo_url,
                default_footer=tenant.default_footer,
                standard_notes=tenant.standard_notes
            )
            self.session.add(record)
        self.session.commit()

    def get_by_id(self, tenant_id: uuid.UUID) -> Optional[Tenant]:
        record = self.session.query(TenantRecord).filter(TenantRecord.id == str(tenant_id)).first()
        if not record:
            return None
        return Tenant(
            tenant_id=uuid.UUID(record.id),
            name=record.name,
            slug=record.name.lower().replace(" ", "-"),
            contact_email="admin@example.com",
            company_name=record.company_name,
            logo_url=record.logo_url,
            default_footer=record.default_footer,
            standard_notes=record.standard_notes
        )
