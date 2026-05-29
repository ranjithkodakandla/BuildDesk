"""
Package Repository  (Phase 3)
==============================
SQLAlchemy-backed repository for ProjectPackage and PackagePage records.
All methods enforce tenant_id scoping.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models import PackagePageRecord, ProjectPackageRecord
from app.models.project_package import (
    PackagePage, PackagePageType, ProjectPackage, ProjectPackageStatus,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _page_from_record(r: PackagePageRecord) -> PackagePage:
    return PackagePage(
        page_id=uuid.UUID(r.id),
        package_id=uuid.UUID(r.package_id),
        page_number=r.page_number,
        page_type=PackagePageType(r.page_type),
        title=r.title,
        content_ref=r.content_ref,
    )


def _package_from_record(r: ProjectPackageRecord, pages: List[PackagePageRecord]) -> ProjectPackage:
    return ProjectPackage(
        package_id=uuid.UUID(r.id),
        project_id=uuid.UUID(r.project_id),
        tenant_id=uuid.UUID(r.tenant_id),
        version=r.version,
        issued_by=r.issued_by,
        issued_date=r.issued_date,
        revision_notes=r.revision_notes,
        status=ProjectPackageStatus(r.status),
        storage_reference=r.storage_reference,
        generated_at=r.generated_at,
        approved_by=r.approved_by,
        approved_at=r.approved_at,
        review_notes=r.review_notes,
        page_count=r.page_count,
        pages=[_page_from_record(p) for p in sorted(pages, key=lambda x: x.page_number)],
    )


class PackageRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save_package(self, package: ProjectPackage) -> ProjectPackage:
        pkg_str_id = str(package.package_id)
        r = self.session.query(ProjectPackageRecord).filter(
            ProjectPackageRecord.id == pkg_str_id,
            ProjectPackageRecord.tenant_id == str(package.tenant_id),
        ).first()
        if not r:
            r = ProjectPackageRecord(
                id=pkg_str_id, project_id=str(package.project_id),
                tenant_id=str(package.tenant_id), created_at=_utcnow(),
            )
            self.session.add(r)
        r.version = package.version
        r.issued_by = package.issued_by
        r.issued_date = package.issued_date
        r.revision_notes = package.revision_notes
        r.status = package.status.value
        r.storage_reference = package.storage_reference
        r.generated_at = package.generated_at
        r.approved_by = package.approved_by
        r.approved_at = package.approved_at
        r.review_notes = package.review_notes
        r.page_count = package.page_count
        r.updated_at = _utcnow()
        self.session.query(PackagePageRecord).filter(
            PackagePageRecord.package_id == pkg_str_id
        ).delete(synchronize_session=False)
        for page in package.pages:
            self.session.add(PackagePageRecord(
                id=str(page.page_id), package_id=pkg_str_id,
                page_number=page.page_number, page_type=page.page_type.value,
                title=page.title, content_ref=page.content_ref, created_at=_utcnow(),
            ))
        self.session.commit()
        return self.get_package(package.tenant_id, package.package_id)

    def _get_record(self, tenant_id: uuid.UUID, package_id: uuid.UUID) -> Optional[ProjectPackageRecord]:
        return self.session.query(ProjectPackageRecord).filter(
            ProjectPackageRecord.id == str(package_id),
            ProjectPackageRecord.tenant_id == str(tenant_id),
        ).first()

    def get_package(self, tenant_id: uuid.UUID, package_id: uuid.UUID) -> Optional[ProjectPackage]:
        r = self._get_record(tenant_id, package_id)
        if not r:
            return None
        pages = self.session.query(PackagePageRecord).filter(
            PackagePageRecord.package_id == str(package_id)
        ).all()
        return _package_from_record(r, pages)

    def get_latest_for_project(self, tenant_id: uuid.UUID, project_id: uuid.UUID) -> Optional[ProjectPackage]:
        r = (
            self.session.query(ProjectPackageRecord)
            .filter(
                ProjectPackageRecord.project_id == str(project_id),
                ProjectPackageRecord.tenant_id == str(tenant_id),
            )
            .order_by(ProjectPackageRecord.created_at.desc())
            .first()
        )
        if not r:
            return None
        pages = self.session.query(PackagePageRecord).filter(PackagePageRecord.package_id == r.id).all()
        return _package_from_record(r, pages)

    def list_for_project(self, tenant_id: uuid.UUID, project_id: uuid.UUID) -> List[ProjectPackage]:
        records = (
            self.session.query(ProjectPackageRecord)
            .filter(
                ProjectPackageRecord.project_id == str(project_id),
                ProjectPackageRecord.tenant_id == str(tenant_id),
            )
            .order_by(ProjectPackageRecord.created_at.desc()).all()
        )
        return [
            ProjectPackage(
                package_id=uuid.UUID(r.id), project_id=uuid.UUID(r.project_id),
                tenant_id=uuid.UUID(r.tenant_id), version=r.version,
                issued_by=r.issued_by, issued_date=r.issued_date,
                revision_notes=r.revision_notes,
                status=ProjectPackageStatus(r.status), storage_reference=r.storage_reference,
                generated_at=r.generated_at, 
                approved_by=r.approved_by, approved_at=r.approved_at, review_notes=r.review_notes,
                page_count=r.page_count, pages=[],
            ) for r in records
        ]

    def update_status(
        self, tenant_id: uuid.UUID, package_id: uuid.UUID,
        status: ProjectPackageStatus, generated_at: Optional[datetime] = None,
    ) -> bool:
        r = self.session.query(ProjectPackageRecord).filter(
            ProjectPackageRecord.id == str(package_id),
            ProjectPackageRecord.tenant_id == str(tenant_id),
        ).first()
        if not r:
            return False
        r.status = status.value
        if generated_at:
            r.generated_at = generated_at
        r.updated_at = _utcnow()
        self.session.commit()
        return True
