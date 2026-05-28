"""
Project Model
=============
A Project is a tenant-scoped collection of geometry instances and
their resulting output packages.

Examples:
    "Canyon Surfaces – Lot 42 Kitchen"
    "Builder A – Unit 7B Vanity"

Design decisions:
- tenant_id ties every project to a single tenant (no cross-tenant access)
- project_id is a UUID for portability
- address is optional at creation (may be entered later)
- status drives the workflow lifecycle

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

class ProjectStatus(str, Enum):
    """Lifecycle states of a project."""
    draft = "draft"
    in_progress = "in_progress"
    review = "review"
    complete = "complete"
    archived = "archived"


# ---------------------------------------------------------------------------
# Core model
# ---------------------------------------------------------------------------

class Project(BaseDomainModel):
    """
    A project belongs to exactly one tenant and groups geometry
    instances with their generated output packages.
    """

    project_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    tenant_id: uuid.UUID = Field(..., description="Owning tenant; enforces data isolation")
    name: str = Field(..., min_length=1, max_length=300, description="Human-readable project name")
    description: Optional[str] = Field(default=None, max_length=1000)
    address: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Job-site address; informational, not used in geometry",
    )
    status: ProjectStatus = Field(default=ProjectStatus.draft)
