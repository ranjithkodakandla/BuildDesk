import json
import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models import ImportJobRecord
from app.models.imports import ImportJob, ImportStatus, ImportRecordError, ImportMapping


class ImportRepository:
    def __init__(self, session: Session):
        self.session = session

    def _map_to_domain(self, record: ImportJobRecord) -> ImportJob:
        errors = []
        if record.error_log:
            try:
                err_dicts = json.loads(record.error_log)
                errors = [ImportRecordError(**e) for e in err_dicts]
            except Exception:
                pass
                
        mapping = None
        if record.column_mapping:
            try:
                mapping = ImportMapping(**json.loads(record.column_mapping))
            except Exception:
                pass

        return ImportJob(
            job_id=uuid.UUID(record.id),
            project_id=uuid.UUID(record.project_id),
            tenant_id=uuid.UUID(record.tenant_id),
            filename=record.filename,
            status=ImportStatus(record.status),
            total_rows=record.total_rows,
            processed_rows=record.processed_rows,
            error_log=errors,
            column_mapping=mapping,
            created_at=record.created_at,
            updated_at=record.updated_at
        )

    def _map_to_record(self, job: ImportJob, existing: Optional[ImportJobRecord] = None) -> ImportJobRecord:
        record = existing or ImportJobRecord(id=str(job.job_id))
        record.project_id = str(job.project_id)
        record.tenant_id = str(job.tenant_id)
        record.filename = job.filename
        record.status = job.status.value
        record.total_rows = job.total_rows
        record.processed_rows = job.processed_rows
        
        record.error_log = json.dumps([e.model_dump() for e in job.error_log]) if job.error_log else None
        record.column_mapping = json.dumps(job.column_mapping.model_dump()) if job.column_mapping else None
        
        return record

    def save_job(self, job: ImportJob) -> ImportJob:
        existing = self.session.query(ImportJobRecord).filter(
            ImportJobRecord.id == str(job.job_id),
            ImportJobRecord.tenant_id == str(job.tenant_id)
        ).first()
        
        record = self._map_to_record(job, existing)
        if not existing:
            self.session.add(record)
            
        self.session.commit()
        return self._map_to_domain(record)

    def get_job(self, tenant_id: uuid.UUID, job_id: uuid.UUID) -> Optional[ImportJob]:
        record = self.session.query(ImportJobRecord).filter(
            ImportJobRecord.id == str(job_id),
            ImportJobRecord.tenant_id == str(tenant_id)
        ).first()
        if not record:
            return None
        return self._map_to_domain(record)

    def list_jobs(self, tenant_id: uuid.UUID, project_id: uuid.UUID) -> List[ImportJob]:
        records = self.session.query(ImportJobRecord).filter(
            ImportJobRecord.project_id == str(project_id),
            ImportJobRecord.tenant_id == str(tenant_id)
        ).order_by(ImportJobRecord.created_at.desc()).all()
        return [self._map_to_domain(r) for r in records]
