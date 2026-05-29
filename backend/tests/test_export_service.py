import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.models import *
from app.models.exports import ExportType, ExportFormat, ExportStatus
from app.repositories.hierarchy_repository import ProjectHierarchyRepository
from app.repositories.fabrication_repository import FabricationRepository
from app.repositories.export_repository import ExportRepository
from app.services.hierarchy_service import HierarchyService
from app.services.fabrication_service import FabricationService
from app.services.export_service import ExportService
from app.services.cloud_storage import CloudStorageService
from app.models.fabrication import Assembly, AssemblyType, Part, PartType, Dimensions


@pytest.fixture(scope="function")
def db_session():
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
    return uuid.UUID("22222222-2222-2222-2222-222222222222")

@pytest.fixture
def export_repo(db_session: Session) -> ExportRepository:
    return ExportRepository(db_session)

@pytest.fixture
def hierarchy_repo(db_session: Session) -> ProjectHierarchyRepository:
    return ProjectHierarchyRepository(db_session)

@pytest.fixture
def fab_repo(db_session: Session) -> FabricationRepository:
    return FabricationRepository(db_session)

@pytest.fixture
def hierarchy_svc(hierarchy_repo) -> HierarchyService:
    return HierarchyService(hierarchy_repo)

@pytest.fixture
def fab_svc(fab_repo, hierarchy_repo) -> FabricationService:
    return FabricationService(fab_repo, hierarchy_repo)

@pytest.fixture
def svc(export_repo, hierarchy_svc, fab_svc) -> ExportService:
    return ExportService(export_repo, hierarchy_svc, fab_svc)


def test_export_workflow(svc: ExportService, hierarchy_svc: HierarchyService, fab_svc: FabricationService, tenant_id: uuid.UUID):
    project = hierarchy_svc.create_project(tenant_id, "Export Project")
    ut = hierarchy_svc.add_unit_type(tenant_id, project.project_id, code="E1", name="Type E1")
    unit = hierarchy_svc.add_unit(tenant_id, project.project_id, name="Unit 101", code="101", unit_type_id=ut.unit_type_id)
    
    asm_id = uuid.uuid4()
    asm = Assembly(
        assembly_id=asm_id,
        project_id=project.project_id,
        tenant_id=tenant_id,
        unit_type_id=ut.unit_type_id,
        name="Kitchen",
        assembly_type=AssemblyType.KITCHEN,
        parts=[
            Part(part_id=uuid.uuid4(), assembly_id=asm_id, name="Main Top", part_type=PartType.MAIN_TOP, dimensions=Dimensions(length=100.0, depth=25.5))
        ]
    )
    fab_svc.create_assembly(asm)
    
    # Test CSV Schedule
    job = svc.request_export(tenant_id, project.project_id, ExportType.SCHEDULE, ExportFormat.CSV)
    assert job.status == ExportStatus.PENDING
    job = svc.execute_export(tenant_id, job.job_id)
    assert job.status == ExportStatus.COMPLETED
    assert job.file_path is not None
    assert ".csv" in job.file_path

    storage = CloudStorageService()
    content = storage.download_bytes(job.file_path).decode()
    assert "101" in content
    assert "E1" in content

    # Test XLSX Fabrication
    job = svc.request_export(tenant_id, project.project_id, ExportType.FABRICATION, ExportFormat.XLSX)
    job = svc.execute_export(tenant_id, job.job_id)
    assert job.status == ExportStatus.COMPLETED
    assert ".xlsx" in job.file_path

    # Test CSV Summary
    job = svc.request_export(tenant_id, project.project_id, ExportType.SUMMARY, ExportFormat.CSV)
    job = svc.execute_export(tenant_id, job.job_id)
    assert job.status == ExportStatus.COMPLETED
    
    content = storage.download_bytes(job.file_path).decode()
    assert "E1" in content
    assert "1" in content  # Count
