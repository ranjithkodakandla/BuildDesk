"""
Fabrication API Router
======================
REST endpoints for the fabrication domain (assemblies and parts).

Routes:
    POST   /api/v1/assemblies                         → create assembly
    GET    /api/v1/assemblies?project_id=...          → list assemblies
    GET    /api/v1/assemblies/{assembly_id}           → get assembly with all parts
    PUT    /api/v1/assemblies/{assembly_id}           → full update of assembly
    DELETE /api/v1/assemblies/{assembly_id}           → delete assembly
"""

from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.fabrication_schemas import (
    AssemblyCreateRequest,
    AssemblyListResponse,
    AssemblyResponse,
    AssemblyUpdateRequest,
    CutoutSchema,
    DimensionsSchema,
    EdgeTreatmentSchema,
    FabricationNoteSchema,
    HoleSchema,
    PartSchema,
    SplashSchema,
)
from app.auth.dependencies import get_current_tenant, require_active_user
from app.dependencies import get_db
from app.models.fabrication import (
    Assembly,
    AssemblyType,
    Cutout,
    CutoutType,
    Dimensions,
    EdgeTreatment,
    EdgeType,
    FabricationNote,
    Hole,
    MountType,
    Part,
    PartType,
    Position,
    Splash,
    SplashType,
)
from app.models.hierarchy import UnitVariant
from app.models.user import User
from app.repositories.fabrication_repository import FabricationRepository
from app.repositories.hierarchy_repository import ProjectHierarchyRepository
from app.services.fabrication_service import FabricationService

router = APIRouter(prefix="/assemblies", tags=["fabrication"])


# ---------------------------------------------------------------------------
# Dependency Providers
# ---------------------------------------------------------------------------

def get_fabrication_service(db: Session = Depends(get_db)) -> FabricationService:
    fab_repo = FabricationRepository(db)
    hierarchy_repo = ProjectHierarchyRepository(db)
    return FabricationService(fab_repo, hierarchy_repo)


# ---------------------------------------------------------------------------
# Mappers: Domain ↔ Schema
# ---------------------------------------------------------------------------

def _map_dimensions_in(d: DimensionsSchema) -> Dimensions:
    return Dimensions(length=d.length, depth=d.depth, thickness=d.thickness)


def _map_dimensions_out(d: Dimensions) -> DimensionsSchema:
    return DimensionsSchema(length=d.length, depth=d.depth, thickness=d.thickness)


def _map_part_in(assembly_id: uuid.UUID, p: PartSchema) -> Part:
    part_id = p.part_id or uuid.uuid4()
    return Part(
        part_id=part_id,
        assembly_id=assembly_id,
        part_type=p.part_type,
        name=p.name,
        dimensions=_map_dimensions_in(p.dimensions),
        notes=p.notes,
        edges=[
            EdgeTreatment(
                edge_id=e.edge_id or uuid.uuid4(),
                part_id=part_id,
                position=e.position,
                edge_type=e.edge_type,
                length=e.length,
                notes=e.notes,
            ) for e in p.edges
        ],
        cutouts=[
            Cutout(
                cutout_id=c.cutout_id or uuid.uuid4(),
                part_id=part_id,
                cutout_type=c.cutout_type,
                mount_type=c.mount_type,
                dimensions=_map_dimensions_in(c.dimensions),
                center_x=c.center_x,
                center_y=c.center_y,
                notes=c.notes,
            ) for c in p.cutouts
        ],
        holes=[
            Hole(
                hole_id=h.hole_id or uuid.uuid4(),
                part_id=part_id,
                diameter=h.diameter,
                center_x=h.center_x,
                center_y=h.center_y,
                purpose=h.purpose,
            ) for h in p.holes
        ],
        splashes=[
            Splash(
                splash_id=s.splash_id or uuid.uuid4(),
                part_id=part_id,
                splash_type=s.splash_type,
                dimensions=_map_dimensions_in(s.dimensions),
                notes=s.notes,
            ) for s in p.splashes
        ]
    )


def _map_part_out(p: Part) -> PartSchema:
    return PartSchema(
        part_id=p.part_id,
        part_type=p.part_type,
        name=p.name,
        dimensions=_map_dimensions_out(p.dimensions),
        notes=p.notes,
        edges=[
            EdgeTreatmentSchema(
                edge_id=e.edge_id,
                position=e.position,
                edge_type=e.edge_type,
                length=e.length,
                notes=e.notes,
            ) for e in p.edges
        ],
        cutouts=[
            CutoutSchema(
                cutout_id=c.cutout_id,
                cutout_type=c.cutout_type,
                mount_type=c.mount_type,
                dimensions=_map_dimensions_out(c.dimensions),
                center_x=c.center_x,
                center_y=c.center_y,
                notes=c.notes,
            ) for c in p.cutouts
        ],
        holes=[
            HoleSchema(
                hole_id=h.hole_id,
                diameter=h.diameter,
                center_x=h.center_x,
                center_y=h.center_y,
                purpose=h.purpose,
            ) for h in p.holes
        ],
        splashes=[
            SplashSchema(
                splash_id=s.splash_id,
                splash_type=s.splash_type,
                dimensions=_map_dimensions_out(s.dimensions),
                notes=s.notes,
            ) for s in p.splashes
        ]
    )


