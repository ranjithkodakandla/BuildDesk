"""
Tenant profile API (Phase 14).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from app.api.tenant_schemas import TenantProfileRequest, TenantProfileResponse
from app.auth.dependencies import get_current_tenant, require_active_user
from app.dependencies import get_tenant_repository
from app.models.tenant import Tenant
from app.models.user import User
from app.repositories.tenant_repository import TenantRepository

router = APIRouter(prefix="/tenant", tags=["tenant"])


def _default_tenant(tenant_id: uuid.UUID, user: User) -> Tenant:
    return Tenant(
        tenant_id=tenant_id,
        name="BuildDesk Tenant",
        slug=f"tenant-{str(tenant_id)[:8]}",
        contact_email=user.email,
    )


def _profile_response(tenant: Tenant) -> TenantProfileResponse:
    return TenantProfileResponse(
        tenant_id=tenant.tenant_id,
        name=tenant.name,
        company_name=tenant.company_name,
        logo_url=tenant.logo_url,
        default_footer=tenant.default_footer,
        standard_notes=tenant.standard_notes,
    )


@router.get("/profile", response_model=TenantProfileResponse)
def get_tenant_profile(
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    user: User = Depends(require_active_user),
    repo: TenantRepository = Depends(get_tenant_repository),
):
    tenant = repo.get_by_id(tenant_id)
    if tenant is None:
        tenant = _default_tenant(tenant_id, user)
        repo.save(tenant)
    return _profile_response(tenant)


@router.put("/profile", response_model=TenantProfileResponse)
def update_tenant_profile(
    body: TenantProfileRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    user: User = Depends(require_active_user),
    repo: TenantRepository = Depends(get_tenant_repository),
):
    tenant = repo.get_by_id(tenant_id) or _default_tenant(tenant_id, user)
    tenant.company_name = body.company_name
    tenant.logo_url = body.logo_url
    tenant.default_footer = body.default_footer
    tenant.standard_notes = body.standard_notes
    if body.company_name:
        tenant.name = body.company_name
    repo.save(tenant)
    return _profile_response(tenant)
