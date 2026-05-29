"""
Tenant profile schemas (Phase 14).
"""

from __future__ import annotations

import uuid
from typing import Optional

from pydantic import BaseModel, Field


class TenantProfileRequest(BaseModel):
    company_name: Optional[str] = Field(default=None, max_length=255)
    logo_url: Optional[str] = Field(default=None, max_length=1000)
    default_footer: Optional[str] = Field(default=None, max_length=500)
    standard_notes: Optional[str] = Field(default=None)


class TenantProfileResponse(TenantProfileRequest):
    tenant_id: uuid.UUID
    name: str
