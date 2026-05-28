"""
BuildDesk Domain Models
=======================
Public surface for all Pydantic domain models.

Import from here, not from individual modules, to keep coupling clean:

    from app.models import Tenant, Project, ShapeTemplate, GeometryModel, Package
    from app.models import BaseDomainModel
"""

from app.models.base import BaseDomainModel
from app.models.geometry import (
    GeometryModel,
    GeometryPiece,
    GeometryStatus,
)
from app.models.package import (
    Package,
    PackageFormat,
    PackageStatus,
    PackageType,
)
from app.models.project import Project, ProjectStatus
from app.models.shape_template import (
    DimensionUnit,
    ShapeCategory,
    ShapeParameter,
    ShapeParameterType,
    ShapeTemplate,
)
from app.models.tenant import Tenant, TenantPlan, TenantStatus

__all__ = [
    # Base
    "BaseDomainModel",
    # Tenant
    "Tenant",
    "TenantPlan",
    "TenantStatus",
    # Project
    "Project",
    "ProjectStatus",
    # Shape Template
    "ShapeTemplate",
    "ShapeParameter",
    "ShapeParameterType",
    "ShapeCategory",
    "DimensionUnit",
    # Geometry
    "GeometryModel",
    "GeometryPiece",
    "GeometryStatus",
    # Package
    "Package",
    "PackageType",
    "PackageStatus",
    "PackageFormat",
]
