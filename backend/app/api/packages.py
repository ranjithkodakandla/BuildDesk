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

@router.post("/projects/{project_id}/package/generate", response_model=PackageResponse)
def generate_package(
    project_id: uuid.UUID,
    body: PackageGenerateRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    _user: User = Depends(require_active_user),
    svc: PackageGeneratorService = Depends(get_package_service),
):
    """
    Generate a complete multi-page fabrication package for the project.
    Traverses: Project → Units → UnitTypes → Assemblies → Parts → Pages.
    Returns the package manifest (page list). PDF download is a separate endpoint.
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


@router.get("/projects/{project_id}/package/pdf")
def download_package_pdf(
    project_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    _user: User = Depends(require_active_user),
    svc: PackageGeneratorService = Depends(get_package_service),
    fab_repo: FabricationRepository = Depends(get_fab_repo),
    hierarchy_repo: ProjectHierarchyRepository = Depends(get_hierarchy_repo),
):
    """
    Generate and stream the full fabrication package PDF.
    The PDF is built on-the-fly from the latest saved package manifest + live data.
    """
    # 1. Get the latest package to confirm it exists
    package = svc.get_latest_for_project(tenant_id, project_id)
    if not package:
        raise HTTPException(
            status_code=404,
            detail="No package found. Call POST /package/generate first."
        )

    # 2. Load project
    project = hierarchy_repo.get_project(tenant_id, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    # 3. Build UnitTypeGroups and assemblies map for the exporter
    groups = svc.get_unit_type_groups(tenant_id, project_id)
    all_assemblies = fab_repo.list_assemblies(tenant_id, project_id)
    summary = svc.get_summary(tenant_id, project_id)

    # Build assemblies map: unit_type_id::assembly_type → [Assembly, ...]
    assemblies_by_type: Dict[str, List[Assembly]] = {}
    for asm in all_assemblies:
        if asm.unit_type_id:
            # Load full assembly (with parts)
            full_asm = fab_repo.get_assembly(tenant_id, asm.assembly_id)
            if full_asm:
                key = f"{asm.unit_type_id}::{asm.assembly_type.value}"
                assemblies_by_type.setdefault(key, []).append(full_asm)

    # 4. Generate PDF bytes
    exporter = PackagePdfExporter()
    pdf_bytes = exporter.export(
        project=project,
        unit_type_groups=groups,
        assemblies_by_type=assemblies_by_type,
        summary=summary,
        version=package.version,
    )

    safe_name = project.name.replace(" ", "_").replace("/", "-")
    filename = f"{safe_name}_v{package.version}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


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
