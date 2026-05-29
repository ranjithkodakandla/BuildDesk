"""
Background task for PDF generation.
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, List

from app.db.session import SessionLocal
from app.models.fabrication import Assembly
from app.models.project_package import ProjectPackageStatus
from app.repositories.fabrication_repository import FabricationRepository
from app.repositories.hierarchy_repository import ProjectHierarchyRepository
from app.repositories.package_repository import PackageRepository
from app.repositories.sqlalchemy_repo import SQLTenantRepository
from app.services.package_generator_service import PackageGeneratorService
from app.services.cloud_storage import CloudStorageService
from app.exporters.package_pdf_exporter import PackagePdfExporter

logger = logging.getLogger(__name__)

def generate_pdf_background(
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    package_id: uuid.UUID
):
    """
    Background worker that fetches all data, generates the PDF, uploads to GCS,
    and updates the ProjectPackageRecord.
    """
    db = SessionLocal()
    try:
        hierarchy_repo = ProjectHierarchyRepository(db)
        fab_repo = FabricationRepository(db)
        svc = PackageGeneratorService(db)
        pkg_repo = PackageRepository(db)
        tenant_repo = SQLTenantRepository(db)
        storage_svc = CloudStorageService()

        # Update status to generating
        db_package = pkg_repo.get_package(tenant_id, package_id)
        if not db_package:
            logger.error(f"Package {package_id} not found in DB.")
            return

        db_record = pkg_repo._get_record(tenant_id, package_id)
        if db_record:
            db_record.status = ProjectPackageStatus.GENERATING.value
            db.commit()

        # 1. Load project and tenant
        project = hierarchy_repo.get_project(tenant_id, project_id)
        if not project:
            raise ValueError("Project not found.")
            
        tenant = tenant_repo.get_by_id(tenant_id)
        if not tenant:
            raise ValueError("Tenant not found.")

        # 2. Build UnitTypeGroups and assemblies map for the exporter
        groups = svc.get_unit_type_groups(tenant_id, project_id)
        all_assemblies = fab_repo.list_assemblies(tenant_id, project_id)
        summary = svc.get_summary(tenant_id, project_id)

        # Build assemblies map: unit_type_id::assembly_type → [Assembly, ...]
        assemblies_by_type: Dict[str, List[Assembly]] = {}
        for asm in all_assemblies:
            if asm.unit_type_id:
                full_asm = fab_repo.get_assembly(tenant_id, asm.assembly_id)
                if full_asm:
                    key = f"{asm.unit_type_id}::{asm.assembly_type.value}"
                    assemblies_by_type.setdefault(key, []).append(full_asm)

        # 3. Generate PDF bytes
        exporter = PackagePdfExporter()
        pdf_bytes = exporter.export(
            project=project,
            package=db_package,
            tenant=tenant,
            unit_type_groups=groups,
            assemblies_by_type=assemblies_by_type,
            summary=summary,
        )

        # 4. Upload to Cloud Storage
        storage_ref = storage_svc.upload_pdf(project_id, package_id, pdf_bytes)

        # 5. Update Package Record
        if db_record:
            db_record.status = ProjectPackageStatus.READY.value
            db_record.storage_reference = storage_ref
            db_record.file_size_bytes = len(pdf_bytes)
            db_record.generated_at = datetime.now(timezone.utc)
            db.commit()
        logger.info(f"Successfully generated package {package_id}")

    except Exception as e:
        logger.exception(f"Failed to generate package {package_id}: {e}")
        db.rollback()
        # Try to set status to failed
        try:
            pkg_repo = PackageRepository(db)
            db_package = pkg_repo._get_record(tenant_id, package_id)
            if db_package:
                db_package.status = ProjectPackageStatus.GENERATION_FAILED.value
                db.commit()
        except Exception as fallback_e:
            logger.error(f"Failed to set generation_failed state: {fallback_e}")
    finally:
        db.close()
