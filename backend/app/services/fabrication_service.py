"""
Fabrication Service
===================
Domain service for managing fabrication assemblies.
Handles business logic, variant validation, and coordination with the repo.
"""

import uuid
from typing import List, Optional

from app.models.fabrication import Assembly, Part, EdgeTreatment, Cutout, Hole, Splash
from app.models.hierarchy import UnitVariant
from app.repositories.fabrication_repository import FabricationRepository
from app.repositories.hierarchy_repository import ProjectHierarchyRepository


class FabricationService:
    def __init__(self, fab_repo: FabricationRepository, hierarchy_repo: ProjectHierarchyRepository):
        self._fab_repo = fab_repo
        self._hierarchy_repo = hierarchy_repo

    def create_assembly(self, assembly: Assembly) -> Assembly:
        """
        Validates and saves a new assembly.
        Ensures the project and unit (if provided) actually exist.
        """
        # Validate Project
        project = self._hierarchy_repo.get_project(assembly.tenant_id, assembly.project_id)
        if not project:
            raise ValueError(f"Project {assembly.project_id} not found.")

        # Validate Unit/Type if provided
        if assembly.unit_id:
            unit = self._hierarchy_repo.get_unit(assembly.tenant_id, assembly.unit_id)
            if not unit:
                raise ValueError(f"Unit {assembly.unit_id} not found.")
            if unit.project_id != assembly.project_id:
                raise ValueError("Unit does not belong to the specified project.")
            # Inherit variant from unit if not explicitly set and unit has one
            if assembly.variant == UnitVariant.STANDARD and unit.variant != UnitVariant.STANDARD:
                assembly.variant = unit.variant

        if assembly.unit_type_id:
            unit_type = self._hierarchy_repo.get_unit_type(assembly.tenant_id, assembly.unit_type_id)
            if not unit_type:
                raise ValueError(f"UnitType {assembly.unit_type_id} not found.")

        # Perform domain validation on parts
        self._validate_assembly_structure(assembly)

        # Apply variant transformations if necessary (e.g., MIRROR)
        # In a real implementation, this would flip coordinates for cutouts and holes.
        # For Phase 2, we just ensure the variant is recorded.
        if assembly.variant == UnitVariant.MIRROR:
            self._apply_mirror_transform(assembly)

        return self._fab_repo.save_assembly(assembly)

    def get_assembly(self, tenant_id: uuid.UUID, assembly_id: uuid.UUID) -> Optional[Assembly]:
        return self._fab_repo.get_assembly(tenant_id, assembly_id)

    def list_assemblies(self, tenant_id: uuid.UUID, project_id: uuid.UUID) -> List[Assembly]:
        return self._fab_repo.list_assemblies(tenant_id, project_id)

    def update_assembly(self, assembly: Assembly) -> Assembly:
        """Full replacement of an assembly's parts and properties."""
        existing = self._fab_repo.get_assembly(assembly.tenant_id, assembly.assembly_id)
        if not existing:
            raise ValueError("Assembly not found.")
            
        self._validate_assembly_structure(assembly)
        return self._fab_repo.save_assembly(assembly)

    def delete_assembly(self, tenant_id: uuid.UUID, assembly_id: uuid.UUID) -> bool:
        return self._fab_repo.delete_assembly(tenant_id, assembly_id)

    # --- Private Helpers ---

    def _validate_assembly_structure(self, assembly: Assembly) -> None:
        """Domain validations for the assembly structure."""
        if not assembly.parts:
            # It's valid to have an empty assembly, but we might want to log it
            pass

        for part in assembly.parts:
            if part.dimensions.length <= 0 or part.dimensions.depth <= 0:
                raise ValueError(f"Part '{part.name}' must have positive length and depth.")
            
            for cutout in part.cutouts:
                if cutout.dimensions.length <= 0 or cutout.dimensions.depth <= 0:
                    raise ValueError("Cutout dimensions must be positive.")
                # Basic bounds checking could go here:
                # if cutout.center_x < 0 or cutout.center_x > part.dimensions.length:
                #     raise ValueError("Cutout center_x is outside part bounds.")

            for hole in part.holes:
                if hole.diameter <= 0:
                    raise ValueError("Hole diameter must be positive.")

    def _apply_mirror_transform(self, assembly: Assembly) -> None:
        """
        Placeholder for geometrical mirroring logic.
        Future phases will invert X coordinates for cutouts/holes across the part's center.
        """
        pass
