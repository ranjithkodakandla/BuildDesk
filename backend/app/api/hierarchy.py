"""
Project Hierarchy API Router
=============================
REST endpoints for the flexible project hierarchy.

Routes:
    POST   /api/v1/projects                         → create project
    GET    /api/v1/projects                         → list projects for tenant
    GET    /api/v1/projects/{project_id}            → get project
    GET    /api/v1/projects/{project_id}/tree       → full hierarchy tree

    POST   /api/v1/projects/{project_id}/buildings  → add building
    GET    /api/v1/projects/{project_id}/buildings  → list buildings

    POST   /api/v1/projects/{project_id}/floors     → add floor (building_id in body)
    GET    /api/v1/projects/{project_id}/floors/{building_id} → list floors

    POST   /api/v1/projects/{project_id}/unit-types → add unit type
    GET    /api/v1/projects/{project_id}/unit-types → list unit types

    POST   /api/v1/projects/{project_id}/units      → add unit
    GET    /api/v1/projects/{project_id}/units      → list units

All endpoints require JWT auth (require_active_user) and are
automatically tenant-scoped via get_current_tenant.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.hierarchy_schemas import (
    BuildingCreateRequest,
    BuildingResponse,
    FloorCreateRequest,
    FloorResponse,
    HierarchyConfigSchema,
    ProjectCreateRequest,
    ProjectListResponse,
    ProjectResponse,
    ProjectTreeResponse,
    UnitCreateRequest,
    UnitListResponse,
    UnitResponse,
    UnitTypeCreateRequest,
    UnitTypeListResponse,
    UnitTypeResponse,
    UnitTypeWithUnitsResponse,
    BuildingWithFloorsResponse,
    FloorWithUnitsResponse,
)
from app.auth.dependencies import get_current_tenant, require_active_user
from app.dependencies import get_db
from app.models.hierarchy import UnitVariant
from app.models.user import User
from app.repositories.hierarchy_repository import ProjectHierarchyRepository
from app.services.hierarchy_service import HierarchyService, ProjectTree

router = APIRouter(prefix="/projects", tags=["hierarchy"])


# ---------------------------------------------------------------------------
# Dependency: HierarchyService per request
# ---------------------------------------------------------------------------

def get_hierarchy_service(db: Session = Depends(get_db)) -> HierarchyService:
    return HierarchyService(ProjectHierarchyRepository(db))


# ---------------------------------------------------------------------------
# Mappers: Domain → Response schemas
# ---------------------------------------------------------------------------

def _project_response(p) -> ProjectResponse:
    cfg = p.hierarchy_config
    return ProjectResponse(
        project_id=p.project_id,
        tenant_id=p.tenant_id,
        name=p.name,
        client_name=p.client_name,
        material=p.material,
        issue_date=p.issue_date,
        description=p.description,
        address=p.address,
        status=p.status.value if hasattr(p.status, "value") else str(p.status),
        hierarchy_config=HierarchyConfigSchema(
            has_buildings=cfg.has_buildings,
            has_floors=cfg.has_floors,
            has_unit_types=cfg.has_unit_types,
        ),
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


def _building_response(b) -> BuildingResponse:
    return BuildingResponse(
        building_id=b.building_id,
        project_id=b.project_id,
        name=b.name,
        code=b.code,
        sort_order=b.sort_order,
        created_at=b.created_at,
    )


def _floor_response(f) -> FloorResponse:
    return FloorResponse(
        floor_id=f.floor_id,
        project_id=f.project_id,
        building_id=f.building_id,
        name=f.name,
        number=f.number,
        sort_order=f.sort_order,
        created_at=f.created_at,
    )


def _unit_type_response(ut) -> UnitTypeResponse:
    return UnitTypeResponse(
        unit_type_id=ut.unit_type_id,
        project_id=ut.project_id,
        code=ut.code,
        name=ut.name,
        description=ut.description,
        is_mirror=ut.is_mirror,
        is_ada=ut.is_ada,
        base_type_id=ut.base_type_id,
        sort_order=ut.sort_order,
        created_at=ut.created_at,
    )


def _unit_response(u) -> UnitResponse:
    return UnitResponse(
        unit_id=u.unit_id,
        project_id=u.project_id,
        name=u.name,
        code=u.code,
        building_id=u.building_id,
        floor_id=u.floor_id,
        unit_type_id=u.unit_type_id,
        variant=u.variant.value if hasattr(u.variant, "value") else str(u.variant),
        notes=u.notes,
        sort_order=u.sort_order,
        created_at=u.created_at,
    )


def _tree_response(tree: ProjectTree) -> ProjectTreeResponse:
    buildings_out = []
    for bwf in tree.buildings:
        floors_out = [
            FloorWithUnitsResponse(
                floor=_floor_response(fw.floor),
                units=[_unit_response(u) for u in fw.units],
            )
            for fw in bwf.floors
        ]
        buildings_out.append(BuildingWithFloorsResponse(
            building=_building_response(bwf.building),
            floors=floors_out,
            units=[_unit_response(u) for u in bwf.units],
        ))

    type_groups_out = [
        UnitTypeWithUnitsResponse(
            unit_type=_unit_type_response(tg.unit_type),
            units=[_unit_response(u) for u in tg.units],
            quantity=tg.quantity,
        )
        for tg in tree.unit_types
    ]

    return ProjectTreeResponse(
        project=_project_response(tree.project),
        buildings=buildings_out,
        unit_types=type_groups_out,
        units=[_unit_response(u) for u in tree.units],
        total_units=tree.total_units,
    )


# ---------------------------------------------------------------------------
# Project endpoints
# ---------------------------------------------------------------------------

@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    body: ProjectCreateRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    _user: User = Depends(require_active_user),
    svc: HierarchyService = Depends(get_hierarchy_service),
):
    """Create a new fabrication project with optional hierarchy configuration."""
    try:
        project = svc.create_project(
            tenant_id=tenant_id,
            name=body.name,
            client_name=body.client_name,
            material=body.material,
            description=body.description,
            address=body.address,
            has_buildings=body.hierarchy_config.has_buildings,
            has_floors=body.hierarchy_config.has_floors,
            has_unit_types=body.hierarchy_config.has_unit_types,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _project_response(project)


@router.get("", response_model=ProjectListResponse)
def list_projects(
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    _user: User = Depends(require_active_user),
    svc: HierarchyService = Depends(get_hierarchy_service),
):
    """List all projects for the authenticated tenant."""
    projects = svc.list_projects(tenant_id)
    return ProjectListResponse(
        projects=[_project_response(p) for p in projects],
        total=len(projects),
    )


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    _user: User = Depends(require_active_user),
    svc: HierarchyService = Depends(get_hierarchy_service),
):
    project = svc.get_project(tenant_id, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    return _project_response(project)


@router.get("/{project_id}/tree", response_model=ProjectTreeResponse)
def get_project_tree(
    project_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    _user: User = Depends(require_active_user),
    svc: HierarchyService = Depends(get_hierarchy_service),
):
    """Return the full project hierarchy tree (used by package generator)."""
    tree = svc.build_project_tree(tenant_id, project_id)
    if not tree:
        raise HTTPException(status_code=404, detail="Project not found.")
    return _tree_response(tree)


# ---------------------------------------------------------------------------
# Building endpoints
# ---------------------------------------------------------------------------

@router.post("/{project_id}/buildings", response_model=BuildingResponse, status_code=201)
def add_building(
    project_id: uuid.UUID,
    body: BuildingCreateRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    _user: User = Depends(require_active_user),
    svc: HierarchyService = Depends(get_hierarchy_service),
):
    try:
        building = svc.add_building(
            tenant_id, project_id, body.name, code=body.code, sort_order=body.sort_order
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _building_response(building)


@router.get("/{project_id}/buildings", response_model=list[BuildingResponse])
def list_buildings(
    project_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    _user: User = Depends(require_active_user),
    svc: HierarchyService = Depends(get_hierarchy_service),
):
    return [_building_response(b) for b in svc.list_buildings(tenant_id, project_id)]


# ---------------------------------------------------------------------------
# Floor endpoints
# ---------------------------------------------------------------------------

@router.post("/{project_id}/floors", response_model=FloorResponse, status_code=201)
def add_floor(
    project_id: uuid.UUID,
    body: FloorCreateRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    _user: User = Depends(require_active_user),
    svc: HierarchyService = Depends(get_hierarchy_service),
):
    try:
        floor = svc.add_floor(
            tenant_id, project_id, body.building_id,
            body.name, number=body.number, sort_order=body.sort_order
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _floor_response(floor)


@router.get("/{project_id}/floors/{building_id}", response_model=list[FloorResponse])
def list_floors(
    project_id: uuid.UUID,
    building_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    _user: User = Depends(require_active_user),
    svc: HierarchyService = Depends(get_hierarchy_service),
):
    return [_floor_response(f) for f in svc.list_floors(tenant_id, building_id)]


# ---------------------------------------------------------------------------
# UnitType endpoints
# ---------------------------------------------------------------------------

@router.post("/{project_id}/unit-types", response_model=UnitTypeResponse, status_code=201)
def add_unit_type(
    project_id: uuid.UUID,
    body: UnitTypeCreateRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    _user: User = Depends(require_active_user),
    svc: HierarchyService = Depends(get_hierarchy_service),
):
    try:
        ut = svc.add_unit_type(
            tenant_id, project_id,
            code=body.code,
            name=body.name,
            description=body.description,
            is_mirror=body.is_mirror,
            is_ada=body.is_ada,
            base_type_id=body.base_type_id,
            sort_order=body.sort_order,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _unit_type_response(ut)


@router.get("/{project_id}/unit-types", response_model=UnitTypeListResponse)
def list_unit_types(
    project_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    _user: User = Depends(require_active_user),
    svc: HierarchyService = Depends(get_hierarchy_service),
):
    types = svc.list_unit_types(tenant_id, project_id)
    return UnitTypeListResponse(
        unit_types=[_unit_type_response(t) for t in types],
        total=len(types),
    )


# ---------------------------------------------------------------------------
# Unit endpoints
# ---------------------------------------------------------------------------

@router.post("/{project_id}/units", response_model=UnitResponse, status_code=201)
def add_unit(
    project_id: uuid.UUID,
    body: UnitCreateRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    _user: User = Depends(require_active_user),
    svc: HierarchyService = Depends(get_hierarchy_service),
):
    try:
        unit = svc.add_unit(
            tenant_id=tenant_id,
            project_id=project_id,
            name=body.name,
            code=body.code,
            building_id=body.building_id,
            floor_id=body.floor_id,
            unit_type_id=body.unit_type_id,
            variant=UnitVariant(body.variant.value),
            notes=body.notes,
            sort_order=body.sort_order,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _unit_response(unit)

from app.api.hierarchy_schemas import UnitBulkCreateRequest, UnitBulkCreateResponse

@router.post("/{project_id}/units/bulk", response_model=UnitBulkCreateResponse, status_code=201)
def bulk_add_units(
    project_id: uuid.UUID,
    body: UnitBulkCreateRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    _user: User = Depends(require_active_user),
    svc: HierarchyService = Depends(get_hierarchy_service),
):
    try:
        units = svc.bulk_add_units(
            tenant_id=tenant_id,
            project_id=project_id,
            start_number=body.start_number,
            end_number=body.end_number,
            prefix=body.prefix or "",
            suffix=body.suffix or "",
            increment=body.increment,
            building_id=body.building_id,
            floor_id=body.floor_id,
            unit_type_id=body.unit_type_id,
            variant=UnitVariant(body.variant.value),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return UnitBulkCreateResponse(
        created_count=len(units),
        units=[_unit_response(u) for u in units]
    )


from app.api.hierarchy_schemas import UnitBulkUpdateRequest, UnitBulkUpdateResponse

@router.put("/{project_id}/units/bulk", response_model=UnitBulkUpdateResponse, status_code=200)
def bulk_update_units(
    project_id: uuid.UUID,
    body: UnitBulkUpdateRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    _user: User = Depends(require_active_user),
    svc: HierarchyService = Depends(get_hierarchy_service),
):
    try:
        updated = svc.bulk_update_units(
            tenant_id=tenant_id,
            project_id=project_id,
            unit_ids=body.unit_ids,
            building_id=body.building_id,
            floor_id=body.floor_id,
            unit_type_id=body.unit_type_id,
            variant=UnitVariant(body.variant.value) if body.variant else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return UnitBulkUpdateResponse(updated_count=updated)


@router.get("/{project_id}/units", response_model=UnitListResponse)
def list_units(
    project_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    _user: User = Depends(require_active_user),
    svc: HierarchyService = Depends(get_hierarchy_service),
):
    units = svc.list_units(tenant_id, project_id)
    return UnitListResponse(
        units=[_unit_response(u) for u in units],
        total=len(units),
    )
