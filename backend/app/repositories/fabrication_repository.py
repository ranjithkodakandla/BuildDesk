"""
Fabrication Repository
======================
SQLAlchemy-backed repository for the Phase 2 fabrication domain:
    Assembly, Part, Splash, Cutout, Hole, EdgeTreatment, FabricationNote

Handles full lifecycle of assemblies and their nested piece hierarchy.
All methods enforce tenant_id scoping.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models import (
    AssemblyRecord,
    CutoutRecord,
    EdgeTreatmentRecord,
    FabricationNoteRecord,
    HoleRecord,
    PartRecord,
    SplashRecord,
)
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


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Mappers: ORM Record ↔ Domain Model
# ---------------------------------------------------------------------------

def _edge_from_record(r: EdgeTreatmentRecord) -> EdgeTreatment:
    return EdgeTreatment(
        edge_id=uuid.UUID(r.id),
        part_id=uuid.UUID(r.part_id),
        position=Position(r.position),
        edge_type=EdgeType(r.edge_type),
        length=r.length,
        notes=r.notes,
    )


def _cutout_from_record(r: CutoutRecord) -> Cutout:
    return Cutout(
        cutout_id=uuid.UUID(r.id),
        part_id=uuid.UUID(r.part_id),
        cutout_type=CutoutType(r.cutout_type),
        mount_type=MountType(r.mount_type),
        dimensions=Dimensions(length=r.dim_length, depth=r.dim_depth, thickness=r.dim_thickness),
        center_x=r.center_x,
        center_y=r.center_y,
        notes=r.notes,
    )


def _hole_from_record(r: HoleRecord) -> Hole:
    return Hole(
        hole_id=uuid.UUID(r.id),
        part_id=uuid.UUID(r.part_id),
        diameter=r.diameter,
        center_x=r.center_x,
        center_y=r.center_y,
        purpose=r.purpose,
    )


def _splash_from_record(r: SplashRecord) -> Splash:
    return Splash(
        splash_id=uuid.UUID(r.id),
        part_id=uuid.UUID(r.part_id),
        splash_type=SplashType(r.splash_type),
        dimensions=Dimensions(length=r.dim_length, depth=r.dim_depth, thickness=r.dim_thickness),
        notes=r.notes,
    )


def _part_from_record(
    r: PartRecord,
    edges: List[EdgeTreatmentRecord],
    cutouts: List[CutoutRecord],
    holes: List[HoleRecord],
    splashes: List[SplashRecord],
) -> Part:
    return Part(
        part_id=uuid.UUID(r.id),
        assembly_id=uuid.UUID(r.assembly_id),
        part_type=PartType(r.part_type),
        name=r.name,
        dimensions=Dimensions(length=r.dim_length, depth=r.dim_depth, thickness=r.dim_thickness),
        notes=r.notes,
        edges=[_edge_from_record(e) for e in edges if e.part_id == r.id],
        cutouts=[_cutout_from_record(c) for c in cutouts if c.part_id == r.id],
        holes=[_hole_from_record(h) for h in holes if h.part_id == r.id],
        splashes=[_splash_from_record(s) for s in splashes if s.part_id == r.id],
    )


def _note_from_record(r: FabricationNoteRecord) -> FabricationNote:
    return FabricationNote(
        note_id=uuid.UUID(r.id),
        assembly_id=uuid.UUID(r.assembly_id),
        content=r.content,
    )


# ---------------------------------------------------------------------------
# FabricationRepository
# ---------------------------------------------------------------------------

class FabricationRepository:
    """
    Repository for the Fabrication Domain.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    def save_assembly(self, assembly: Assembly) -> Assembly:
        """Creates or completely replaces an assembly and all its nested pieces."""
        # 1. UPSERT AssemblyRecord
        ar = self.session.query(AssemblyRecord).filter(
            AssemblyRecord.id == str(assembly.assembly_id),
            AssemblyRecord.tenant_id == str(assembly.tenant_id)
        ).first()

        if not ar:
            ar = AssemblyRecord(
                id=str(assembly.assembly_id),
                project_id=str(assembly.project_id),
                tenant_id=str(assembly.tenant_id),
                created_at=_utcnow(),
            )
            self.session.add(ar)

        ar.unit_id = str(assembly.unit_id) if assembly.unit_id else None
        ar.unit_type_id = str(assembly.unit_type_id) if assembly.unit_type_id else None
        ar.name = assembly.name
        ar.assembly_type = assembly.assembly_type.value
        ar.variant = assembly.variant.value
        ar.updated_at = _utcnow()

        # 2. DELETE existing nested records to perform full replace
        # (Safer and simpler than complex diffing for piece-level updates)
        assembly_str_id = str(assembly.assembly_id)
        part_records = self.session.query(PartRecord).filter(PartRecord.assembly_id == assembly_str_id).all()
        part_ids = [p.id for p in part_records]

        if part_ids:
            self.session.query(EdgeTreatmentRecord).filter(EdgeTreatmentRecord.part_id.in_(part_ids)).delete(synchronize_session=False)
            self.session.query(CutoutRecord).filter(CutoutRecord.part_id.in_(part_ids)).delete(synchronize_session=False)
            self.session.query(HoleRecord).filter(HoleRecord.part_id.in_(part_ids)).delete(synchronize_session=False)
            self.session.query(SplashRecord).filter(SplashRecord.part_id.in_(part_ids)).delete(synchronize_session=False)
            self.session.query(PartRecord).filter(PartRecord.assembly_id == assembly_str_id).delete(synchronize_session=False)

        self.session.query(FabricationNoteRecord).filter(FabricationNoteRecord.assembly_id == assembly_str_id).delete(synchronize_session=False)

        # 3. INSERT Notes
        for note in assembly.notes:
            nr = FabricationNoteRecord(
                id=str(note.note_id),
                assembly_id=assembly_str_id,
                content=note.content,
                created_at=_utcnow(),
            )
            self.session.add(nr)

        # 4. INSERT Parts and nested pieces
        for part in assembly.parts:
            pr = PartRecord(
                id=str(part.part_id),
                assembly_id=assembly_str_id,
                part_type=part.part_type.value,
                name=part.name,
                dim_length=part.dimensions.length,
                dim_depth=part.dimensions.depth,
                dim_thickness=part.dimensions.thickness,
                notes=part.notes,
                created_at=_utcnow(),
            )
            self.session.add(pr)

            for edge in part.edges:
                er = EdgeTreatmentRecord(
                    id=str(edge.edge_id),
                    part_id=str(part.part_id),
                    position=edge.position.value,
                    edge_type=edge.edge_type.value,
                    length=edge.length,
                    notes=edge.notes,
                    created_at=_utcnow(),
                )
                self.session.add(er)

            for cutout in part.cutouts:
                cr = CutoutRecord(
                    id=str(cutout.cutout_id),
                    part_id=str(part.part_id),
                    cutout_type=cutout.cutout_type.value,
                    mount_type=cutout.mount_type.value,
                    center_x=cutout.center_x,
                    center_y=cutout.center_y,
                    dim_length=cutout.dimensions.length,
                    dim_depth=cutout.dimensions.depth,
                    dim_thickness=cutout.dimensions.thickness,
                    notes=cutout.notes,
                    created_at=_utcnow(),
                )
                self.session.add(cr)

            for hole in part.holes:
                hr = HoleRecord(
                    id=str(hole.hole_id),
                    part_id=str(part.part_id),
                    diameter=hole.diameter,
                    center_x=hole.center_x,
                    center_y=hole.center_y,
                    purpose=hole.purpose,
                    created_at=_utcnow(),
                )
                self.session.add(hr)

            for splash in part.splashes:
                sr = SplashRecord(
                    id=str(splash.splash_id),
                    part_id=str(part.part_id),
                    splash_type=splash.splash_type.value,
                    dim_length=splash.dimensions.length,
                    dim_depth=splash.dimensions.depth,
                    dim_thickness=splash.dimensions.thickness,
                    notes=splash.notes,
                    created_at=_utcnow(),
                )
                self.session.add(sr)

        self.session.commit()
        return self.get_assembly(assembly.tenant_id, assembly.assembly_id)

    def get_assembly(self, tenant_id: uuid.UUID, assembly_id: uuid.UUID) -> Optional[Assembly]:
        """Fetch a complete assembly with all nested parts and pieces."""
        ar = self.session.query(AssemblyRecord).filter(
            AssemblyRecord.id == str(assembly_id),
            AssemblyRecord.tenant_id == str(tenant_id)
        ).first()

        if not ar:
            return None

        assembly_str_id = str(assembly_id)

        # Fetch all related records
        notes = self.session.query(FabricationNoteRecord).filter(FabricationNoteRecord.assembly_id == assembly_str_id).all()
        parts = self.session.query(PartRecord).filter(PartRecord.assembly_id == assembly_str_id).all()
        
        part_ids = [p.id for p in parts]
        if part_ids:
            edges = self.session.query(EdgeTreatmentRecord).filter(EdgeTreatmentRecord.part_id.in_(part_ids)).all()
            cutouts = self.session.query(CutoutRecord).filter(CutoutRecord.part_id.in_(part_ids)).all()
            holes = self.session.query(HoleRecord).filter(HoleRecord.part_id.in_(part_ids)).all()
            splashes = self.session.query(SplashRecord).filter(SplashRecord.part_id.in_(part_ids)).all()
        else:
            edges, cutouts, holes, splashes = [], [], [], []

        return Assembly(
            assembly_id=uuid.UUID(ar.id),
            project_id=uuid.UUID(ar.project_id),
            tenant_id=uuid.UUID(ar.tenant_id),
            unit_id=uuid.UUID(ar.unit_id) if ar.unit_id else None,
            unit_type_id=uuid.UUID(ar.unit_type_id) if ar.unit_type_id else None,
            name=ar.name,
            assembly_type=AssemblyType(ar.assembly_type),
            variant=UnitVariant(ar.variant),
            notes=[_note_from_record(n) for n in notes],
            parts=[_part_from_record(p, edges, cutouts, holes, splashes) for p in parts],
        )

    def list_assemblies(self, tenant_id: uuid.UUID, project_id: uuid.UUID) -> List[Assembly]:
        """List all assemblies for a project (lazy loaded - parts not included to save memory)."""
        records = self.session.query(AssemblyRecord).filter(
            AssemblyRecord.project_id == str(project_id),
            AssemblyRecord.tenant_id == str(tenant_id)
        ).all()

        assemblies = []
        for ar in records:
            assemblies.append(Assembly(
                assembly_id=uuid.UUID(ar.id),
                project_id=uuid.UUID(ar.project_id),
                tenant_id=uuid.UUID(ar.tenant_id),
                unit_id=uuid.UUID(ar.unit_id) if ar.unit_id else None,
                unit_type_id=uuid.UUID(ar.unit_type_id) if ar.unit_type_id else None,
                name=ar.name,
                assembly_type=AssemblyType(ar.assembly_type),
                variant=UnitVariant(ar.variant),
                parts=[],  # Intentionally empty for list endpoint
                notes=[],  # Intentionally empty for list endpoint
            ))
        return assemblies

    def delete_assembly(self, tenant_id: uuid.UUID, assembly_id: uuid.UUID) -> bool:
        """Deletes an assembly and all its parts via application cascade."""
        assembly_str_id = str(assembly_id)
        ar = self.session.query(AssemblyRecord).filter(
            AssemblyRecord.id == assembly_str_id,
            AssemblyRecord.tenant_id == str(tenant_id)
        ).first()
        
        if not ar:
            return False

        part_records = self.session.query(PartRecord).filter(PartRecord.assembly_id == assembly_str_id).all()
        part_ids = [p.id for p in part_records]

        if part_ids:
            self.session.query(EdgeTreatmentRecord).filter(EdgeTreatmentRecord.part_id.in_(part_ids)).delete(synchronize_session=False)
            self.session.query(CutoutRecord).filter(CutoutRecord.part_id.in_(part_ids)).delete(synchronize_session=False)
            self.session.query(HoleRecord).filter(HoleRecord.part_id.in_(part_ids)).delete(synchronize_session=False)
            self.session.query(SplashRecord).filter(SplashRecord.part_id.in_(part_ids)).delete(synchronize_session=False)
            self.session.query(PartRecord).filter(PartRecord.assembly_id == assembly_str_id).delete(synchronize_session=False)

        self.session.query(FabricationNoteRecord).filter(FabricationNoteRecord.assembly_id == assembly_str_id).delete(synchronize_session=False)
        self.session.delete(ar)
        self.session.commit()
        return True
