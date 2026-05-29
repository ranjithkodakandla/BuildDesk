import csv
import io
import uuid
from typing import List, Dict, Any, Tuple

from app.models.imports import ImportJob, ImportStatus, ImportRecordError, ImportErrorSeverity, ImportMapping
from app.repositories.import_repository import ImportRepository
from app.services.hierarchy_service import HierarchyService
from app.models.hierarchy import UnitVariant


class ImportService:
    def __init__(self, import_repo: ImportRepository, hierarchy_svc: HierarchyService):
        self.import_repo = import_repo
        self.hierarchy_svc = hierarchy_svc

    def create_import_job(self, tenant_id: uuid.UUID, project_id: uuid.UUID, filename: str) -> ImportJob:
        job = ImportJob(
            job_id=uuid.uuid4(),
            project_id=project_id,
            tenant_id=tenant_id,
            filename=filename,
            status=ImportStatus.PENDING
        )
        return self.import_repo.save_job(job)

    def update_mapping(self, tenant_id: uuid.UUID, job_id: uuid.UUID, mapping: ImportMapping) -> ImportJob:
        job = self.import_repo.get_job(tenant_id, job_id)
        if not job:
            raise ValueError("Import job not found")
        job.column_mapping = mapping
        job.status = ImportStatus.MAPPED
        return self.import_repo.save_job(job)

    def _parse_csv(self, file_bytes: bytes) -> List[Dict[str, str]]:
        # Assume utf-8 for now
        decoded = file_bytes.decode('utf-8')
        reader = csv.DictReader(io.StringIO(decoded))
        return list(reader)

    def validate_import(self, tenant_id: uuid.UUID, job_id: uuid.UUID, file_bytes: bytes) -> Tuple[ImportJob, List[Dict]]:
        job = self.import_repo.get_job(tenant_id, job_id)
        if not job:
            raise ValueError("Import job not found")
            
        if not job.column_mapping:
            raise ValueError("Mapping not configured")
            
        mapping = job.column_mapping
        
        job.status = ImportStatus.VALIDATING
        self.import_repo.save_job(job)
        
        rows = self._parse_csv(file_bytes)
        job.total_rows = len(rows)
        
        # We need project hierarchy to validate references
        tree = self.hierarchy_svc.build_project_tree(tenant_id, job.project_id)
        
        errors = []
        valid_rows = []
        
        # Build maps for quick lookup
        bldg_map = {b.building.code: b.building for b in tree.buildings if b.building.code} if tree.buildings else {}
        # Also support matching by name for building
        for b in tree.buildings or []:
            bldg_map[b.building.name] = b.building
            
        # Floors are scoped to buildings in the system, but we can do a global lookup for simplistic importing
        floor_map = {}
        for b in tree.buildings:
            for f in b.floors:
                floor_map[f.floor.name] = f.floor
                if f.floor.number is not None:
                    floor_map[str(f.floor.number)] = f.floor
            
        type_map = {t.unit_type.code: t.unit_type for t in tree.unit_types if t.unit_type.code}
        for t in tree.unit_types:
            type_map[t.unit_type.name] = t.unit_type
            
        # Existing units map to check duplicates
        existing_units = {}
        # flat units
        for u in tree.units:
            existing_units[u.code] = u
        for b in tree.buildings:
            for u in b.units:
                existing_units[u.code] = u
            for f in b.floors:
                for u in f.units:
                    existing_units[u.code] = u
        
        for i, row in enumerate(rows):
            row_idx = i + 1
            unit_num = row.get(mapping.unit_number_col) if mapping.unit_number_col else None
            if not unit_num:
                errors.append(ImportRecordError(
                    row_index=row_idx, 
                    column=mapping.unit_number_col, 
                    message="Unit number is required",
                    severity=ImportErrorSeverity.ERROR
                ))
                continue
                
            if unit_num in existing_units:
                errors.append(ImportRecordError(
                    row_index=row_idx,
                    column=mapping.unit_number_col,
                    message=f"Unit {unit_num} already exists in project",
                    severity=ImportErrorSeverity.ERROR
                ))
                continue
                
            ut_id = None
            if mapping.unit_type_col and row.get(mapping.unit_type_col):
                t_val = row.get(mapping.unit_type_col)
                if t_val in type_map:
                    ut_id = type_map[t_val].unit_type_id
                else:
                    errors.append(ImportRecordError(
                        row_index=row_idx,
                        column=mapping.unit_type_col,
                        message=f"Unit Type '{t_val}' not found",
                        severity=ImportErrorSeverity.ERROR
                    ))
                    
            bldg_id = None
            if mapping.building_col and row.get(mapping.building_col):
                b_val = row.get(mapping.building_col)
                if b_val in bldg_map:
                    bldg_id = bldg_map[b_val].building_id
                else:
                    errors.append(ImportRecordError(
                        row_index=row_idx,
                        column=mapping.building_col,
                        message=f"Building '{b_val}' not found",
                        severity=ImportErrorSeverity.ERROR
                    ))
                    
            floor_id = None
            if mapping.floor_col and row.get(mapping.floor_col):
                f_val = row.get(mapping.floor_col)
                if f_val in floor_map:
                    f_record = floor_map[f_val]
                    # verify building matches if provided
                    if bldg_id and f_record.building_id != bldg_id:
                        errors.append(ImportRecordError(
                            row_index=row_idx,
                            column=mapping.floor_col,
                            message=f"Floor '{f_val}' does not belong to the specified building",
                            severity=ImportErrorSeverity.ERROR
                        ))
                    else:
                        floor_id = f_record.floor_id
                else:
                    errors.append(ImportRecordError(
                        row_index=row_idx,
                        column=mapping.floor_col,
                        message=f"Floor '{f_val}' not found",
                        severity=ImportErrorSeverity.ERROR
                    ))
            
            # If there are no errors for this row, it's valid
            if not any(e.row_index == row_idx for e in errors):
                valid_rows.append({
                    "code": unit_num,
                    "name": f"Unit {unit_num}",
                    "unit_type_id": ut_id,
                    "building_id": bldg_id,
                    "floor_id": floor_id
                })

        job.error_log = errors
        job.status = ImportStatus.VALIDATED
        self.import_repo.save_job(job)
        
        return job, valid_rows

    def execute_import(self, tenant_id: uuid.UUID, job_id: uuid.UUID, file_bytes: bytes) -> ImportJob:
        job, valid_rows = self.validate_import(tenant_id, job_id, file_bytes)
        
        if job.error_log:
            # If there are errors, we do not commit the import. It must be clean.
            job.status = ImportStatus.FAILED
            self.import_repo.save_job(job)
            raise ValueError("Cannot execute import with validation errors")
            
        job.status = ImportStatus.IMPORTING
        self.import_repo.save_job(job)
        
        created_count = 0
        try:
            tree = self.hierarchy_svc.build_project_tree(tenant_id, job.project_id)
            type_map_id = {t.unit_type.unit_type_id: t.unit_type for t in tree.unit_types}
            
            for r in valid_rows:
                # determine variant based on type
                variant = UnitVariant.STANDARD
                if r["unit_type_id"]:
                    ut = type_map_id.get(r["unit_type_id"])
                    if ut and ut.is_mirror:
                        variant = UnitVariant.MIRROR
                    elif ut and ut.is_ada:
                        variant = UnitVariant.ADA
                
                self.hierarchy_svc.add_unit(
                    tenant_id=tenant_id,
                    project_id=job.project_id,
                    name=r["name"],
                    code=r["code"],
                    unit_type_id=r["unit_type_id"],
                    building_id=r["building_id"],
                    floor_id=r["floor_id"],
                    variant=variant
                )
                created_count += 1
                
            job.processed_rows = created_count
            job.status = ImportStatus.COMPLETED
            self.import_repo.save_job(job)
            return job
            
        except Exception as e:
            job.status = ImportStatus.FAILED
            job.error_log.append(ImportRecordError(row_index=0, message=f"Internal import error: {str(e)}", severity=ImportErrorSeverity.FATAL))
            self.import_repo.save_job(job)
            raise e
