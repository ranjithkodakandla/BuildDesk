"""
Background task for PDF package generation (Phase 7, hardened Phase 15).
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from app.db.session import SessionLocal
from app.models.fabrication import Assembly
from app.models.project_package import ProjectPackageStatus
from app.models.tenant import Tenant
from app.repositories.fabrication_repository import FabricationRepository
from app.repositories.hierarchy_repository import ProjectHierarchyRepository
from app.repositories.package_repository import PackageRepository
from app.repositories.sqlalchemy_repo import SQLTenantRepository
from app.services.package_generator_service import PackageGeneratorService
from app.services.cloud_storage import CloudStorageService
from app.exporters.package_pdf_exporter import PackagePdfExporter

logger = logging.getLogger(__name__)

MAX_GENERATION_ATTEMPTS = 2


def _mark_generating(pkg_repo: PackageRepository, tenant_id: uuid.UUID, package_id: uuid.UUID) -> None:
    record = pkg_repo._get_record(tenant_id, package_id)
    if record:
        record.status = ProjectPackageStatus.GENERATING.value
        record.generation_error = None
        pkg_repo.session.commit()


def _mark_failed(
    pkg_repo: PackageRepository,
    tenant_id: uuid.UUID,
    package_id: uuid.UUID,
    error_message: str,
    attempts: int,
) -> None:
    record = pkg_repo._get_record(tenant_id, package_id)
    if record:
        record.status = ProjectPackageStatus.GENERATION_FAILED.value
        record.generation_error = error_message[:2000]
        record.generation_attempts = attempts
        record.storage_reference = None
        record.file_size_bytes = None
        pkg_repo.session.commit()


def _mark_ready(
    pkg_repo: PackageRepository,
    tenant_id: uuid.UUID,
    package_id: uuid.UUID,
    storage_ref: str,
    file_size: int,
    attempts: int,
) -> None:
    record = pkg_repo._get_record(tenant_id, package_id)
    if record:
        record.status = ProjectPackageStatus.READY.value
        record.storage_reference = storage_ref
        record.file_size_bytes = file_size
        record.generated_at = datetime.now(timezone.utc)
        record.generation_error = None
        record.generation_attempts = attempts
        pkg_repo.session.commit()


def _load_tenant(tenant_repo: SQLTenantRepository, tenant_id: uuid.UUID) -> Tenant:
    tenant = tenant_repo.get_by_id(tenant_id)
    if tenant:
        return tenant
    tenant = Tenant(
        tenant_id=tenant_id,
        name="BuildDesk Tenant",
        slug=f"tenant-{str(tenant_id)[:8]}",
        contact_email="ops@example.com",
    )
    tenant_repo.save(tenant)
    return tenant


def _build_assemblies_map(
    fab_repo: FabricationRepository,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
) -> Dict[str, List[Assembly]]:
    assemblies_by_type: Dict[str, List[Assembly]] = {}
    for asm in fab_repo.list_assemblies(tenant_id, project_id):
        if not asm.unit_type_id:
            continue
        full_asm = fab_repo.get_assembly(tenant_id, asm.assembly_id)
        if not full_asm:
            continue
        key = f"{asm.unit_type_id}::{asm.assembly_type.value}"
        assemblies_by_type.setdefault(key, []).append(full_asm)
    return assemblies_by_type


def _generate_pdf_once(
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    package_id: uuid.UUID,
) -> Tuple[bytes, str]:
    """Run one generation attempt. Returns (pdf_bytes, storage_reference)."""
    db = SessionLocal()
    try:
        hierarchy_repo = ProjectHierarchyRepository(db)
        fab_repo = FabricationRepository(db)
        svc = PackageGeneratorService(db)
        pkg_repo = PackageRepository(db)
        tenant_repo = SQLTenantRepository(db)
        storage_svc = CloudStorageService()

        db_package = pkg_repo.get_package(tenant_id, package_id)
        if not db_package:
            raise ValueError(f"Package {package_id} not found.")

        project = hierarchy_repo.get_project(tenant_id, project_id)
        if not project:
            raise ValueError("Project not found for tenant.")

        if db_package.project_id != project_id:
            raise ValueError("Package does not belong to the specified project.")

        tenant = _load_tenant(tenant_repo, tenant_id)
        groups = svc.get_unit_type_groups(tenant_id, project_id)
        summary = svc.get_summary(tenant_id, project_id)
        assemblies_by_type = _build_assemblies_map(fab_repo, tenant_id, project_id)

        exporter = PackagePdfExporter()
        pdf_bytes = exporter.export(
            project=project,
            package=db_package,
            tenant=tenant,
            unit_type_groups=groups,
            assemblies_by_type=assemblies_by_type,
            summary=summary,
        )
        if not pdf_bytes:
            raise ValueError("PDF exporter returned empty bytes.")

        storage_ref = storage_svc.upload_pdf(project_id, package_id, pdf_bytes)
        return pdf_bytes, storage_ref
    finally:
        db.close()


def generate_pdf_background(
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    package_id: uuid.UUID,
) -> None:
    """
    Background worker: generates PDF with bounded retries and persists failure metadata.
    """
    db = SessionLocal()
    pkg_repo = PackageRepository(db)
    try:
        if not pkg_repo.get_package(tenant_id, package_id):
            logger.error("Package %s not found for tenant %s", package_id, tenant_id)
            return

        _mark_generating(pkg_repo, tenant_id, package_id)

        last_error: Optional[str] = None
        for attempt in range(1, MAX_GENERATION_ATTEMPTS + 1):
            try:
                pdf_bytes, storage_ref = _generate_pdf_once(tenant_id, project_id, package_id)
                _mark_ready(
                    pkg_repo,
                    tenant_id,
                    package_id,
                    storage_ref,
                    len(pdf_bytes),
                    attempt,
                )
                logger.info(
                    "Package %s generated successfully (attempt %s/%s)",
                    package_id,
                    attempt,
                    MAX_GENERATION_ATTEMPTS,
                )
                return
            except Exception as exc:
                last_error = str(exc)
                logger.warning(
                    "Package %s generation attempt %s/%s failed: %s",
                    package_id,
                    attempt,
                    MAX_GENERATION_ATTEMPTS,
                    exc,
                )
                db.rollback()
                pkg_repo = PackageRepository(db)

        _mark_failed(
            pkg_repo,
            tenant_id,
            package_id,
            last_error or "Unknown generation error",
            MAX_GENERATION_ATTEMPTS,
        )
        logger.error("Package %s failed after %s attempts", package_id, MAX_GENERATION_ATTEMPTS)
    except Exception as exc:
        logger.exception("Unhandled failure generating package %s: %s", package_id, exc)
        db.rollback()
        try:
            pkg_repo = PackageRepository(db)
            _mark_failed(pkg_repo, tenant_id, package_id, str(exc), MAX_GENERATION_ATTEMPTS)
        except Exception as fallback_exc:
            logger.error("Failed to persist generation_failed state: %s", fallback_exc)
    finally:
        db.close()
