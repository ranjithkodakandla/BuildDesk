from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

from pydantic import BaseModel, Field


class ImportRecordErrorSchema(BaseModel):
    row_index: int
    column: Optional[str] = None
    message: str
    severity: str


class ImportMappingSchema(BaseModel):
    # e.g. "UnitNumber": "Unit", "Type": "UnitType", "Building": "Building", "Floor": "Floor"
    unit_number_col: Optional[str] = None
    unit_type_col: Optional[str] = None
    building_col: Optional[str] = None
    floor_col: Optional[str] = None


class ImportJobCreateRequest(BaseModel):
    filename: str


class ImportJobResponse(BaseModel):
    job_id: uuid.UUID
    project_id: uuid.UUID
    tenant_id: uuid.UUID
    filename: str
    status: str
    total_rows: int
    processed_rows: int
    error_log: List[ImportRecordErrorSchema] = Field(default_factory=list)
    column_mapping: Optional[ImportMappingSchema] = None
    created_at: datetime
    updated_at: datetime


class ImportJobMapRequest(BaseModel):
    mapping: ImportMappingSchema


class ImportValidationPreviewResponse(BaseModel):
    is_valid: bool
    total_rows: int
    valid_rows: int
    errors: List[ImportRecordErrorSchema]


class ImportExecutionResponse(BaseModel):
    status: str
    units_created: int
    assemblies_created: int
