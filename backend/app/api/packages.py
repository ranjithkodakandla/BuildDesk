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
        status=pkg.status,
        storage_reference=pkg.storage_reference,
        generated_at=pkg.generated_at,
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
from app.tasks.package_generation import generate_pdf_background

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

    if package.status != "ready" or not package.storage_reference:
        raise HTTPException(status_code=400, detail=f"Package is not ready yet. Status: {package.status}")

    # For local storage fallback, we return a FileResponse
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
    
    # If it was a real signed URL, we would return a RedirectResponse
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
