from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

class ExportStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ExportType(str, enum.Enum):
    SCHEDULE = "schedule"
    FABRICATION = "fabrication"
    SUMMARY = "summary"

class ExportFormat(str, enum.Enum):
    CSV = "csv"
    XLSX = "xlsx"

class ExportJob(BaseModel):
    job_id: uuid.UUID
    project_id: uuid.UUID
    tenant_id: uuid.UUID
    
    export_type: ExportType
    format: ExportFormat
    status: ExportStatus = ExportStatus.PENDING
    
    file_path: Optional[str] = None
    error_log: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
