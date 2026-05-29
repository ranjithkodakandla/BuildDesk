import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.models import *  # import all tables
from app.models.imports import ImportMapping, ImportStatus, ImportErrorSeverity
from app.repositories.hierarchy_repository import ProjectHierarchyRepository
from app.repositories.import_repository import ImportRepository
from app.services.hierarchy_service import HierarchyService
from app.services.import_service import ImportService


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
    return uuid.UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture
def import_repo(db_session: Session) -> ImportRepository:
    return ImportRepository(db_session)


@pytest.fixture
def hierarchy_repo(db_session: Session) -> ProjectHierarchyRepository:
    return ProjectHierarchyRepository(db_session)


@pytest.fixture
def hierarchy_svc(hierarchy_repo) -> HierarchyService:
    return HierarchyService(hierarchy_repo)


@pytest.fixture
def svc(import_repo, hierarchy_svc) -> ImportService:
    return ImportService(import_repo, hierarchy_svc)


def test_import_workflow(svc: ImportService, hierarchy_svc: HierarchyService, tenant_id: uuid.UUID):
    # Setup project
    project = hierarchy_svc.create_project(tenant_id, "Test Project", has_buildings=True, has_floors=True)
    bldg = hierarchy_svc.add_building(tenant_id, project.project_id, name="Tower A", code="A")
    floor = hierarchy_svc.add_floor(tenant_id, project.project_id, bldg.building_id, name="1st Floor", number=1)
    type_a = hierarchy_svc.add_unit_type(tenant_id, project.project_id, code="A1", name="Type A1")
    
    # 1. Create Job
    job = svc.create_import_job(tenant_id, project.project_id, "schedule.csv")
    assert job.status == ImportStatus.PENDING
    
    # 2. Update mapping
    mapping = ImportMapping(
        unit_number_col="Unit",
        unit_type_col="Type",
        building_col="Bldg",
        floor_col="Floor"
    )
    job = svc.update_mapping(tenant_id, job.job_id, mapping)
    assert job.status == ImportStatus.MAPPED
    
    # 3. Validate
    csv_data = b"Unit,Type,Bldg,Floor\n101,A1,Tower A,1st Floor\n102,A1,Tower A,1st Floor\n"
    job, valid_rows = svc.validate_import(tenant_id, job.job_id, csv_data)
    assert job.status == ImportStatus.VALIDATED
    assert len(valid_rows) == 2
    assert len(job.error_log) == 0
    
    # 4. Execute
    job = svc.execute_import(tenant_id, job.job_id, csv_data)
    assert job.status == ImportStatus.COMPLETED
    assert job.processed_rows == 2
    
    # Verify units created
    units = hierarchy_svc.list_units(tenant_id, project.project_id)
    assert len(units) == 2
    codes = {u.code for u in units}
    assert "101" in codes
    assert "102" in codes


def test_import_validation_errors(svc: ImportService, hierarchy_svc: HierarchyService, tenant_id: uuid.UUID):
    project = hierarchy_svc.create_project(tenant_id, "Test Project", has_buildings=False, has_floors=False)
    
    job = svc.create_import_job(tenant_id, project.project_id, "errors.csv")
    mapping = ImportMapping(unit_number_col="Unit", unit_type_col="Type")
    svc.update_mapping(tenant_id, job.job_id, mapping)
    
    # Missing type, missing unit
    csv_data = b"Unit,Type\n,A1\n101,MissingType\n"
    job, valid_rows = svc.validate_import(tenant_id, job.job_id, csv_data)
    
    assert job.status == ImportStatus.VALIDATED
    assert len(job.error_log) == 2
    assert "Unit number is required" in job.error_log[0].message
    assert "not found" in job.error_log[1].message
    
    with pytest.raises(ValueError, match="Cannot execute import with validation errors"):
        svc.execute_import(tenant_id, job.job_id, csv_data)
