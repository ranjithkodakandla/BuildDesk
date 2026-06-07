"""
Matrix Setup API Router  (Phase 6)
====================================
POST /api/v1/projects/{project_id}/units/bulk-matrix

Accepts a list of matrix rows (Building | Floor | Flat | Template | Mirror | ADA)
and idempotently creates the full project hierarchy.

Auth:     Bearer JWT or X-Tenant-ID header + active user (same as all hierarchy endpoints)
Stateful: writes to DB (Building, Floor, UnitType, Unit records)
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.matrix_schemas import MatrixBulkRequest, MatrixBulkResponse
from app.auth.dependencies import get_current_tenant, require_active_user
from app.dependencies import get_db
from app.models.user import User
from app.repositories.hierarchy_repository import ProjectHierarchyRepository
from app.services.matrix_service import bulk_matrix_create

router = APIRouter(prefix="/projects", tags=["matrix"])


@router.post(
    "/{project_id}/units/bulk-matrix",
    response_model=MatrixBulkResponse,
    status_code=status.HTTP_200_OK,
    summary="Bulk-create units from a matrix of rows",
    description="""
Idempotent bulk unit creation from a spreadsheet-style matrix.

Each row specifies:  Building | Floor | Flat | Template | Mirror | ADA

**Idempotency**: rows that already exist (matched by building + floor + flat code)
are returned with status="existing" and are not duplicated.

**Auto-hierarchy**: the project is automatically upgraded to
`has_buildings=True, has_floors=True` if not already configured.

**Limits**: up to 500 rows per call. For larger projects call in batches.
    """,
)
def bulk_matrix(
    project_id: uuid.UUID,
    body: MatrixBulkRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    _user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> MatrixBulkResponse:
    # Verify project exists and belongs to this tenant
    repo = ProjectHierarchyRepository(db)
    project = repo.get_project(tenant_id, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found.",
        )

    return bulk_matrix_create(
        session=db,
        project_id=project_id,
        tenant_id=tenant_id,
        request=body,
    )


@router.get(
    "/{project_id}/matrix",
    summary="Export project units as matrix rows",
    description="Returns all units as matrix rows for display/export.",
)
def get_matrix(
    project_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    _user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> dict:
    repo = ProjectHierarchyRepository(db)
    project = repo.get_project(tenant_id, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    buildings  = {b.building_id: b for b in repo.list_buildings(tenant_id, project_id)}
    unit_types = {ut.unit_type_id: ut for ut in repo.list_unit_types(tenant_id, project_id)}
    units      = repo.list_units(tenant_id, project_id)

    # Build floor lookup: floor_id → floor
    from app.db.models import FloorRecord
    floor_records = db.query(FloorRecord).filter_by(
        project_id=str(project_id), tenant_id=str(tenant_id)
    ).all()
    floors = {r.id: r for r in floor_records}

    rows = []
    for u in units:
        bldg = buildings.get(u.building_id)
        floor = floors.get(str(u.floor_id)) if u.floor_id else None
        ut   = unit_types.get(u.unit_type_id)

        # Extract template_id from unit_type description (stored by matrix_service)
        template_id = (ut.description if ut and ut.description else
                       (ut.code if ut else ""))
        # Strip _MIR / _ADA suffixes if description not set
        if not template_id and ut:
            template_id = ut.code.replace("_MIR", "").replace("_ADA", "")

        mirror = ut.is_mirror if ut else False
        ada    = ut.is_ada    if ut else False

        rows.append({
            "unit_id":      str(u.unit_id),
            "building":     bldg.code if bldg and bldg.code else (str(bldg.name) if bldg else ""),
            "floor":        floor.name if floor else "",
            "flat":         u.code,
            "template":     template_id,
            "mirror":       mirror,
            "ada":          ada,
            "unit_type_id": str(u.unit_type_id) if u.unit_type_id else None,
            "building_id":  str(u.building_id)  if u.building_id  else None,
            "floor_id":     str(u.floor_id)     if u.floor_id     else None,
        })

    return {"rows": rows, "total": len(rows)}
