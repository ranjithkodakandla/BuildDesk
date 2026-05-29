"""
Search Repository (Phase 14)
===========================
"""

import uuid
from datetime import datetime, time
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import cast, or_, String

from app.api.search_schemas import SearchQueryRequest, SearchResultItem
from app.db.models import (
    ProjectRecord, UnitRecord, AssemblyRecord, 
    ProjectPackageRecord, RFIRecord
)


class SearchRepository:
    def __init__(self, session: Session):
        self.session = session

    def _date_bounds(self, params: SearchQueryRequest):
        start = params.date_from
        end = params.date_to
        if start and not isinstance(start, datetime):
            start = datetime.combine(start, time.min)
        if end and not isinstance(end, datetime):
            end = datetime.combine(end, time.max)
        return start, end

    def _apply_date_filter(self, query, column, params: SearchQueryRequest):
        start, end = self._date_bounds(params)
        if start:
            query = query.filter(column >= start)
        if end:
            query = query.filter(column <= end)
        return query

    def search(self, tenant_id: uuid.UUID, params: SearchQueryRequest) -> List[SearchResultItem]:
        results: List[SearchResultItem] = []
        tid = str(tenant_id)
        
        types = params.entity_types or ["projects", "units", "assemblies", "packages", "rfis"]
        types = [t.lower() for t in types]
        q = params.query.lower().strip() if params.query else ""
        
        pid = str(params.project_id) if params.project_id else None
        limit = params.limit

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
            query = self._apply_date_filter(query, ProjectRecord.created_at, params)
                
            for rec in query.order_by(ProjectRecord.updated_at.desc()).limit(limit).all():
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
            if params.status:
                query = query.filter(UnitRecord.status == params.status)
            query = self._apply_date_filter(query, UnitRecord.created_at, params)
                
            for rec in query.order_by(UnitRecord.sort_order.asc(), UnitRecord.code.asc()).limit(limit).all():
                results.append(SearchResultItem(
                    id=uuid.UUID(rec.id),
                    entity_type="unit",
                    title=rec.name,
                    subtitle=rec.code,
                    project_id=uuid.UUID(rec.project_id),
                    status=rec.status,
                    created_at=rec.created_at,
                    metadata={
                        "variant": rec.variant,
                        "building_id": rec.building_id,
                        "floor_id": rec.floor_id,
                        "unit_type_id": rec.unit_type_id,
                    }
                ))

        # 3. Assemblies
        if "assemblies" in types:
            query = self.session.query(AssemblyRecord).filter(AssemblyRecord.tenant_id == tid)
            if pid: query = query.filter(AssemblyRecord.project_id == pid)
            if params.building_id or params.floor_id:
                query = query.outerjoin(UnitRecord, AssemblyRecord.unit_id == UnitRecord.id)
                if params.building_id:
                    query = query.filter(UnitRecord.building_id == str(params.building_id))
                if params.floor_id:
                    query = query.filter(UnitRecord.floor_id == str(params.floor_id))
            if q:
                query = query.filter(or_(
                    AssemblyRecord.name.ilike(f"%{q}%"),
                    AssemblyRecord.assembly_type.ilike(f"%{q}%")
                ))
            if params.unit_type_id:
                query = query.filter(AssemblyRecord.unit_type_id == str(params.unit_type_id))
            if params.assembly_type:
                query = query.filter(AssemblyRecord.assembly_type == params.assembly_type)
            query = self._apply_date_filter(query, AssemblyRecord.created_at, params)
                
            for rec in query.order_by(AssemblyRecord.updated_at.desc()).limit(limit).all():
                results.append(SearchResultItem(
                    id=uuid.UUID(rec.id),
                    entity_type="assembly",
                    title=rec.name,
                    subtitle=rec.assembly_type,
                    project_id=uuid.UUID(rec.project_id),
                    created_at=rec.created_at,
                    metadata={
                        "variant": rec.variant,
                        "unit_id": rec.unit_id,
                        "unit_type_id": rec.unit_type_id,
                    }
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
            query = self._apply_date_filter(query, ProjectPackageRecord.created_at, params)
                
            for rec in query.order_by(ProjectPackageRecord.created_at.desc()).limit(limit).all():
                results.append(SearchResultItem(
                    id=uuid.UUID(rec.id),
                    entity_type="package",
                    title=f"Package {rec.version}",
                    subtitle=rec.revision_notes or "",
                    project_id=uuid.UUID(rec.project_id),
                    status=rec.status,
                    created_at=rec.created_at,
                    metadata={
                        "page_count": rec.page_count,
                        "version": rec.version,
                        "generated_at": rec.generated_at.isoformat() if rec.generated_at else None,
                    }
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
            query = self._apply_date_filter(query, RFIRecord.created_at, params)
                
            for rec in query.order_by(RFIRecord.updated_at.desc()).limit(limit).all():
                results.append(SearchResultItem(
                    id=uuid.UUID(rec.id),
                    entity_type="rfi",
                    title=f"RFI-{rec.number}: {rec.title}",
                    subtitle=rec.question[:100],
                    project_id=uuid.UUID(rec.project_id),
                    status=rec.status,
                    created_at=rec.created_at,
                    metadata={
                        "number": rec.number,
                        "package_id": rec.package_id,
                        "assembly_id": rec.assembly_id,
                        "part_id": rec.part_id,
                    }
                ))

        return results
