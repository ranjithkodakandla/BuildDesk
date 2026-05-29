"""
Project Package Domain Models  (Phase 3)
=========================================
Core entities for BuildDesk's primary deliverable:
the multi-page project fabrication package.

Hierarchy:
    ProjectPackage
    └── PackagePage  (cover | type_sheet | assembly_drawing | summary)

Lifecycle:
    draft → generating → ready → archived
    Error state: generation_failed

Design decisions:
- PackageStatus tracks the generation lifecycle.
- storage_reference is reserved for future GCS upload (Phase 6).
- Packages are immutable once 'ready'; regeneration creates a new record.
- page_type drives the PackagePdfExporter page renderer dispatch.
- UnitTypeGroup and PackageSummary are intermediate data structures
  used by PackageGeneratorService during traversal — not persisted as models.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import Field

from app.models.base import BaseDomainModel


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ProjectPackageStatus(str, Enum):
    """Lifecycle states of a fabrication package."""
    DRAFT             = "draft"
    GENERATING        = "generating"
    READY             = "ready"
    GENERATION_FAILED = "generation_failed"
    ARCHIVED          = "archived"


class PackagePageType(str, Enum):
    """
    Types of pages in a fabrication package PDF.

    COVER            — Project identity (name, client, material, issue date, version)
    TYPE_SHEET       — One page per UnitType: code, qty, unit list, assembly list
    ASSEMBLY_DRAWING — One drawing per assembly type per unit type
    SUMMARY          — Final page: piece counts, assembly counts, sq ft totals
    """
    COVER             = "cover"
    TYPE_SHEET        = "type_sheet"
    ASSEMBLY_DRAWING  = "assembly_drawing"
    SUMMARY           = "summary"


# ---------------------------------------------------------------------------
# PackagePage — one page in the PDF
# ---------------------------------------------------------------------------

class PackagePage(BaseDomainModel):
    """
    A single page within a ProjectPackage.

    content_ref is a string that tells PackagePdfExporter what to render:
        'cover'
        'type_sheet::<unit_type_id>'
        'assembly_drawing::<unit_type_id>::<assembly_type>'
        'summary'
    """
    page_id:     uuid.UUID      = Field(default_factory=uuid.uuid4)
    package_id:  uuid.UUID      = Field(..., description="Parent package")
    page_number: int            = Field(..., description="1-indexed page order in PDF")
    page_type:   PackagePageType = Field(...)
    title:       str            = Field(..., max_length=300)
    content_ref: str            = Field(..., max_length=500)


# ---------------------------------------------------------------------------
# ProjectPackage — the full fabrication package record
# ---------------------------------------------------------------------------

class ProjectPackage(BaseDomainModel):
    """
    A versioned, multi-page PDF fabrication drawing package for one project.

    Generated from the live project hierarchy + assemblies at a point in time.
    Immutable once 'ready'. Regenerating creates a new ProjectPackage record.

    version examples: '1.0', 'Rev A', 'IFC', 'Rev B - 2026-06-01'
    """
    package_id:        uuid.UUID                = Field(default_factory=uuid.uuid4)
    project_id:        uuid.UUID                = Field(...)
    tenant_id:         uuid.UUID                = Field(...)
    version:           str                      = Field(default="1.0", max_length=50)
    issued_by:         Optional[str]            = Field(default=None, max_length=200)
    issued_date:       Optional[datetime]       = Field(default=None)
    revision_notes:    Optional[str]            = Field(default=None)
    status:            ProjectPackageStatus     = Field(default=ProjectPackageStatus.DRAFT)
    # Reserved for Phase 6 GCS upload (gs://... blob path or signed URL)
    storage_reference: Optional[str]            = Field(default=None, max_length=1000)
    file_size_bytes:   Optional[int]            = Field(default=None)
    generated_at:      Optional[datetime]       = Field(default=None)
    page_count:        int                      = Field(default=0)
    pages:             List[PackagePage]        = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Intermediate generation structures (used by service, not persisted as models)
# ---------------------------------------------------------------------------

class UnitTypeGroup(BaseDomainModel):
    """
    Groups all units sharing the same UnitType.
    This drives type-sheet generation:
        TYPE A — Qty 8 — Units: 101, 102, 201, 202 ...

    assembly_types lists which assembly types exist for this unit type,
    which drives the assembly drawing page generation.
    """
    unit_type_id:   uuid.UUID  = Field(...)
    unit_type_code: str        = Field(...)
    unit_type_name: str        = Field(...)
    is_mirror:      bool       = Field(default=False)
    is_ada:         bool       = Field(default=False)
    unit_count:     int        = Field(default=0)
    unit_codes:     List[str]  = Field(default_factory=list,
                                       description="Sorted list of unit codes for type sheet")
    assembly_types: List[str]  = Field(default_factory=list,
                                       description="Assembly types present for this unit type")


class PackageSummary(BaseDomainModel):
    """
    Computed totals for the Summary page.
    All counts and areas are accumulated during hierarchy traversal.
    """
    total_units:      int              = Field(default=0)
    total_assemblies: int              = Field(default=0)
    total_parts:      int              = Field(default=0)
    # Stone area totals
    total_area_sqin:  float            = Field(default=0.0,
                                               description="Total stone area in sq inches")
    total_area_sqft:  float            = Field(default=0.0,
                                               description="Total stone area in sq feet")
    # Breakdown dictionaries
    assembly_counts:  Dict[str, int]   = Field(default_factory=dict,
                                               description="{'kitchen': 8, 'vanity': 12}")
    unit_type_counts: Dict[str, int]   = Field(default_factory=dict,
                                               description="{'Type A': 8, 'Type B': 4}")
    part_counts_by_type: Dict[str, int] = Field(default_factory=dict,
                                                description="{'main_top': 16, 'splash': 8}")
