"""
Search Repository (Phase 14)
===========================
"""

import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, cast, String

from app.api.search_schemas import SearchQueryRequest, SearchResultItem
from app.db.models import (
    ProjectRecord, UnitRecord, AssemblyRecord, 
    ProjectPackageRecord, RFIRecord
)


class SearchRepository:
    def __init__(self, session: Session):
        self.session = session

    def search(self, tenant_id: uuid.UUID, params: SearchQueryRequest) -> List[SearchResultItem]:
        results: List[SearchResultItem] = []
        tid = str(tenant_id)
        
        types = params.entity_types or ["projects", "units", "assemblies", "packages", "rfis"]
        q = params.query.lower().strip() if params.query else ""
        
        pid = str(params.project_id) if params.project_id else None

        # 1. Projects
        if "projects" in types and not pid:
            query = self.session.query(ProjectRecord).filter(ProjectRecord.tenant_id == tid)
            if q:
                query = query.filter(or_(
                    ProjectRecord.name.ilike(f"%{q}%"),
                    ProjectRecord.client_name.ilike(f"%{q}%"),
                    ProjectRecord.address.ilike(f"%{q}%")
                ))
            if params.status:
                query = query.filter(ProjectRecord.status == params.status)
                
            for rec in query.limit(50).all():
                results.append(SearchResultItem(
                    id=uuid.UUID(rec.id),
                    entity_type="project",
                    title=rec.name,
                    subtitle=rec.client_name or "",
                    project_id=uuid.UUID(rec.id),
                    status=rec.status,
                    created_at=rec.created_at,
                    metadata={"address": rec.address, "material": rec.material}
                ))

        # 2. Units
        if "units" in types:
            query = self.session.query(UnitRecord).filter(UnitRecord.tenant_id == tid)
            if pid: query = query.filter(UnitRecord.project_id == pid)
            if q:
                query = query.filter(or_(
                    UnitRecord.name.ilike(f"%{q}%"),
                    UnitRecord.code.ilike(f"%{q}%")
                ))
            if params.building_id:
                query = query.filter(UnitRecord.building_id == str(params.building_id))
            if params.floor_id:
                query = query.filter(UnitRecord.floor_id == str(params.floor_id))
            if params.unit_type_id:
                query = query.filter(UnitRecord.unit_type_id == str(params.unit_type_id))
                
            for rec in query.limit(50).all():
                results.append(SearchResultItem(
                    id=uuid.UUID(rec.id),
                    entity_type="unit",
                    title=rec.name,
                    subtitle=rec.code,
                    project_id=uuid.UUID(rec.project_id),
                    created_at=rec.created_at,
                    metadata={"variant": rec.variant}
                ))

        # 3. Assemblies
        if "assemblies" in types:
            query = self.session.query(AssemblyRecord).filter(AssemblyRecord.tenant_id == tid)
            if pid: query = query.filter(AssemblyRecord.project_id == pid)
            if q:
                query = query.filter(or_(
                    AssemblyRecord.name.ilike(f"%{q}%"),
                    AssemblyRecord.assembly_type.ilike(f"%{q}%")
                ))
            if params.assembly_type:
                query = query.filter(AssemblyRecord.assembly_type == params.assembly_type)
                
            for rec in query.limit(50).all():
                results.append(SearchResultItem(
                    id=uuid.UUID(rec.id),
                    entity_type="assembly",
                    title=rec.name,
                    subtitle=rec.assembly_type,
                    project_id=uuid.UUID(rec.project_id),
                    created_at=rec.created_at,
                    metadata={"variant": rec.variant}
                ))
                
        # 4. Packages
        if "packages" in types:
            query = self.session.query(ProjectPackageRecord).filter(ProjectPackageRecord.tenant_id == tid)
            if pid: query = query.filter(ProjectPackageRecord.project_id == pid)
            if q:
                query = query.filter(or_(
                    ProjectPackageRecord.version.ilike(f"%{q}%"),
                    ProjectPackageRecord.revision_notes.ilike(f"%{q}%")
                ))
            if params.status:
                query = query.filter(ProjectPackageRecord.status == params.status)
                
            for rec in query.limit(50).all():
                results.append(SearchResultItem(
                    id=uuid.UUID(rec.id),
                    entity_type="package",
                    title=f"Package {rec.version}",
                    subtitle=rec.revision_notes or "",
                    project_id=uuid.UUID(rec.project_id),
                    status=rec.status,
                    created_at=rec.created_at,
                    metadata={"page_count": rec.page_count}
                ))

        # 5. RFIs
        if "rfis" in types:
            query = self.session.query(RFIRecord).filter(RFIRecord.tenant_id == tid)
            if pid: query = query.filter(RFIRecord.project_id == pid)
            if q:
                query = query.filter(or_(
                    RFIRecord.title.ilike(f"%{q}%"),
                    RFIRecord.question.ilike(f"%{q}%"),
                    cast(RFIRecord.number, String).ilike(f"%{q}%")
                ))
            if params.status:
                query = query.filter(RFIRecord.status == params.status)
                
            for rec in query.limit(50).all():
                results.append(SearchResultItem(
                    id=uuid.UUID(rec.id),
                    entity_type="rfi",
                    title=f"RFI-{rec.number}: {rec.title}",
                    subtitle=rec.question[:100],
                    project_id=uuid.UUID(rec.project_id),
                    status=rec.status,
                    created_at=rec.created_at,
                    metadata={}
                ))

        return results
