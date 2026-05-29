from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

from pydantic import BaseModel, Field


class ImportStatus(str, enum.Enum):
    PENDING = "pending"         # Uploaded, awaiting mapping/parsing
    MAPPED = "mapped"           # Column mapping provided, awaiting validation
    VALIDATING = "validating"   # Parsing and validating data
    VALIDATED = "validated"     # Validation complete, preview ready
    IMPORTING = "importing"     # Writing to database
    COMPLETED = "completed"     # Success
    FAILED = "failed"           # Critical failure


class ImportErrorSeverity(str, enum.Enum):
    WARNING = "warning"
    ERROR = "error"
    FATAL = "fatal"


class ImportRecordError(BaseModel):
    row_index: int
    column: Optional[str] = None
    message: str
    severity: ImportErrorSeverity = ImportErrorSeverity.ERROR


class ImportMapping(BaseModel):
    unit_number_col: Optional[str] = None
    unit_type_col: Optional[str] = None
    building_col: Optional[str] = None
    floor_col: Optional[str] = None


class ImportJob(BaseModel):
    job_id: uuid.UUID
    project_id: uuid.UUID
    tenant_id: uuid.UUID
    
    filename: str
    status: ImportStatus = ImportStatus.PENDING
    
    total_rows: int = 0
    processed_rows: int = 0
    
    error_log: List[ImportRecordError] = Field(default_factory=list)
    column_mapping: Optional[ImportMapping] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
