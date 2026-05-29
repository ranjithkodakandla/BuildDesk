import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models import ExportJobRecord
from app.models.exports import ExportJob, ExportStatus, ExportType, ExportFormat

class ExportRepository:
    def __init__(self, session: Session):
        self.session = session

    def _map_to_domain(self, record: ExportJobRecord) -> ExportJob:
        return ExportJob(
            job_id=uuid.UUID(record.id),
            project_id=uuid.UUID(record.project_id),
            tenant_id=uuid.UUID(record.tenant_id),
            export_type=ExportType(record.export_type),
            format=ExportFormat(record.format),
            status=ExportStatus(record.status),
            file_path=record.file_path,
            error_log=record.error_log,
            created_at=record.created_at,
            updated_at=record.updated_at
        )

    def _map_to_record(self, job: ExportJob, existing: Optional[ExportJobRecord] = None) -> ExportJobRecord:
        record = existing or ExportJobRecord(id=str(job.job_id))
        record.project_id = str(job.project_id)
        record.tenant_id = str(job.tenant_id)
        record.export_type = job.export_type.value
        record.format = job.format.value
        record.status = job.status.value
        record.file_path = job.file_path
        record.error_log = job.error_log
        return record

    def save_job(self, job: ExportJob) -> ExportJob:
        existing = self.session.query(ExportJobRecord).filter(
            ExportJobRecord.id == str(job.job_id),
            ExportJobRecord.tenant_id == str(job.tenant_id)
        ).first()
        
        record = self._map_to_record(job, existing)
        if not existing:
            self.session.add(record)
            
        self.session.commit()
        return self._map_to_domain(record)

    def get_job(self, tenant_id: uuid.UUID, job_id: uuid.UUID) -> Optional[ExportJob]:
        record = self.session.query(ExportJobRecord).filter(
            ExportJobRecord.id == str(job_id),
            ExportJobRecord.tenant_id == str(tenant_id)
        ).first()
        if not record:
            return None
        return self._map_to_domain(record)

    def list_jobs(self, tenant_id: uuid.UUID, project_id: uuid.UUID) -> List[ExportJob]:
        records = self.session.query(ExportJobRecord).filter(
            ExportJobRecord.project_id == str(project_id),
            ExportJobRecord.tenant_id == str(tenant_id)
        ).order_by(ExportJobRecord.created_at.desc()).all()
        return [self._map_to_domain(r) for r in records]
