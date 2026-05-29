"""
Package API Schemas  (Phase 3)
================================
Pydantic schemas for the /projects/{id}/package and /assemblies/{id}/preview/svg endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.project_package import PackagePageType, ProjectPackageStatus


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class PackageGenerateRequest(BaseModel):
    version:           str          = Field(default="1.0",  max_length=50)
    issued_by:         Optional[str] = Field(default=None,  max_length=200)
    revision_notes:    Optional[str] = Field(default=None)

class PackageTransitionRequest(BaseModel):
    status:            ProjectPackageStatus = Field(...)
    review_notes:      Optional[str] = Field(default=None)


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class PackagePageResponse(BaseModel):
    page_id:     uuid.UUID
    page_number: int
    page_type:   PackagePageType
    title:       str
    content_ref: str

    model_config = {"from_attributes": True}


class PackageResponse(BaseModel):
    package_id:        uuid.UUID
    project_id:        uuid.UUID
    tenant_id:         uuid.UUID
    version:           str
    issued_by:         Optional[str]
    issued_date:       Optional[datetime]
    revision_notes:    Optional[str]
    status:            ProjectPackageStatus
    storage_reference: Optional[str]
    generated_at:      Optional[datetime]
    
    approved_by:       Optional[str]
    approved_at:       Optional[datetime]
    review_notes:      Optional[str]
    generation_error:  Optional[str] = None
    generation_attempts: int = 0
    
    page_count:        int
    pages:             List[PackagePageResponse]

    model_config = {"from_attributes": True}


class PackageListResponse(BaseModel):
    packages: List[PackageResponse]
    total:    int
