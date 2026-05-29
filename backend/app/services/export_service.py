import csv
import io
import uuid
import openpyxl
from datetime import datetime
from typing import List, Dict, Any, Tuple

from app.models.exports import ExportJob, ExportStatus, ExportType, ExportFormat
from app.repositories.export_repository import ExportRepository
from app.services.hierarchy_service import HierarchyService, ProjectTree
from app.services.fabrication_service import FabricationService

class ExportService:
    def __init__(self, export_repo: ExportRepository, hierarchy_svc: HierarchyService, fab_svc: FabricationService):
        self.export_repo = export_repo
        self.hierarchy_svc = hierarchy_svc
        self.fab_svc = fab_svc

    def request_export(self, tenant_id: uuid.UUID, project_id: uuid.UUID, export_type: ExportType, format: ExportFormat) -> ExportJob:
        job = ExportJob(
            job_id=uuid.uuid4(),
            project_id=project_id,
            tenant_id=tenant_id,
            export_type=export_type,
            format=format,
            status=ExportStatus.PENDING
        )
        return self.export_repo.save_job(job)

    def execute_export(self, tenant_id: uuid.UUID, job_id: uuid.UUID) -> ExportJob:
        job = self.export_repo.get_job(tenant_id, job_id)
        if not job:
            raise ValueError("Export job not found")
            
        job.status = ExportStatus.PROCESSING
        self.export_repo.save_job(job)
        
        try:
            tree = self.hierarchy_svc.build_project_tree(tenant_id, job.project_id)
            
            headers = []
            rows = []
            
            if job.export_type == ExportType.SCHEDULE:
                headers, rows = self._build_schedule_data(tree)
            elif job.export_type == ExportType.FABRICATION:
                headers, rows = self._build_fabrication_data(tenant_id, job.project_id, tree)
            elif job.export_type == ExportType.SUMMARY:
                headers, rows = self._build_summary_data(tenant_id, job.project_id, tree)
            else:
                raise ValueError(f"Unknown export type: {job.export_type}")
                
            file_bytes = self._generate_file(headers, rows, job.format)

            from app.services.cloud_storage import CloudStorageService

            content_types = {
                "csv": "text/csv",
                "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            }
            storage_svc = CloudStorageService()
            object_name = f"projects/{job.project_id}/exports/{job.job_id}.{job.format.value}"
            job.file_path = storage_svc.upload_bytes(
                object_name,
                file_bytes,
                content_type=content_types.get(job.format.value, "application/octet-stream"),
            )
            job.status = ExportStatus.COMPLETED
            self.export_repo.save_job(job)
            return job
            
        except Exception as e:
            job.status = ExportStatus.FAILED
            job.error_log = str(e)
            self.export_repo.save_job(job)
            raise e

    def _build_schedule_data(self, tree: ProjectTree) -> Tuple[List[str], List[Dict[str, Any]]]:
        headers = ["UnitNumber", "UnitType", "Building", "Floor", "Variant"]
        rows = []
        
        type_map = {t.unit_type.unit_type_id: t.unit_type for t in tree.unit_types}
        
        for u in tree.units:
            ut = type_map.get(u.unit_type_id) if u.unit_type_id else None
            rows.append({
                "UnitNumber": u.code,
                "UnitType": ut.code if ut else "",
                "Building": "",
                "Floor": "",
                "Variant": u.variant.value
            })
            
        for b in tree.buildings:
            for u in b.units:
                ut = type_map.get(u.unit_type_id) if u.unit_type_id else None
                rows.append({
                    "UnitNumber": u.code,
                    "UnitType": ut.code if ut else "",
                    "Building": b.building.name,
                    "Floor": "",
                    "Variant": u.variant.value
                })
            for f in b.floors:
                for u in f.units:
                    ut = type_map.get(u.unit_type_id) if u.unit_type_id else None
                    rows.append({
                        "UnitNumber": u.code,
                        "UnitType": ut.code if ut else "",
                        "Building": b.building.name,
                        "Floor": f.floor.name,
                        "Variant": u.variant.value
                    })
                    
        return headers, rows

    def _build_fabrication_data(self, tenant_id: uuid.UUID, project_id: uuid.UUID, tree: ProjectTree) -> Tuple[List[str], List[Dict[str, Any]]]:
        # A list of all parts across the project
        headers = ["UnitNumber", "UnitType", "Assembly", "Part", "PartType", "Length", "Depth", "SqFt"]
        rows = []
        
        type_map = {t.unit_type.unit_type_id: t.unit_type for t in tree.unit_types}
        
        # We need to list assemblies for each unit. 
        # For a large project, calling get_assemblies for every unit is N queries.
        # But this is a background job, so we can afford N queries or write a bulk fetch.
        
        # Flatten all units
        all_units = tree.units + [u for b in tree.buildings for u in b.units] + [u for b in tree.buildings for f in b.floors for u in f.units]
        
        for u in all_units:
            ut = type_map.get(u.unit_type_id) if u.unit_type_id else None
            assemblies = self.fab_svc.list_assemblies(tenant_id, u.unit_id)
            for asm in assemblies:
                for part in asm.parts:
                    sqft = (part.length * part.depth) / 144.0
                    rows.append({
                        "UnitNumber": u.code,
                        "UnitType": ut.code if ut else "",
                        "Assembly": asm.name,
                        "Part": part.name,
                        "PartType": part.type.value,
                        "Length": part.length,
                        "Depth": part.depth,
                        "SqFt": round(sqft, 2)
                    })
        return headers, rows

    def _build_summary_data(self, tenant_id: uuid.UUID, project_id: uuid.UUID, tree: ProjectTree) -> Tuple[List[str], List[Dict[str, Any]]]:
        # Count by unit type
        headers = ["UnitType", "Count", "TotalSqFt"]
        rows = []
        
        all_units = tree.units + [u for b in tree.buildings for u in b.units] + [u for b in tree.buildings for f in b.floors for u in f.units]
        type_counts = {}
        for u in all_units:
            type_counts[u.unit_type_id] = type_counts.get(u.unit_type_id, 0) + 1
            
        type_map = {t.unit_type.unit_type_id: t.unit_type for t in tree.unit_types}
        
        # Get one representative unit per type to compute SqFt per type
        for t_id, count in type_counts.items():
            ut = type_map.get(t_id)
            code = ut.code if ut else "Untyped"
            
            # Find first unit of this type to estimate sqft
            rep_unit = next((u for u in all_units if u.unit_type_id == t_id), None)
            total_sqft = 0.0
            if rep_unit:
                assemblies = self.fab_svc.list_assemblies(tenant_id, rep_unit.unit_id)
                for asm in assemblies:
                    for part in asm.parts:
                        total_sqft += (part.length * part.depth) / 144.0
                        
            rows.append({
                "UnitType": code,
                "Count": count,
                "TotalSqFt": round(total_sqft * count, 2)
            })
            
        return headers, rows

    def _generate_file(self, headers: List[str], rows: List[Dict[str, Any]], format: ExportFormat) -> bytes:
        if format == ExportFormat.CSV:
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)
            return output.getvalue().encode('utf-8')
        elif format == ExportFormat.XLSX:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.append(headers)
            for row in rows:
                ws.append([row.get(h, "") for h in headers])
            output = io.BytesIO()
            wb.save(output)
            return output.getvalue()
        else:
            raise ValueError("Unsupported format")

