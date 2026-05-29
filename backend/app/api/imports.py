import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from app.api.import_schemas import (
    ImportJobResponse,
    ImportJobMapRequest,
    ImportValidationPreviewResponse,
    ImportExecutionResponse,
    ImportMappingSchema
)
from app.auth.dependencies import get_current_tenant, require_active_user
from app.dependencies import get_db
from app.models.imports import ImportMapping
from app.models.user import User
from app.repositories.hierarchy_repository import ProjectHierarchyRepository
from app.repositories.import_repository import ImportRepository
from app.services.hierarchy_service import HierarchyService
from app.services.import_service import ImportService

router = APIRouter(prefix="/projects/{project_id}/imports", tags=["Imports"])


def _require_import_job(svc: ImportService, tenant_id: uuid.UUID, project_id: uuid.UUID, job_id: uuid.UUID):
    job = svc.import_repo.get_job(tenant_id, job_id)
    if not job or job.project_id != project_id:
        raise HTTPException(status_code=404, detail="Import job not found.")
    return job


def get_import_service(db: Session = Depends(get_db)) -> ImportService:
    import_repo = ImportRepository(db)
    hierarchy_repo = ProjectHierarchyRepository(db)
    hierarchy_svc = HierarchyService(hierarchy_repo)
    return ImportService(import_repo, hierarchy_svc)


def _map_job_out(job) -> ImportJobResponse:
    return ImportJobResponse(
        job_id=job.job_id,
        project_id=job.project_id,
        tenant_id=job.tenant_id,
        filename=job.filename,
        status=job.status.value,
        total_rows=job.total_rows,
        processed_rows=job.processed_rows,
        error_log=[
            {"row_index": e.row_index, "column": e.column, "message": e.message, "severity": e.severity.value}
            for e in job.error_log
        ],
        column_mapping=ImportMappingSchema(**job.column_mapping.model_dump()) if job.column_mapping else None,
        created_at=job.created_at,
        updated_at=job.updated_at
    )


@router.post("", response_model=ImportJobResponse, status_code=status.HTTP_201_CREATED)
async def upload_import_file(
    project_id: uuid.UUID,
    file: UploadFile = File(...),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    _user: User = Depends(require_active_user),
    svc: ImportService = Depends(get_import_service),
):
    # In a real system we would persist the file to cloud storage (like GCS in Phase 7)
    # For this MVP phase, we just create the job. The client will send the file bytes again
    # for validation and execution to avoid complex temp file management locally.
    # We will simulate the file upload by creating the job record.
    job = svc.create_import_job(tenant_id, project_id, file.filename)
    return _map_job_out(job)


@router.put("/{job_id}/mapping", response_model=ImportJobResponse)
def map_import_columns(
    project_id: uuid.UUID,
    job_id: uuid.UUID,
    body: ImportJobMapRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    _user: User = Depends(require_active_user),
    svc: ImportService = Depends(get_import_service),
):
    try:
        _require_import_job(svc, tenant_id, project_id, job_id)
        mapping = ImportMapping(**body.mapping.model_dump())
        job = svc.update_mapping(tenant_id, job_id, mapping)
        return _map_job_out(job)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{job_id}/validate", response_model=ImportValidationPreviewResponse)
async def validate_import(
    project_id: uuid.UUID,
    job_id: uuid.UUID,
    file: UploadFile = File(...),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    _user: User = Depends(require_active_user),
    svc: ImportService = Depends(get_import_service),
):
    _require_import_job(svc, tenant_id, project_id, job_id)
    file_bytes = await file.read()
    try:
        job, valid_rows = svc.validate_import(tenant_id, job_id, file_bytes)
        return ImportValidationPreviewResponse(
            is_valid=len(job.error_log) == 0,
            total_rows=job.total_rows,
            valid_rows=len(valid_rows),
            errors=[
                {"row_index": e.row_index, "column": e.column, "message": e.message, "severity": e.severity.value}
                for e in job.error_log
            ]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{job_id}/execute", response_model=ImportExecutionResponse)
async def execute_import(
    project_id: uuid.UUID,
    job_id: uuid.UUID,
    file: UploadFile = File(...),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    _user: User = Depends(require_active_user),
    svc: ImportService = Depends(get_import_service),
):
    _require_import_job(svc, tenant_id, project_id, job_id)
    file_bytes = await file.read()
    try:
        job = svc.execute_import(tenant_id, job_id, file_bytes)
        return ImportExecutionResponse(
            status=job.status.value,
            units_created=job.processed_rows,
            assemblies_created=0 # Not yet implemented for imports
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
