"""
Fabrication persistence with foreign keys enforced (mirrors PostgreSQL / Cloud SQL).

SQLite tests in test_fabrication.py do not enable PRAGMA foreign_keys=ON, so insert-order
bugs can pass locally while production returns HTTP 500.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db import models  # noqa: F401 — register metadata
from app.db.models import utcnow
from app.models.fabrication import (
    Assembly,
    AssemblyType,
    Cutout,
    CutoutType,
    Dimensions,
    EdgeTreatment,
    EdgeType,
    MountType,
    Part,
    PartType,
    Position,
)
from app.models.hierarchy import Project, UnitVariant
from app.repositories.fabrication_repository import FabricationRepository
from app.repositories.hierarchy_repository import ProjectHierarchyRepository
from app.services.fabrication_service import FabricationService


@pytest.fixture(scope="function")
def fk_session():
    engine = create_engine("sqlite:///:memory:", echo=False)

    @event.listens_for(engine, "connect")
    def _enable_sqlite_fk(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def fk_service(fk_session: Session) -> FabricationService:
    hierarchy_repo = ProjectHierarchyRepository(fk_session)
    fab_repo = FabricationRepository(fk_session)
    return FabricationService(fab_repo, hierarchy_repo)


@pytest.fixture
def fk_project(fk_session: Session) -> Project:
    tenant_id = uuid.uuid4()
    fk_session.add(
        models.TenantRecord(
            id=str(tenant_id),
            name="FK Test Tenant",
            created_at=utcnow(),
        )
    )
    fk_session.flush()
    project = Project(
        project_id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="FK Test Project",
    )
    return ProjectHierarchyRepository(fk_session).create_project(project)


def test_edge_and_cutout_persist_with_foreign_keys_enforced(fk_service, fk_project):
    """Production-style payload: edges + sink cutout must round-trip."""
    tenant_id = fk_project.tenant_id
    assembly_id = uuid.uuid4()
    part_id = uuid.uuid4()

    assembly = Assembly(
        assembly_id=assembly_id,
        project_id=fk_project.project_id,
        tenant_id=tenant_id,
        name="Bull Outdoor Piece 1",
        assembly_type=AssemblyType.CUSTOM,
        variant=UnitVariant.STANDARD,
        parts=[
            Part(
                part_id=part_id,
                assembly_id=assembly_id,
                part_type=PartType.MAIN_TOP,
                name="28.5x30 Top + sink",
                dimensions=Dimensions(length=28.5, depth=30.0, thickness=3.0),
                edges=[
                    EdgeTreatment(
                        part_id=part_id,
                        position=Position.LEFT,
                        edge_type=EdgeType.POLISHED,
                        notes="3mm round",
                    ),
                    EdgeTreatment(
                        part_id=part_id,
                        position=Position.FRONT,
                        edge_type=EdgeType.POLISHED,
                    ),
                ],
                cutouts=[
                    Cutout(
                        part_id=part_id,
                        cutout_type=CutoutType.SINK,
                        mount_type=MountType.DROP_IN,
                        dimensions=Dimensions(length=17.5, depth=17.5),
                        center_x=14.25,
                        center_y=15.0,
                        notes="Top mount sink",
                    )
                ],
            )
        ],
    )

    saved = fk_service.create_assembly(assembly)
    assert len(saved.parts) == 1
    assert len(saved.parts[0].edges) == 2
    assert len(saved.parts[0].cutouts) == 1

    fetched = fk_service.get_assembly(tenant_id, assembly_id)
    assert fetched is not None
    assert fetched.parts[0].cutouts[0].cutout_type == CutoutType.SINK
    assert fetched.parts[0].edges[0].edge_type == EdgeType.POLISHED
