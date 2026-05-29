"""
Phase 2 Fabrication Tests
=========================
Unit tests for the Fabrication Service and Repository logic.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.models import (  # import all to register with Base metadata
    AssemblyRecord,
    BuildingRecord,
    CutoutRecord,
    EdgeTreatmentRecord,
    FabricationNoteRecord,
    FloorRecord,
    GeometryRecord,
    HoleRecord,
    PartRecord,
    ProjectRecord,
    SplashRecord,
    TenantRecord,
    UnitRecord,
    UnitTypeRecord,
    UserRecord,
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
from app.models.hierarchy import Project, UnitVariant
from app.repositories.fabrication_repository import FabricationRepository
from app.repositories.hierarchy_repository import ProjectHierarchyRepository
from app.services.fabrication_service import FabricationService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def db_session():
    """In-memory SQLite session for each test function."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def tenant_id() -> uuid.UUID:
    return uuid.UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture
def hierarchy_repo(db_session: Session) -> ProjectHierarchyRepository:
    return ProjectHierarchyRepository(db_session)


@pytest.fixture
def service(db_session: Session, hierarchy_repo: ProjectHierarchyRepository) -> FabricationService:
    fab_repo = FabricationRepository(db_session)
    return FabricationService(fab_repo, hierarchy_repo)


