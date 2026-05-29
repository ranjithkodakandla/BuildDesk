import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.export_schemas import ExportJobRequest, ExportJobResponse
from app.auth.dependencies import get_current_tenant, require_active_user
from app.dependencies import get_db
from app.models.user import User
from app.repositories.hierarchy_repository import ProjectHierarchyRepository
from app.repositories.fabrication_repository import FabricationRepository
from app.repositories.export_repository import ExportRepository
from app.services.hierarchy_service import HierarchyService
from app.services.fabrication_service import FabricationService
from app.services.export_service import ExportService
from app.models.exports import ExportStatus

router = APIRouter(prefix="/projects/{project_id}/exports", tags=["Exports"])

def get_export_service(db: Session = Depends(get_db)) -> ExportService:
    export_repo = ExportRepository(db)
    hierarchy_repo = ProjectHierarchyRepository(db)
    fab_repo = FabricationRepository(db)
    hierarchy_svc = HierarchyService(hierarchy_repo)
    fab_svc = FabricationService(fab_repo, hierarchy_repo)
    return ExportService(export_repo, hierarchy_svc, fab_svc)


def _map_job_out(job) -> ExportJobResponse:
    return ExportJobResponse(
        job_id=job.job_id,
        project_id=job.project_id,
        tenant_id=job.tenant_id,
        export_type=job.export_type,
        format=job.format,
        status=job.status,
        file_path=job.file_path,
        error_log=job.error_log,
        created_at=job.created_at,
        updated_at=job.updated_at
    )


@router.post("", response_model=ExportJobResponse, status_code=status.HTTP_201_CREATED)
async def request_export(
    project_id: uuid.UUID,
    body: ExportJobRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    _user: User = Depends(require_active_user),
    svc: ExportService = Depends(get_export_service),
):
    job = svc.request_export(tenant_id, project_id, body.export_type, body.format)
    # Ideally, execution is backgrounded. But since it's Phase 10 MVP and local, 
    # we can just execute synchronously right after creation for simplicity
    # or expose a /execute endpoint like imports. Let's execute synchronously for MVP.
    try:
        job = svc.execute_export(tenant_id, job.job_id)
    except Exception as e:
        # Error is stored in job
        pass
    
    return _map_job_out(job)


@router.get("", response_model=List[ExportJobResponse])
async def list_exports(
    project_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    _user: User = Depends(require_active_user),
    svc: ExportService = Depends(get_export_service),
):
    jobs = svc.export_repo.list_jobs(tenant_id, project_id)
    return [_map_job_out(j) for j in jobs]


@router.get("/{job_id}/download")
async def download_export(
    project_id: uuid.UUID,
    job_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    _user: User = Depends(require_active_user),
    svc: ExportService = Depends(get_export_service),
):
    job = svc.export_repo.get_job(tenant_id, job_id)
    if not job or job.project_id != project_id:
        raise HTTPException(status_code=404, detail="Export job not found")
        
    if job.status != ExportStatus.COMPLETED or not job.file_path:
        raise HTTPException(status_code=400, detail="Export not ready")
        
    from app.services.storage_download import artifact_file_response

    media_type = (
        "text/csv"
        if job.format.value == "csv"
        else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    filename = f"export_{job.export_type.value}_{job.project_id}.{job.format.value}"
    return artifact_file_response(
        job.file_path,
        filename=filename,
        media_type=media_type,
        inline=False,
    )
