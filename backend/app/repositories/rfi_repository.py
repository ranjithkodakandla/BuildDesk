"""
RFI Repository (Phase 13)
========================
SQLAlchemy repository for RFIs.
"""

from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models import RFIRecord
from app.models.rfi import RFI, RFIStatus


def _rfi_from_record(r: RFIRecord) -> RFI:
    return RFI(
        rfi_id=uuid.UUID(r.id),
        project_id=uuid.UUID(r.project_id),
        tenant_id=uuid.UUID(r.tenant_id),
        package_id=uuid.UUID(r.package_id) if r.package_id else None,
        assembly_id=uuid.UUID(r.assembly_id) if r.assembly_id else None,
        part_id=uuid.UUID(r.part_id) if r.part_id else None,
        number=r.number,
        title=r.title,
        question=r.question,
        answer=r.answer,
        status=RFIStatus(r.status),
        created_by=r.created_by,
        created_at=r.created_at,
        answered_by=r.answered_by,
        answered_at=r.answered_at,
    )


class RFIRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_next_number(self, tenant_id: uuid.UUID, project_id: uuid.UUID) -> int:
        max_num = self.session.query(RFIRecord.number).filter(
            RFIRecord.tenant_id == str(tenant_id),
            RFIRecord.project_id == str(project_id)
        ).order_by(RFIRecord.number.desc()).first()
        if max_num and max_num[0]:
            return max_num[0] + 1
        return 1

    def save(self, rfi: RFI) -> RFI:
        r = self.session.query(RFIRecord).filter(
            RFIRecord.id == str(rfi.rfi_id),
            RFIRecord.tenant_id == str(rfi.tenant_id),
        ).first()
        if not r:
            r = RFIRecord(
                id=str(rfi.rfi_id),
                project_id=str(rfi.project_id),
                tenant_id=str(rfi.tenant_id),
                number=rfi.number,
                created_by=rfi.created_by,
                created_at=rfi.created_at,
            )
            self.session.add(r)
        
        r.package_id = str(rfi.package_id) if rfi.package_id else None
        r.assembly_id = str(rfi.assembly_id) if rfi.assembly_id else None
        r.part_id = str(rfi.part_id) if rfi.part_id else None
        r.title = rfi.title
        r.question = rfi.question
        r.answer = rfi.answer
        r.status = rfi.status.value
        r.answered_by = rfi.answered_by
        r.answered_at = rfi.answered_at
        
        self.session.commit()
        return self.get(rfi.tenant_id, rfi.rfi_id)

    def get(self, tenant_id: uuid.UUID, rfi_id: uuid.UUID) -> Optional[RFI]:
        r = self.session.query(RFIRecord).filter(
            RFIRecord.id == str(rfi_id),
            RFIRecord.tenant_id == str(tenant_id),
        ).first()
        if not r:
            return None
        return _rfi_from_record(r)

    def list_for_project(self, tenant_id: uuid.UUID, project_id: uuid.UUID) -> List[RFI]:
        records = self.session.query(RFIRecord).filter(
            RFIRecord.project_id == str(project_id),
            RFIRecord.tenant_id == str(tenant_id),
        ).order_by(RFIRecord.number.desc()).all()
        return [_rfi_from_record(r) for r in records]
