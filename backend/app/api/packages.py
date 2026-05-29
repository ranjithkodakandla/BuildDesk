"""
Package API Router  (Phase 3)
================================
JWT-protected endpoints for project fabrication package generation.

Routes:
    POST  /api/v1/projects/{project_id}/package/generate  → generate package
    GET   /api/v1/projects/{project_id}/package/status    → get latest package status
    GET   /api/v1/projects/{project_id}/package/pdf       → download latest package PDF
    GET   /api/v1/assemblies/{assembly_id}/preview/svg    → single assembly SVG preview
"""

from __future__ import annotations

import uuid
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.api.package_schemas import (
    PackageGenerateRequest, PackageListResponse,
    PackagePageResponse, PackageResponse,
)
from app.auth.dependencies import get_current_tenant, require_active_user
from app.dependencies import get_db
from app.exporters.assembly_svg_exporter import AssemblySvgExporter
from app.exporters.package_pdf_exporter import PackagePdfExporter
from app.models.fabrication import Assembly
from app.models.user import User
from app.repositories.fabrication_repository import FabricationRepository
from app.repositories.hierarchy_repository import ProjectHierarchyRepository
from app.repositories.package_repository import PackageRepository
from app.services.package_generator_service import PackageGeneratorService

router = APIRouter(tags=["packages"])


# ---------------------------------------------------------------------------
# Dependency helpers
# ---------------------------------------------------------------------------

def get_package_service(db: Session = Depends(get_db)) -> PackageGeneratorService:
    return PackageGeneratorService(db)


def get_fab_repo(db: Session = Depends(get_db)) -> FabricationRepository:
    return FabricationRepository(db)


def get_hierarchy_repo(db: Session = Depends(get_db)) -> ProjectHierarchyRepository:
    return ProjectHierarchyRepository(db)


def get_package_repo(db: Session = Depends(get_db)) -> PackageRepository:
    return PackageRepository(db)


# ---------------------------------------------------------------------------
# Schema mapper
# ---------------------------------------------------------------------------

def _map_package(pkg) -> PackageResponse:
    return PackageResponse(
        package_id=pkg.package_id,
        project_id=pkg.project_id,
        tenant_id=pkg.tenant_id,
        version=pkg.version,
        issued_by=pkg.issued_by,
        issued_date=pkg.issued_date,
        revision_notes=pkg.revision_notes,
        status=pkg.status,
        storage_reference=pkg.storage_reference,
        generated_at=pkg.generated_at,
        approved_by=pkg.approved_by,
        approved_at=pkg.approved_at,
        review_notes=pkg.review_notes,
        generation_error=pkg.generation_error,
        generation_attempts=pkg.generation_attempts,
        page_count=pkg.page_count,
        pages=[
            PackagePageResponse(
                page_id=p.page_id,
                page_number=p.page_number,
                page_type=p.page_type,
                title=p.title,
                content_ref=p.content_ref,
            ) for p in pkg.pages
        ],
    )


# ---------------------------------------------------------------------------
# Package generation endpoints
# ---------------------------------------------------------------------------

from fastapi import APIRouter, Depends, HTTPException, Response, BackgroundTasks
from fastapi.responses import FileResponse
from app.api.package_schemas import PackageGenerateRequest, PackageResponse, PackageListResponse, PackageTransitionRequest
from app.exporters.assembly_svg_exporter import AssemblySvgExporter
from app.tasks.package_generation import generate_pdf_background
from app.models.project_package import ProjectPackageStatus


def _package_download_guard(package) -> None:
    if package.status == ProjectPackageStatus.GENERATION_FAILED:
        detail = package.generation_error or "Package PDF generation failed."
        raise HTTPException(
            status_code=409,
            detail={
                "message": detail,
                "generation_attempts": package.generation_attempts,
                "status": package.status.value,
            },
        )
    if package.status != ProjectPackageStatus.READY or not package.storage_reference:
        raise HTTPException(
            status_code=400,
            detail={
                "message": f"Package is not ready yet. Status: {package.status.value}",
                "generation_error": package.generation_error,
            },
        )


@router.post("/projects/{project_id}/package/generate", response_model=PackageResponse)
def generate_package(
    project_id: uuid.UUID,
    body: PackageGenerateRequest,
    background_tasks: BackgroundTasks,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    _user: User = Depends(require_active_user),
    svc: PackageGeneratorService = Depends(get_package_service),
):
    """
    Generate a complete multi-page fabrication package for the project.
    Traverses: Project → Units → UnitTypes → Assemblies → Parts → Pages.
    Returns the package manifest and queues the PDF generation in the background.
    """
    try:
        package = svc.generate(
            tenant_id=tenant_id,
            project_id=project_id,
            version=body.version,
            issued_by=body.issued_by,
            revision_notes=body.revision_notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    # Queue background task for PDF rendering
    background_tasks.add_task(
        generate_pdf_background,
        tenant_id=tenant_id,
        project_id=project_id,
        package_id=package.package_id
    )
        
    return _map_package(package)


@router.post(
    "/projects/{project_id}/packages/{package_id}/retry-generation",
    response_model=PackageResponse,
)
def retry_package_generation(
    project_id: uuid.UUID,
    package_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    _user: User = Depends(require_active_user),
    package_repo: PackageRepository = Depends(get_package_repo),
):
    """Re-queue PDF generation for a failed or stuck package."""
    package = package_repo.get_package(tenant_id, package_id)
    if not package or package.project_id != project_id:
        raise HTTPException(status_code=404, detail="Package not found.")
    if package.status not in (
        ProjectPackageStatus.GENERATION_FAILED,
        ProjectPackageStatus.GENERATING,
        ProjectPackageStatus.DRAFT,
    ):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot retry generation for status '{package.status.value}'.",
        )

    background_tasks.add_task(
        generate_pdf_background,
        tenant_id=tenant_id,
        project_id=project_id,
        package_id=package_id,
    )
    package.status = ProjectPackageStatus.GENERATING
    package.generation_error = None
    package_repo.save_package(package)
    return _map_package(package_repo.get_package(tenant_id, package_id))


