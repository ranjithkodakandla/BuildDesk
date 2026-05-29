"""
Operational Coordination Models (Phase 13)
========================================
Defines the RFI (Request for Information) model and Field Notes.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import Field

from app.models.base import BaseDomainModel


class RFIStatus(str, Enum):
    OPEN = "open"
    ANSWERED = "answered"
    CLOSED = "closed"
    VOID = "void"


class RFI(BaseDomainModel):
    """
    Request for Information for field coordination and shop clarification.
    Can be linked to a project, a specific package revision, or an assembly.
    """
    rfi_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    project_id: uuid.UUID = Field(...)
    tenant_id: uuid.UUID = Field(...)
    
    # Optional links
    package_id: Optional[uuid.UUID] = Field(default=None)
    assembly_id: Optional[uuid.UUID] = Field(default=None)
    part_id: Optional[uuid.UUID] = Field(default=None)
    
    number: int = Field(..., description="Sequential RFI number per project")
    title: str = Field(..., max_length=200)
    question: str = Field(...)
    answer: Optional[str] = Field(default=None)
    
    status: RFIStatus = Field(default=RFIStatus.OPEN)
    
    created_by: str = Field(..., max_length=200)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    answered_by: Optional[str] = Field(default=None, max_length=200)
    answered_at: Optional[datetime] = Field(default=None)
