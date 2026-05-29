"""
Generate Sample Project Script (Validation Milestone)
======================================================
Creates a realistic multifamily countertop project with a full
hierarchy, multiple unit types, variants, and assemblies with high-fidelity
fabrication details (cutouts, holes, splashes, multiple edges).
Then generates the package PDF.
"""

import sys
import uuid
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import SessionLocal, engine
from app.db.models import Base
from app.models.fabrication import (
    Assembly, AssemblyType, Cutout, CutoutType, Dimensions, EdgeTreatment,
    EdgeType, FabricationNote, Hole, MountType, Part, PartType, Position, Splash, SplashType
)
from app.models.hierarchy import HierarchyConfig, Project, ProjectStatus, Unit, UnitType, UnitVariant
from app.repositories.fabrication_repository import FabricationRepository
from app.repositories.hierarchy_repository import ProjectHierarchyRepository
from app.repositories.package_repository import PackageRepository
from app.services.package_generator_service import PackageGeneratorService
from app.exporters.package_pdf_exporter import PackagePdfExporter

def setup_db():
    Base.metadata.create_all(bind=engine)
    return SessionLocal()

def run():
    session = setup_db()
    try:
        tenant_id = uuid.uuid4()
        proj_repo = ProjectHierarchyRepository(session)
        fab_repo = FabricationRepository(session)
        pkg_service = PackageGeneratorService(session)

        # 1. Project
        project = Project(
            project_id=uuid.uuid4(),
            tenant_id=tenant_id,
            name="The Avalon at Mueller",
            client_name="Canyon Surfaces / Avalon Construction",
            material="Silestone Lusso 3cm (Polished)",
            address="456 Mueller Blvd, Austin TX",
            status=ProjectStatus.draft,
            hierarchy_config=HierarchyConfig(has_buildings=False, has_floors=False)
        )
        proj_repo.create_project(project)

        # 2. Unit Types
        ut_a = UnitType(
            unit_type_id=uuid.uuid4(),
            project_id=project.project_id,
            tenant_id=tenant_id,
            code="A1",
            name="1 Bed / 1 Bath",
            sort_order=1
        )
        ut_a_mir = UnitType(
            unit_type_id=uuid.uuid4(),
            project_id=project.project_id,
            tenant_id=tenant_id,
            code="A1-MIR",
            name="1 Bed / 1 Bath (Mirror)",
            is_mirror=True,
            base_type_id=ut_a.unit_type_id,
            sort_order=2
        )
        ut_b = UnitType(
            unit_type_id=uuid.uuid4(),
            project_id=project.project_id,
            tenant_id=tenant_id,
            code="B1",
            name="2 Bed / 2 Bath Island",
            sort_order=3
        )
        ut_b_ada = UnitType(
            unit_type_id=uuid.uuid4(),
            project_id=project.project_id,
            tenant_id=tenant_id,
            code="B1-ADA",
            name="2 Bed / 2 Bath Island (ADA)",
            is_ada=True,
            base_type_id=ut_b.unit_type_id,
            sort_order=4
        )
        for ut in [ut_a, ut_a_mir, ut_b, ut_b_ada]:
            proj_repo.create_unit_type(ut)

        # 3. Units
        units_data = [
            (ut_a, ["101", "102", "103", "201", "202", "203"]),
            (ut_a_mir, ["104", "105", "204", "205"]),
            (ut_b, ["301", "302", "303", "304", "305"]),
            (ut_b_ada, ["106"])
        ]
        for ut, codes in units_data:
            for code in codes:
                u = Unit(
                    unit_id=uuid.uuid4(),
                    project_id=project.project_id,
                    tenant_id=tenant_id,
                    unit_type_id=ut.unit_type_id,
                    name=f"Unit {code}",
                    code=code,
                    variant=UnitVariant.STANDARD if not ut.is_mirror else UnitVariant.MIRROR
                )
                proj_repo.create_unit(u)

        # 4. Assemblies
        # Type A1 - Kitchen (L-Shape)
        a1_kitchen = Assembly(
            assembly_id=uuid.uuid4(),
            project_id=project.project_id,
            tenant_id=tenant_id,
            unit_type_id=ut_a.unit_type_id,
            name="Kitchen",
            assembly_type=AssemblyType.KITCHEN,
            parts=[
                Part(
                    part_id=uuid.uuid4(),
                    assembly_id=uuid.uuid4(), # assigned in repo
                    part_type=PartType.MAIN_TOP,
                    name="Sink Run",
                    dimensions=Dimensions(length=102.5, depth=25.5, thickness=1.25),
                    edges=[
                        EdgeTreatment(part_id=uuid.uuid4(), position=Position.FRONT, edge_type=EdgeType.EASED),
                        EdgeTreatment(part_id=uuid.uuid4(), position=Position.RIGHT, edge_type=EdgeType.EASED),
                        EdgeTreatment(part_id=uuid.uuid4(), position=Position.BACK, edge_type=EdgeType.RAW),
                        EdgeTreatment(part_id=uuid.uuid4(), position=Position.LEFT, edge_type=EdgeType.RAW),
                    ],
                    cutouts=[
                        Cutout(part_id=uuid.uuid4(), cutout_type=CutoutType.SINK, mount_type=MountType.UNDERMOUNT,
                               dimensions=Dimensions(length=30.0, depth=17.5), center_x=51.25, center_y=12.5)
                    ],
                    holes=[
                        Hole(part_id=uuid.uuid4(), diameter=1.375, center_x=51.25, center_y=4.0, purpose="Faucet"),
                        Hole(part_id=uuid.uuid4(), diameter=1.375, center_x=45.0, center_y=4.0, purpose="Air Switch")
                    ],
                    splashes=[
                        Splash(part_id=uuid.uuid4(), splash_type=SplashType.BACKSPLASH, dimensions=Dimensions(length=102.5, depth=4.0))
                    ]
                ),
                Part(
                    part_id=uuid.uuid4(),
                    assembly_id=uuid.uuid4(),
                    part_type=PartType.LEFT_RETURN,
                    name="Range Run",
                    dimensions=Dimensions(length=48.0, depth=25.5, thickness=1.25),
                    edges=[
                        EdgeTreatment(part_id=uuid.uuid4(), position=Position.FRONT, edge_type=EdgeType.EASED),
                        EdgeTreatment(part_id=uuid.uuid4(), position=Position.LEFT, edge_type=EdgeType.RAW),
                        EdgeTreatment(part_id=uuid.uuid4(), position=Position.BACK, edge_type=EdgeType.RAW),
                        EdgeTreatment(part_id=uuid.uuid4(), position=Position.RIGHT, edge_type=EdgeType.RAW),
                    ],
                    cutouts=[
                        Cutout(part_id=uuid.uuid4(), cutout_type=CutoutType.COOKTOP, mount_type=MountType.DROP_IN,
                               dimensions=Dimensions(length=28.5, depth=20.0), center_x=24.0, center_y=12.5)
                    ],
                    splashes=[
                        Splash(part_id=uuid.uuid4(), splash_type=SplashType.BACKSPLASH, dimensions=Dimensions(length=48.0, depth=4.0)),
                        Splash(part_id=uuid.uuid4(), splash_type=SplashType.LEFT_SPLASH, dimensions=Dimensions(length=24.25, depth=4.0))
                    ]
                )
            ],
            notes=[
                FabricationNote(assembly_id=uuid.uuid4(), content="Verify sink template on site prior to cutting."),
                FabricationNote(assembly_id=uuid.uuid4(), content="Seam between Sink Run and Range Run must be reinforced.")
            ]
        )
        
        a1_vanity = Assembly(
            assembly_id=uuid.uuid4(),
            project_id=project.project_id,
            tenant_id=tenant_id,
            unit_type_id=ut_a.unit_type_id,
            name="Master Vanity",
            assembly_type=AssemblyType.VANITY,
            parts=[
                Part(
                    part_id=uuid.uuid4(), assembly_id=uuid.uuid4(), part_type=PartType.MAIN_TOP, name="Vanity Top",
                    dimensions=Dimensions(length=60.0, depth=22.5, thickness=1.25),
                    edges=[
                        EdgeTreatment(part_id=uuid.uuid4(), position=Position.FRONT, edge_type=EdgeType.EASED),
                        EdgeTreatment(part_id=uuid.uuid4(), position=Position.LEFT, edge_type=EdgeType.EASED),
                        EdgeTreatment(part_id=uuid.uuid4(), position=Position.RIGHT, edge_type=EdgeType.EASED),
                        EdgeTreatment(part_id=uuid.uuid4(), position=Position.BACK, edge_type=EdgeType.RAW),
                    ],
                    cutouts=[
                        Cutout(part_id=uuid.uuid4(), cutout_type=CutoutType.SINK, mount_type=MountType.UNDERMOUNT,
                               dimensions=Dimensions(length=19.0, depth=14.0), center_x=30.0, center_y=11.25)
                    ],
                    holes=[
                        Hole(part_id=uuid.uuid4(), diameter=1.375, center_x=30.0, center_y=4.0, purpose="Faucet (Single Hole)")
                    ],
                    splashes=[
                        Splash(part_id=uuid.uuid4(), splash_type=SplashType.BACKSPLASH, dimensions=Dimensions(length=60.0, depth=4.0))
                    ]
                )
            ]
        )

        # Mirror Type A1 gets mirrored instances (just copies for the model)
        a1_mir_kitchen = a1_kitchen.model_copy(deep=True)
        a1_mir_kitchen.assembly_id = uuid.uuid4()
        a1_mir_kitchen.unit_type_id = ut_a_mir.unit_type_id
        a1_mir_vanity = a1_vanity.model_copy(deep=True)
        a1_mir_vanity.assembly_id = uuid.uuid4()
        a1_mir_vanity.unit_type_id = ut_a_mir.unit_type_id

        # Type B1 - Island
        b1_island = Assembly(
            assembly_id=uuid.uuid4(),
            project_id=project.project_id,
            tenant_id=tenant_id,
            unit_type_id=ut_b.unit_type_id,
            name="Center Island",
            assembly_type=AssemblyType.ISLAND,
            parts=[
                Part(
                    part_id=uuid.uuid4(), assembly_id=uuid.uuid4(), part_type=PartType.ISLAND_TOP, name="Island Main",
                    dimensions=Dimensions(length=108.0, depth=42.0, thickness=1.25),
                    edges=[
                        EdgeTreatment(part_id=uuid.uuid4(), position=Position.FRONT, edge_type=EdgeType.EASED),
                        EdgeTreatment(part_id=uuid.uuid4(), position=Position.BACK, edge_type=EdgeType.EASED),
                        EdgeTreatment(part_id=uuid.uuid4(), position=Position.LEFT, edge_type=EdgeType.EASED),
                        EdgeTreatment(part_id=uuid.uuid4(), position=Position.RIGHT, edge_type=EdgeType.EASED),
                    ],
                    cutouts=[
                        Cutout(part_id=uuid.uuid4(), cutout_type=CutoutType.SINK, mount_type=MountType.UNDERMOUNT,
                               dimensions=Dimensions(length=32.0, depth=18.0), center_x=54.0, center_y=12.0)
                    ],
                    holes=[
                        Hole(part_id=uuid.uuid4(), diameter=1.375, center_x=54.0, center_y=23.0, purpose="Faucet"),
                        Hole(part_id=uuid.uuid4(), diameter=1.375, center_x=60.0, center_y=23.0, purpose="Soap"),
                        Hole(part_id=uuid.uuid4(), diameter=1.375, center_x=48.0, center_y=23.0, purpose="Air Switch")
                    ]
                )
            ]
        )
        
        # ADA Type B1
        b1_ada_island = b1_island.model_copy(deep=True)
        b1_ada_island.assembly_id = uuid.uuid4()
        b1_ada_island.unit_type_id = ut_b_ada.unit_type_id
        # ADA has lower height, maybe different sink center, but for drawing it's similar

        for asm in [a1_kitchen, a1_vanity, a1_mir_kitchen, a1_mir_vanity, b1_island, b1_ada_island]:
            # Assign correct ids for nested objects
            for p in asm.parts:
                if p.assembly_id != asm.assembly_id:
                    p.part_id = uuid.uuid4()
                p.assembly_id = asm.assembly_id
                for e in p.edges:
                    if e.part_id != p.part_id: e.edge_id = uuid.uuid4()
                    e.part_id = p.part_id
                for c in p.cutouts:
                    if c.part_id != p.part_id: c.cutout_id = uuid.uuid4()
                    c.part_id = p.part_id
                for h in p.holes:
                    if h.part_id != p.part_id: h.hole_id = uuid.uuid4()
                    h.part_id = p.part_id
                for s in p.splashes:
                    if s.part_id != p.part_id: s.splash_id = uuid.uuid4()
                    s.part_id = p.part_id
            for n in asm.notes: 
                if n.assembly_id != asm.assembly_id: n.note_id = uuid.uuid4()
                n.assembly_id = asm.assembly_id
            fab_repo.save_assembly(asm)

        session.commit()
        print(f"Project '{project.name}' populated successfully.")

        # Generate Package
        package = pkg_service.generate(tenant_id, project.project_id, version="Rev A", issued_by="Canyon Surfaces / BuildDesk")
        
        groups = pkg_service.get_unit_type_groups(tenant_id, project.project_id)
        all_assemblies = fab_repo.list_assemblies(tenant_id, project.project_id)
        summary = pkg_service.get_summary(tenant_id, project.project_id)

        assemblies_by_type = {}
        for asm in all_assemblies:
            if asm.unit_type_id:
                full_asm = fab_repo.get_assembly(tenant_id, asm.assembly_id)
                key = f"{asm.unit_type_id}::{asm.assembly_type.value}"
                assemblies_by_type.setdefault(key, []).append(full_asm)

        exporter = PackagePdfExporter()
        pdf_bytes = exporter.export(
            project=project,
            unit_type_groups=groups,
            assemblies_by_type=assemblies_by_type,
            summary=summary,
            version=package.version
        )

        out_dir = os.path.join(os.path.dirname(__file__), "..", "..", "artifacts")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, "validation_package.pdf")
        with open(out_path, "wb") as f:
            f.write(pdf_bytes)
        print(f"Generated PDF at {out_path}")

    finally:
        session.close()

if __name__ == "__main__":
    run()