@router.get("/projects/{project_id}/package/status", response_model=PackageResponse)
def get_package_status(
    project_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    _user: User = Depends(require_active_user),
    svc: PackageGeneratorService = Depends(get_package_service),
):
    """Return the most recently generated package manifest for a project."""
    package = svc.get_latest_for_project(tenant_id, project_id)
    if not package:
        raise HTTPException(status_code=404, detail="No package found for this project.")
    return _map_package(package)


@router.post("/projects/{project_id}/packages/{package_id}/transition", response_model=PackageResponse)
def transition_package_status(
    project_id: uuid.UUID,
    package_id: uuid.UUID,
    body: PackageTransitionRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    user: User = Depends(require_active_user),
    package_repo: PackageRepository = Depends(get_package_repo),
    db: Session = Depends(get_db),
):
    """
    Transition a package status (e.g. submit, approve, reject).
    Records approval metadata if transitioning to APPROVED or REJECTED.
    """
    package = package_repo.get_package(tenant_id, package_id)
    if not package or str(package.project_id) != str(project_id):
        raise HTTPException(status_code=404, detail="Package not found.")
        
    from datetime import datetime, timezone

    package.status = body.status
    if body.review_notes:
        package.review_notes = body.review_notes
        
    if body.status in (ProjectPackageStatus.APPROVED, ProjectPackageStatus.REJECTED):
        package.approved_by = user.email
        package.approved_at = datetime.now(timezone.utc)
        
    package_repo.save_package(package)
    db.commit()
    
    return _map_package(package)


from fastapi.responses import FileResponse

@router.get("/projects/{project_id}/package/download")
@router.get("/projects/{project_id}/package/pdf")
def download_package_pdf(
    project_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    _user: User = Depends(require_active_user),
    svc: PackageGeneratorService = Depends(get_package_service),
):
    """
    Download the generated PDF package.
    Redirects to signed URL or serves local file if in fallback mode.
    """
    package = svc.get_latest_for_project(tenant_id, project_id)
    if not package:
        raise HTTPException(status_code=404, detail="No package found. Call POST /package/generate first.")

    _package_download_guard(package)

    from app.services.cloud_storage import CloudStorageService
    storage_svc = CloudStorageService()
    url_or_path = storage_svc.get_download_url(package.storage_reference)
    
    if package.storage_reference.startswith("local://"):
        return FileResponse(
            path=url_or_path,
            media_type="application/pdf",
            filename=f"package_{package.version}.pdf",
            content_disposition_type="inline"
        )
    
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=url_or_path)


@router.get("/projects/{project_id}/packages", response_model=PackageListResponse)
def list_packages(
    project_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    _user: User = Depends(require_active_user),
    package_repo: PackageRepository = Depends(get_package_repo),
):
    """
    List all generated packages (revisions) for a project.
    """
    packages = package_repo.list_for_project(tenant_id, project_id)
    return PackageListResponse(
        packages=[_map_package(p) for p in packages],
        total=len(packages)
    )


@router.get("/projects/{project_id}/packages/{package_id}/pdf")
def download_specific_package_pdf(
    project_id: uuid.UUID,
    package_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    _user: User = Depends(require_active_user),
    package_repo: PackageRepository = Depends(get_package_repo),
):
    """
    Download a specific generated PDF package revision.
    """
    package = package_repo.get_package(tenant_id, package_id)
    if not package or str(package.project_id) != str(project_id):
        raise HTTPException(status_code=404, detail="Package not found.")

    _package_download_guard(package)

    from app.services.cloud_storage import CloudStorageService
    storage_svc = CloudStorageService()
    url_or_path = storage_svc.get_download_url(package.storage_reference)
    
    if package.storage_reference.startswith("local://"):
        return FileResponse(
            path=url_or_path,
            media_type="application/pdf",
            filename=f"package_{package.version}.pdf",
            content_disposition_type="inline"
        )
    
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=url_or_path)


# ---------------------------------------------------------------------------
# Assembly SVG preview endpoint
# ---------------------------------------------------------------------------

@router.get("/assemblies/{assembly_id}/preview/svg")
def preview_assembly_svg(
    assembly_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    _user: User = Depends(require_active_user),
    fab_repo: FabricationRepository = Depends(get_fab_repo),
):
    """
    Render a single assembly to SVG for rapid visual validation.
    Shows parts, dimensions, cutouts, holes, and splashes to scale.
    """
    assembly = fab_repo.get_assembly(tenant_id, assembly_id)
    if not assembly:
        raise HTTPException(status_code=404, detail="Assembly not found.")

    exporter = AssemblySvgExporter()
    svg_str = exporter.export(assembly)
    return Response(
        content=svg_str.encode("utf-8"),
        media_type="image/svg+xml",
        headers={"Content-Disposition": f'inline; filename="assembly-{assembly_id}.svg"'},
    )