def _map_assembly_out(a: Assembly) -> AssemblyResponse:
    return AssemblyResponse(
        assembly_id=a.assembly_id,
        project_id=a.project_id,
        tenant_id=a.tenant_id,
        unit_id=a.unit_id,
        unit_type_id=a.unit_type_id,
        name=a.name,
        assembly_type=a.assembly_type,
        variant=a.variant,
        parts=[_map_part_out(p) for p in a.parts],
        notes=[FabricationNoteSchema(note_id=n.note_id, content=n.content) for n in a.notes],
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("", response_model=AssemblyResponse, status_code=status.HTTP_201_CREATED)
def create_assembly(
    body: AssemblyCreateRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    _user: User = Depends(require_active_user),
    svc: FabricationService = Depends(get_fabrication_service),
):
    assembly_id = uuid.uuid4()
    
    assembly = Assembly(
        assembly_id=assembly_id,
        project_id=body.project_id,
        tenant_id=tenant_id,
        unit_id=body.unit_id,
        unit_type_id=body.unit_type_id,
        name=body.name,
        assembly_type=body.assembly_type,
        variant=body.variant,
        parts=[_map_part_in(assembly_id, p) for p in body.parts],
        notes=[
            FabricationNote(
                note_id=n.note_id or uuid.uuid4(),
                assembly_id=assembly_id,
                content=n.content
            ) for n in body.notes
        ]
    )
    
    try:
        saved = svc.create_assembly(assembly)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    return _map_assembly_out(saved)


@router.get("", response_model=AssemblyListResponse)
def list_assemblies(
    project_id: uuid.UUID = Query(..., description="Filter assemblies by project ID"),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    _user: User = Depends(require_active_user),
    svc: FabricationService = Depends(get_fabrication_service),
):
    assemblies = svc.list_assemblies(tenant_id, project_id)
    return AssemblyListResponse(
        assemblies=[_map_assembly_out(a) for a in assemblies],
        total=len(assemblies),
    )


@router.get("/{assembly_id}", response_model=AssemblyResponse)
def get_assembly(
    assembly_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    _user: User = Depends(require_active_user),
    svc: FabricationService = Depends(get_fabrication_service),
):
    assembly = svc.get_assembly(tenant_id, assembly_id)
    if not assembly:
        raise HTTPException(status_code=404, detail="Assembly not found.")
    return _map_assembly_out(assembly)

from app.api.fabrication_schemas import AssemblyDuplicateRequest

@router.post("/{assembly_id}/duplicate", response_model=AssemblyResponse, status_code=201)
def duplicate_assembly(
    assembly_id: uuid.UUID,
    body: AssemblyDuplicateRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    _user: User = Depends(require_active_user),
    svc: FabricationService = Depends(get_fabrication_service),
):
    try:
        new_assembly = svc.duplicate_assembly(
            tenant_id=tenant_id,
            assembly_id=assembly_id,
            new_name=body.new_name,
            new_unit_type_id=body.new_unit_type_id,
            variant=UnitVariant(body.variant.value) if body.variant else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _map_assembly_out(new_assembly)


@router.put("/{assembly_id}", response_model=AssemblyResponse)
def update_assembly(
    assembly_id: uuid.UUID,
    body: AssemblyUpdateRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    _user: User = Depends(require_active_user),
    svc: FabricationService = Depends(get_fabrication_service),
):
    # Retrieve existing to ensure it belongs to the tenant and get the project_id
    existing = svc.get_assembly(tenant_id, assembly_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Assembly not found.")
        
    assembly = Assembly(
        assembly_id=assembly_id,
        project_id=existing.project_id,  # Project cannot be changed via PUT
        tenant_id=tenant_id,
        unit_id=body.unit_id,
        unit_type_id=body.unit_type_id,
        name=body.name,
        assembly_type=body.assembly_type,
        variant=body.variant,
        parts=[_map_part_in(assembly_id, p) for p in body.parts],
        notes=[
            FabricationNote(
                note_id=n.note_id or uuid.uuid4(),
                assembly_id=assembly_id,
                content=n.content
            ) for n in body.notes
        ]
    )
    
    try:
        updated = svc.update_assembly(assembly)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    return _map_assembly_out(updated)


@router.delete("/{assembly_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assembly(
    assembly_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    _user: User = Depends(require_active_user),
    svc: FabricationService = Depends(get_fabrication_service),
):
    success = svc.delete_assembly(tenant_id, assembly_id)
    if not success:
        raise HTTPException(status_code=404, detail="Assembly not found.")
