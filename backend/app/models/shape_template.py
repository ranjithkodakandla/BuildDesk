"""
Shape Template Model
====================
A ShapeTemplate is a reusable parametric shape definition.

It declares which named variables (parameters) a shape accepts,
along with constraints on each parameter. When a user provides
concrete dimension values for those parameters, a GeometryModel
is produced.

MVP shapes (from docs/mvp.md):
    Island
    Vanity
    Straight Kitchen
    L Shape Kitchen

Design decisions:
- tenant_id is Optional: None means the template is system-wide (global library)
  A non-None tenant_id means the template was created by a specific tenant.
- parameters is a list of ShapeParameter, not a flat dict, to allow
  validation rules (min/max, unit, type, allowed_options) to travel with
  each parameter and be consumed by template_resolver.
- schema_version (from BaseDomainModel) enables future StoneDesk compatibility.

Inherits from BaseDomainModel: created_at, updated_at, schema_version, touch()
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any, List, Optional

from pydantic import Field

from app.models.base import BaseDomainModel


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ShapeCategory(str, Enum):
    """Broad category grouping for UI browsing."""
    kitchen = "kitchen"
    bathroom = "bathroom"
    island = "island"
    custom = "custom"


class DimensionUnit(str, Enum):
    """Supported measurement units."""
    inches = "inches"
    millimeters = "millimeters"
    centimeters = "centimeters"


class ShapeParameterType(str, Enum):
    """
    Runtime data type of a shape parameter.

    Used by the template resolver to apply type-aware validation.

        number  – numeric dimension (float); supports min/max
        string  – free-text annotation or label
        boolean – toggle flag (e.g. has_sink)
        select  – one value from a fixed allowed_options list
    """
    number = "number"
    string = "string"
    boolean = "boolean"
    select = "select"


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class ShapeParameter(BaseDomainModel):
    """
    A single named dimension variable on a shape template.

    The template_resolver uses the fields here to validate and normalise
    a runtime payload before creating a GeometryModel.

    Example (L Shape Kitchen):
        name="A", label="Leg A length", type="number",
        unit="inches", min_value=12, max_value=240
    """

    name: str = Field(..., description="Short variable name used in geometry formulas, e.g. 'A', 'Depth'")
    label: str = Field(..., description="Human-readable label shown in the UI")
    parameter_type: ShapeParameterType = Field(
        default=ShapeParameterType.number,
        description="Runtime data type; controls which validation rules apply",
    )
    unit: DimensionUnit = Field(default=DimensionUnit.inches)
    min_value: Optional[float] = Field(default=None, description="Minimum allowed value (number type only)")
    max_value: Optional[float] = Field(default=None, description="Maximum allowed value (number type only)")
    default_value: Optional[Any] = Field(default=None, description="Applied when the parameter is absent from the payload")
    required: bool = Field(default=True)
    allowed_options: Optional[List[str]] = Field(
        default=None,
        description="Exhaustive list of valid values (select type only)",
    )
    description: Optional[str] = Field(default=None)


# ---------------------------------------------------------------------------
# Core model
# ---------------------------------------------------------------------------

class ShapeTemplate(BaseDomainModel):
    """
    Parametric shape definition shared across a tenant's projects.

    system_template=True → available to all tenants (global library).
    system_template=False → private to the owning tenant.
    """

    template_id: uuid.UUID = Field(default_factory=uuid.uuid4)

    # None = system-wide template; UUID = tenant-specific template
    tenant_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Owning tenant. None indicates a system-level (global) template.",
    )

    name: str = Field(..., min_length=1, max_length=200)
    category: ShapeCategory = Field(default=ShapeCategory.custom)
    description: Optional[str] = Field(default=None, max_length=1000)
    parameters: List[ShapeParameter] = Field(
        default_factory=list,
        description="Ordered list of parametric dimension inputs for this shape",
    )
    system_template: bool = Field(
        default=False,
        description="True = built-in shape available to all tenants",
    )
