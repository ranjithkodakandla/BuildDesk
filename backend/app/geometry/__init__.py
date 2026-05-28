"""
BuildDesk Geometry Package
==========================
Public surface for geometry primitives and computation utilities.

    from app.geometry import Point, Line, Rectangle, Circle
    from app.geometry import Polyline, DimensionLine, TextAnnotation
"""

from app.geometry.primitives import (
    Circle,
    DimensionLine,
    Line,
    Point,
    Polyline,
    Rectangle,
    TextAnnotation,
)

__all__ = [
    "Point",
    "Line",
    "Rectangle",
    "Circle",
    "Polyline",
    "DimensionLine",
    "TextAnnotation",
]
