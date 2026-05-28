"""
Geometry Primitives
===================
Low-level, serializable geometric building blocks used throughout
the BuildDesk geometry pipeline.

These are pure data structures — no rendering, no SVG, no PDF.
They represent logical geometric entities that the geometry builder
assembles and that output engines later consume.

Primitives defined here:
    Point           – 2-D coordinate (x, y)
    Line            – segment between two Points
    Rectangle       – axis-aligned box (origin + width + height)
    Circle          – centre Point + radius
    Polyline        – ordered sequence of Points
    DimensionLine   – annotated measurement between two Points
    TextAnnotation  – free-text label anchored at a Point

Design decisions:
- All primitives carry a UUID id for referencing / deduplication.
- All primitives carry an optional label for human-readable identification.
- All primitives carry optional metadata Dict for extensibility
  (e.g. layer name, colour, line weight — consumed by output engines).
- Coordinates are unitless floats; the ShapeTemplate's DimensionUnit
  context determines the real-world unit.
- Primitives are plain Pydantic BaseModel (not BaseDomainModel) —
  they are value objects, not persisted domain entities.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Point
# ---------------------------------------------------------------------------

class Point(BaseModel):
    """
    A 2-D coordinate.

    The coordinate system is:
        origin (0, 0) at bottom-left
        x increases to the right
        y increases upward

    All other primitives are expressed in terms of Points.
    """

    point_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    x: float = Field(..., description="Horizontal coordinate")
    y: float = Field(..., description="Vertical coordinate")
    label: Optional[str] = Field(default=None)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def translate(self, dx: float, dy: float) -> "Point":
        """Return a new Point shifted by (dx, dy)."""
        return Point(x=self.x + dx, y=self.y + dy, label=self.label)

    def __repr__(self) -> str:
        return f"Point({self.x}, {self.y})"


# ---------------------------------------------------------------------------
# Line
# ---------------------------------------------------------------------------

class Line(BaseModel):
    """
    A straight line segment between two Points.

    Used for:
        - edge lines of a rectangle/polyline
        - construction lines in a shape
    """

    line_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    start: Point = Field(..., description="Start point of the segment")
    end: Point = Field(..., description="End point of the segment")
    label: Optional[str] = Field(default=None)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def length(self) -> float:
        """Euclidean length of the segment."""
        dx = self.end.x - self.start.x
        dy = self.end.y - self.start.y
        return (dx * dx + dy * dy) ** 0.5

    @model_validator(mode="after")
    def start_and_end_must_differ(self) -> "Line":
        if self.start.x == self.end.x and self.start.y == self.end.y:
            raise ValueError("Line start and end points must not be identical.")
        return self


# ---------------------------------------------------------------------------
# Rectangle
# ---------------------------------------------------------------------------

class Rectangle(BaseModel):
    """
    Axis-aligned rectangle defined by an origin point, width, and height.

    origin is the bottom-left corner.

    Derived corners:
        bottom-left  = origin
        bottom-right = (origin.x + width, origin.y)
        top-right    = (origin.x + width, origin.y + height)
        top-left     = (origin.x, origin.y + height)
    """

    rect_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    origin: Point = Field(..., description="Bottom-left corner")
    width: float = Field(..., gt=0, description="Horizontal extent")
    height: float = Field(..., gt=0, description="Vertical extent")
    label: Optional[str] = Field(default=None)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def perimeter(self) -> float:
        return 2 * (self.width + self.height)

    @property
    def corners(self) -> Dict[str, Point]:
        """Named corner points."""
        ox, oy = self.origin.x, self.origin.y
        return {
            "bottom_left":  Point(x=ox,                y=oy),
            "bottom_right": Point(x=ox + self.width,   y=oy),
            "top_right":    Point(x=ox + self.width,   y=oy + self.height),
            "top_left":     Point(x=ox,                y=oy + self.height),
        }

    @property
    def edges(self) -> List[Line]:
        """Four edges in counter-clockwise order: bottom, right, top, left."""
        c = self.corners
        return [
            Line(start=c["bottom_left"],  end=c["bottom_right"], label="bottom"),
            Line(start=c["bottom_right"], end=c["top_right"],    label="right"),
            Line(start=c["top_right"],    end=c["top_left"],     label="top"),
            Line(start=c["top_left"],     end=c["bottom_left"],  label="left"),
        ]

    @property
    def center(self) -> Point:
        return Point(
            x=self.origin.x + self.width / 2,
            y=self.origin.y + self.height / 2,
        )


# ---------------------------------------------------------------------------
# Circle
# ---------------------------------------------------------------------------

class Circle(BaseModel):
    """
    A circle defined by a centre Point and a radius.

    Used for:
        - sink cutout representation
        - corner-rounding annotations
    """

    circle_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    center: Point = Field(..., description="Centre of the circle")
    radius: float = Field(..., gt=0, description="Radius; must be positive")
    label: Optional[str] = Field(default=None)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def area(self) -> float:
        import math
        return math.pi * self.radius ** 2

    @property
    def circumference(self) -> float:
        import math
        return 2 * math.pi * self.radius


# ---------------------------------------------------------------------------
# Polyline
# ---------------------------------------------------------------------------

class Polyline(BaseModel):
    """
    An ordered sequence of Points forming a connected path.

    Used for:
        - L-shape kitchen outlines
        - irregular countertop shapes
        - future complex shape outlines

    closed=True means the last point is implicitly connected back to
    the first (forming a closed polygon).
    """

    polyline_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    points: List[Point] = Field(..., min_length=2, description="Ordered vertices; minimum 2")
    closed: bool = Field(default=False, description="True = last point connects back to first")
    label: Optional[str] = Field(default=None)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def segments(self) -> List[Line]:
        """Return all line segments in the polyline."""
        lines = [
            Line(start=self.points[i], end=self.points[i + 1])
            for i in range(len(self.points) - 1)
        ]
        if self.closed and len(self.points) >= 2:
            lines.append(Line(start=self.points[-1], end=self.points[0], label="closing"))
        return lines

    @property
    def total_length(self) -> float:
        return sum(seg.length for seg in self.segments)


# ---------------------------------------------------------------------------
# DimensionLine
# ---------------------------------------------------------------------------

class DimensionLine(BaseModel):
    """
    An annotated measurement between two Points.

    Represents a dimension callout on a drawing:
        ←——— 96" ———→

    Used by output engines to render dimension annotations on
    builder/installer packages.
    """

    dim_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    start: Point = Field(..., description="One end of the dimension")
    end: Point = Field(..., description="Other end of the dimension")
    value: float = Field(..., gt=0, description="The measured value")
    unit: str = Field(default="in", description="Unit abbreviation, e.g. 'in', 'mm'")
    label: Optional[str] = Field(
        default=None,
        description="Override display text; defaults to '{value} {unit}'",
    )
    offset: float = Field(
        default=0.5,
        description="Perpendicular offset from the measured line for placement",
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def display_text(self) -> str:
        return self.label or f"{self.value} {self.unit}"

    @property
    def geometric_length(self) -> float:
        """Actual Euclidean distance between start and end points."""
        dx = self.end.x - self.start.x
        dy = self.end.y - self.start.y
        return (dx * dx + dy * dy) ** 0.5


# ---------------------------------------------------------------------------
# TextAnnotation
# ---------------------------------------------------------------------------

class TextAnnotation(BaseModel):
    """
    A free-text label anchored at a Point.

    Used by output engines to place room labels, piece names,
    edge-profile callouts, and installer notes on drawings.
    """

    annotation_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    position: Point = Field(..., description="Anchor point for the text")
    text: str = Field(..., min_length=1, description="Text content to display")
    font_size: float = Field(default=12.0, gt=0, description="Logical font size")
    bold: bool = Field(default=False)
    label: Optional[str] = Field(default=None, description="Internal name for referencing")
    metadata: Dict[str, Any] = Field(default_factory=dict)
