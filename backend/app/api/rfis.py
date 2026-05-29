"""
RFI API Router (Phase 13)
========================
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.api.rfi_schemas import RFICreateRequest, RFIAnswerRequest, RFIResponse, RFIListResponse
from app.auth.dependencies import get_current_tenant, require_active_user
from app.dependencies import get_db
from app.models.rfi import RFI, RFIStatus
from app.models.user import User
from app.repositories.rfi_repository import RFIRepository

router = APIRouter(tags=["rfis"])

def get_rfi_repo(db: Session = Depends(get_db)) -> RFIRepository:
    return RFIRepository(db)

@router.post("/projects/{project_id}/rfis", response_model=RFIResponse)
def create_rfi(
    project_id: uuid.UUID,
    body: RFICreateRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    user: User = Depends(require_active_user),
    repo: RFIRepository = Depends(get_rfi_repo),
):
    number = repo.get_next_number(tenant_id, project_id)
    rfi = RFI(
        project_id=project_id,
        tenant_id=tenant_id,
        package_id=body.package_id,
        assembly_id=body.assembly_id,
        part_id=body.part_id,
        number=number,
        title=body.title,
        question=body.question,
        created_by=user.email,
        created_at=datetime.now(timezone.utc),
    )
    return repo.save(rfi)

@router.get("/projects/{project_id}/rfis", response_model=RFIListResponse)
def list_rfis(
    project_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    user: User = Depends(require_active_user),
    repo: RFIRepository = Depends(get_rfi_repo),
):
    rfis = repo.list_for_project(tenant_id, project_id)
    return RFIListResponse(rfis=rfis)

@router.post("/rfis/{rfi_id}/answer", response_model=RFIResponse)
def answer_rfi(
    rfi_id: uuid.UUID,
    body: RFIAnswerRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    user: User = Depends(require_active_user),
    repo: RFIRepository = Depends(get_rfi_repo),
):
    rfi = repo.get(tenant_id, rfi_id)
    if not rfi:
        raise HTTPException(status_code=404, detail="RFI not found")
        
    rfi.answer = body.answer
    rfi.status = body.status
    rfi.answered_by = user.email
    rfi.answered_at = datetime.now(timezone.utc)
    
    return repo.save(rfi)
