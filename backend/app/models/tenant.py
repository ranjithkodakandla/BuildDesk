"""
Tenant Model
============
A tenant is the top-level organisational unit in BuildDesk.

Every builder, construction company, or surface contractor operates
as an isolated tenant. All downstream entities (projects, shapes,
geometry, packages) are scoped under a tenant.

Multi-tenant design principles:
- tenant_id is a UUID, not an auto-increment int (portable, non-guessable)
- slug supports future white-label / custom domain routing
- plan enables future SaaS billing tiers
- No Canyon-specific fields; Canyon is just another tenant

Inherits from BaseDomainModel: created_at, updated_at, schema_version, touch()
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Optional

from pydantic import EmailStr, Field

from app.models.base import BaseDomainModel


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TenantPlan(str, Enum):
    """Billing / feature tier for the tenant."""
    trial = "trial"
    starter = "starter"
    professional = "professional"
    enterprise = "enterprise"


class TenantStatus(str, Enum):
    active = "active"
    suspended = "suspended"
    cancelled = "cancelled"


# ---------------------------------------------------------------------------
# Core model
# ---------------------------------------------------------------------------

class Tenant(BaseDomainModel):
    """
    Represents a BuildDesk customer organisation.

    Examples:
        Canyon Surfaces   → tenant_id=<uuid>, slug="canyon-surfaces"
        Builder A         → tenant_id=<uuid>, slug="builder-a"
    """

    tenant_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str = Field(..., min_length=1, max_length=200, description="Legal or trading name of the organisation")
    slug: str = Field(..., min_length=1, max_length=100, description="URL-safe identifier; used for white-label routing")
    contact_email: EmailStr = Field(..., description="Primary contact email for the tenant")
    plan: TenantPlan = Field(default=TenantPlan.trial)
    status: TenantStatus = Field(default=TenantStatus.active)
    
    # Phase 14: Tenant Profile & Customization
    company_name: Optional[str] = Field(default=None, description="Company name displayed on PDFs")
    logo_url: Optional[str] = Field(default=None, description="URL or data URI for the company logo")
    default_footer: Optional[str] = Field(default=None, description="Default footer string for generated PDFs")
    standard_notes: Optional[str] = Field(default=None, description="Default fabrication standard notes")

    # Future StoneDesk interoperability: external tenant mapping
    stonedesk_tenant_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Linked StoneDesk tenant when cross-platform integration is enabled",
    )
