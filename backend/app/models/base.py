"""
Base Domain Model
=================
Shared foundation for all BuildDesk domain entities.

All models that represent persistent domain objects should inherit
from BaseDomainModel instead of Pydantic's BaseModel directly.

Provides:
    id          – UUID primary key (portable, non-guessable)
    created_at  – UTC timestamp set on creation
    updated_at  – UTC timestamp; must be refreshed on mutation
    schema_version – optional; used for StoneDesk interoperability
                     and future migration safety

Design decisions:
- id is named generically here; domain models alias it
  (e.g. tenant_id, project_id) for clarity at the API surface.
- schema_version defaults to "1.0"; bump when the shape/geometry
  schema changes in a breaking way.
- frozen=False: domain objects are mutable during their lifecycle
  (status changes, computed fields populated by engines).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class BaseDomainModel(BaseModel):
    """
    Reusable base for all BuildDesk domain entities.

    Usage::

        class Tenant(BaseDomainModel):
            tenant_id: uuid.UUID = Field(default_factory=uuid.uuid4)
            name: str
            ...
    """

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the record was first created",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of the last mutation; callers must refresh this",
    )
    schema_version: str = Field(
        default="1.0",
        description=(
            "Schema version string for this record. "
            "Used for StoneDesk interoperability and migration safety."
        ),
    )

    def touch(self) -> None:
        """Refresh updated_at to the current UTC time."""
        self.updated_at = datetime.now(timezone.utc)

    model_config = {"frozen": False}
