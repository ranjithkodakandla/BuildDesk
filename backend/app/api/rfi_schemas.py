"""
RFI API Schemas (Phase 13)
========================
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.rfi import RFIStatus


class RFICreateRequest(BaseModel):
    title: str = Field(..., max_length=200)
    question: str = Field(...)
    package_id: Optional[uuid.UUID] = Field(default=None)
    assembly_id: Optional[uuid.UUID] = Field(default=None)
    part_id: Optional[uuid.UUID] = Field(default=None)


class RFIAnswerRequest(BaseModel):
    answer: str = Field(...)
    status: RFIStatus = Field(default=RFIStatus.ANSWERED)


class RFIResponse(BaseModel):
    rfi_id: uuid.UUID
    project_id: uuid.UUID
    tenant_id: uuid.UUID
    package_id: Optional[uuid.UUID]
    assembly_id: Optional[uuid.UUID]
    part_id: Optional[uuid.UUID]
    number: int
    title: str
    question: str
    answer: Optional[str]
    status: RFIStatus
    created_by: str
    created_at: datetime
    answered_by: Optional[str]
    answered_at: Optional[datetime]

    model_config = {"from_attributes": True}


class RFIListResponse(BaseModel):
    rfis: List[RFIResponse]
