import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.exports import ExportType, ExportFormat, ExportStatus

class ExportJobRequest(BaseModel):
    export_type: ExportType
    format: ExportFormat

class ExportJobResponse(BaseModel):
    job_id: uuid.UUID
    project_id: uuid.UUID
    tenant_id: uuid.UUID
    export_type: ExportType
    format: ExportFormat
    status: ExportStatus
    file_path: Optional[str] = None
    error_log: Optional[str] = None
    created_at: datetime
    updated_at: datetime
