"""
Matrix Setup Schemas  (Phase 6)
================================
Request / response models for the bulk matrix unit-creation endpoint.

A matrix row represents one unit in the building:

    Building | Floor | Flat  | Template      | Mirror | ADA
    A        | 1     | 101   | SINGLE_VANITY | false  | false
    A        | 1     | 102   | SINGLE_VANITY | true   | false
    A        | 2     | 201   | KITCHEN_L     | false  | true

The endpoint is idempotent: submitting the same row twice creates the unit
only once.  Existing units are detected by (project, building_code,
floor_name, flat_code) and skipped with status="existing".
"""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Row input
# ---------------------------------------------------------------------------

class MatrixRowRequest(BaseModel):
    """One row in the matrix spreadsheet."""

    building: str = Field(
        min_length=1, max_length=20,
        description="Building code, e.g. 'A', 'North', 'Tower 1'",
    )
    floor: str = Field(
        min_length=1, max_length=20,
        description="Floor label, e.g. '1', '2', 'Ground'",
    )
    flat: str = Field(
        min_length=1, max_length=50,
        description="Unit / flat code, e.g. '101', 'A12', '4B'",
    )
    template: str = Field(
        min_length=1, max_length=50,
        description="Template ID from the template registry",
    )
    mirror: bool = Field(
        default=False,
        description="Mirror (Left ↔ Right) variant",
    )
    ada: bool = Field(
        default=False,
        description="ADA accessible variant",
    )

    @field_validator("building", "floor", "flat", "template", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()


class MatrixBulkRequest(BaseModel):
    """Full body for POST .../units/bulk-matrix."""

    rows: List[MatrixRowRequest] = Field(
        min_length=1, max_length=500,
        description="Matrix rows — up to 500 per call",
    )


# ---------------------------------------------------------------------------
# Row result
# ---------------------------------------------------------------------------

RowStatus = Literal["created", "existing", "error"]


class MatrixRowResult(BaseModel):
    """Result for a single matrix row."""

    row_index:    int
    building:     str
    floor:        str
    flat:         str
    template:     str
    mirror:       bool
    ada:          bool
    status:       RowStatus
    unit_id:      Optional[str] = None
    unit_type_id: Optional[str] = None
    building_id:  Optional[str] = None
    floor_id:     Optional[str] = None
    error:        Optional[str] = None


# ---------------------------------------------------------------------------
# Bulk response
# ---------------------------------------------------------------------------

class MatrixBulkResponse(BaseModel):
    """Summary returned after a bulk-matrix POST."""

    rows_processed:  int
    units_created:   int
    units_existing:  int
    units_errored:   int
    buildings_total: int
    floors_total:    int
    unit_types_total: int
    results:         List[MatrixRowResult]
