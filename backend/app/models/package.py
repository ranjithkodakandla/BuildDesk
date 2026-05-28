"""
Package Model
=============
A Package is a generated output artifact derived from a GeometryModel.

BuildDesk supports three output package types (from docs/mvp.md):
    Builder Package    – site-focused: layout, dimensions, quantities
    Installer Package  – field-focused: edge treatments, cutouts, install notes
    Manufacturer Package – fabrication-focused: exact cut pieces, material specs

Each package has a status that tracks the generation pipeline.
Packages are immutable once delivered; new versions create new Package records.

Design decisions:
- geometry_id links back to the source of truth (never denormalised)
- package_type is an enum so output engines can dispatch correctly
- storage_url is populated after the PDF is written to Cloud Storage (Phase 3)
- version allows regeneration without losing history

Inherits from BaseDomainModel: created_at, updated_at, schema_version, touch()
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Optional

from pydantic import Field

from app.models.base import BaseDomainModel


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class PackageType(str, Enum):
    """
    The three first-class output packages defined in the MVP.

    builder      → dimensions, layout, quantities for the site team
    installer    → field installation notes, edge details, cutout positions
    manufacturer → fabrication specs, cut-piece list, material requirements
    """
    builder = "builder"
    installer = "installer"
    manufacturer = "manufacturer"


class PackageStatus(str, Enum):
    """Lifecycle of a package generation job."""
    queued = "queued"           # generation requested, not yet started
    generating = "generating"   # output engine is running
    ready = "ready"             # PDF available at storage_url
    failed = "failed"           # generation failed; see error_message
    delivered = "delivered"     # sent to recipient (email / download)


class PackageFormat(str, Enum):
    """Output format of the generated artifact."""
    pdf = "pdf"
    xlsx = "xlsx"          # future: Excel cut-sheet export
    json = "json"          # future: machine-readable for integrations


# ---------------------------------------------------------------------------
# Core model
# ---------------------------------------------------------------------------

class Package(BaseDomainModel):
    """
    A generated output artifact for a specific geometry instance.

    One GeometryModel may produce multiple Package records
    (one per type: builder, installer, manufacturer).
    """

    package_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    geometry_id: uuid.UUID = Field(..., description="Source GeometryModel this package was generated from")
    project_id: uuid.UUID = Field(..., description="Parent project; denormalised for fast queries")
    tenant_id: uuid.UUID = Field(..., description="Owning tenant; enforces data isolation")

    package_type: PackageType = Field(..., description="Which output audience this package targets")
    format: PackageFormat = Field(default=PackageFormat.pdf)
    status: PackageStatus = Field(default=PackageStatus.queued)

    # Populated by the output engine after generation
    storage_url: Optional[str] = Field(
        default=None,
        description="GCS object URL (gs://...) or signed download URL; set after Phase 3",
    )

    # Versioning: regenerating produces a new record with version incremented
    version: int = Field(default=1, ge=1, description="Starts at 1; increments on regeneration")

    error_message: Optional[str] = Field(
        default=None,
        description="Populated when status=failed",
    )

    requested_by: Optional[uuid.UUID] = Field(
        default=None,
        description="User ID who triggered generation (future: user model)",
    )