@pytest.fixture
def project(hierarchy_repo, tenant_id) -> Project:
    p = Project(
        project_id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="Test Project"
    )
    return hierarchy_repo.create_project(p)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAssemblyCreation:
    def test_create_simple_assembly(self, service, project, tenant_id):
        assembly_id = uuid.uuid4()
        assembly = Assembly(
            assembly_id=assembly_id,
            project_id=project.project_id,
            tenant_id=tenant_id,
            name="Kitchen",
            assembly_type=AssemblyType.KITCHEN,
            variant=UnitVariant.STANDARD,
            parts=[
                Part(
                    part_id=uuid.uuid4(),
                    assembly_id=assembly_id,
                    part_type=PartType.MAIN_TOP,
                    name="Island",
                    dimensions=Dimensions(length=120.0, depth=36.0, thickness=1.5),
                )
            ]
        )
        
        saved = service.create_assembly(assembly)
        assert saved.name == "Kitchen"
        assert len(saved.parts) == 1
        assert saved.parts[0].name == "Island"
        assert saved.parts[0].dimensions.length == 120.0

    def test_create_complex_assembly(self, service, project, tenant_id):
        assembly_id = uuid.uuid4()
        part_id = uuid.uuid4()
        
        assembly = Assembly(
            assembly_id=assembly_id,
            project_id=project.project_id,
            tenant_id=tenant_id,
            name="Master Bath",
            assembly_type=AssemblyType.VANITY,
            notes=[FabricationNote(assembly_id=assembly_id, content="Careful with veining")],
            parts=[
                Part(
                    part_id=part_id,
                    assembly_id=assembly_id,
                    part_type=PartType.MAIN_TOP,
                    name="Vanity Top",
                    dimensions=Dimensions(length=72.0, depth=22.0, thickness=1.5),
                    edges=[
                        EdgeTreatment(
                            part_id=part_id,
                            position=Position.FRONT,
                            edge_type=EdgeType.EASED
                        ),
                        EdgeTreatment(
                            part_id=part_id,
                            position=Position.LEFT,
                            edge_type=EdgeType.RAW
                        )
                    ],
                    cutouts=[
                        Cutout(
                            part_id=part_id,
                            cutout_type=CutoutType.SINK,
                            mount_type=MountType.UNDERMOUNT,
                            dimensions=Dimensions(length=17.0, depth=14.0),
                            center_x=36.0,
                            center_y=11.0,
                        )
                    ],
                    holes=[
                        Hole(
                            part_id=part_id,
                            diameter=1.375,
                            center_x=36.0,
                            center_y=3.0,
                            purpose="Faucet"
                        )
                    ],
                    splashes=[
                        Splash(
                            part_id=part_id,
                            splash_type=SplashType.BACKSPLASH,
                            dimensions=Dimensions(length=72.0, depth=4.0, thickness=1.5)
                        )
                    ]
                )
            ]
        )
        
        saved = service.create_assembly(assembly)
        
        # Verify persistence via get
        fetched = service.get_assembly(tenant_id, assembly_id)
        assert fetched is not None
        assert fetched.name == "Master Bath"
        assert len(fetched.notes) == 1
        assert fetched.notes[0].content == "Careful with veining"
        
        assert len(fetched.parts) == 1
        part = fetched.parts[0]
        assert part.name == "Vanity Top"
        
        assert len(part.edges) == 2
        assert part.edges[0].position == Position.FRONT
        
        assert len(part.cutouts) == 1
        assert part.cutouts[0].cutout_type == CutoutType.SINK
        
        assert len(part.holes) == 1
        assert part.holes[0].purpose == "Faucet"
        
        assert len(part.splashes) == 1
        assert part.splashes[0].splash_type == SplashType.BACKSPLASH

    def test_validation_rejects_negative_dimensions(self, service, project, tenant_id):
        assembly_id = uuid.uuid4()
        assembly = Assembly(
            assembly_id=assembly_id,
            project_id=project.project_id,
            tenant_id=tenant_id,
            name="Bad Kitchen",
            assembly_type=AssemblyType.KITCHEN,
            parts=[
                Part(
                    part_id=uuid.uuid4(),
                    assembly_id=assembly_id,
                    part_type=PartType.MAIN_TOP,
                    name="Top",
                    dimensions=Dimensions(length=-10.0, depth=36.0),
                )
            ]
        )
        with pytest.raises(ValueError, match="positive length and depth"):
            service.create_assembly(assembly)

    def test_update_assembly_replaces_parts(self, service, project, tenant_id):
        assembly_id = uuid.uuid4()
        assembly = Assembly(
            assembly_id=assembly_id,
            project_id=project.project_id,
            tenant_id=tenant_id,
            name="V1",
            assembly_type=AssemblyType.KITCHEN,
            parts=[
                Part(
                    part_id=uuid.uuid4(),
                    assembly_id=assembly_id,
                    part_type=PartType.MAIN_TOP,
                    name="P1",
                    dimensions=Dimensions(length=10, depth=10)
                )
            ]
        )
        service.create_assembly(assembly)
        
        # Update
        assembly.name = "V2"
        assembly.parts = [
            Part(
                part_id=uuid.uuid4(),
                assembly_id=assembly_id,
                part_type=PartType.ISLAND_TOP,
                name="P2",
                dimensions=Dimensions(length=20, depth=20)
            )
        ]
        service.update_assembly(assembly)
        
        fetched = service.get_assembly(tenant_id, assembly_id)
        assert fetched.name == "V2"
        assert len(fetched.parts) == 1
        assert fetched.parts[0].name == "P2"
        assert fetched.parts[0].dimensions.length == 20

    def test_delete_assembly(self, service, project, tenant_id):
        assembly_id = uuid.uuid4()
        assembly = Assembly(
            assembly_id=assembly_id,
            project_id=project.project_id,
            tenant_id=tenant_id,
            name="ToDelete",
            assembly_type=AssemblyType.KITCHEN,
        )
        service.create_assembly(assembly)
        assert service.get_assembly(tenant_id, assembly_id) is not None
        
        success = service.delete_assembly(tenant_id, assembly_id)
        assert success is True
        assert service.get_assembly(tenant_id, assembly_id) is None

    def test_duplicate_assembly(self, service, project, tenant_id):
        assembly_id = uuid.uuid4()
        assembly = Assembly(
            assembly_id=assembly_id,
            project_id=project.project_id,
            tenant_id=tenant_id,
            name="Original",
            assembly_type=AssemblyType.KITCHEN,
            notes=[FabricationNote(assembly_id=assembly_id, content="A note")],
            parts=[
                Part(
                    part_id=uuid.uuid4(),
                    assembly_id=assembly_id,
                    part_type=PartType.MAIN_TOP,
                    name="Top",
                    dimensions=Dimensions(length=10, depth=10)
                )
            ]
        )
        service.create_assembly(assembly)

        dup = service.duplicate_assembly(tenant_id, assembly_id, new_name="Duplicated", variant=UnitVariant.MIRROR)
        assert dup.assembly_id != assembly_id
        assert dup.name == "Duplicated"
        assert dup.variant == UnitVariant.MIRROR
        assert len(dup.parts) == 1
        assert dup.parts[0].part_id != assembly.parts[0].part_id
        assert dup.parts[0].name == "Top"
        assert len(dup.notes) == 1
        assert dup.notes[0].note_id != assembly.notes[0].note_id
