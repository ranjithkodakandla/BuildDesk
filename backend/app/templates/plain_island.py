"""
Plain Island Template
=====================
Freestanding island countertop — no sink, all four edges exposed.

Defaults:
    width=84, depth=42, thickness=1.5  (islands are often thicker)
    splash: none (islands have no wall contact)
    sink:   none

Parts produced:
    1  ISLAND_TOP  (full width × depth, all edges polished)
"""
from __future__ import annotations

import uuid

from app.models.fabrication import Assembly, AssemblyType, Dimensions, Part, PartType
from app.models.hierarchy import UnitVariant
from app.templates._helpers import island_edges
from app.templates.base import (
    BaseTemplate,
    SinkConfig,
    SinkShape,
    SplashConfig,
    TemplateCategory,
    TemplateConfig,
    TemplateDefinition,
)

_ID           = "PLAIN_ISLAND"
_DISPLAY_NAME = "Plain Island"
_DEFAULTS = {
    "width":     84,
    "depth":     42,
    "thickness": 1.5,
    "splash":    {"back": False, "left": False, "right": False, "height": 4.0},
    "sink":      {"shape": "none"},
    "edge_finish": "polished",
    "mirror":    False,
}


class PlainIslandTemplate(BaseTemplate):
    """
    Plain freestanding island.

    All four edges are exposed and finished — there is no wall edge.
    island_edges() is used so all sides receive edge_finish.
    Splash and sink configs are intentionally ignored in build()
    because an island has no wall contact and no standard sink.
    Users who need a prep sink on an island should use KitchenStraight
    with an adjusted depth, or configure a custom sink via SinkConfig.
    """

    @property
    def definition(self) -> TemplateDefinition:
        return TemplateDefinition(
            id=_ID,
            category=TemplateCategory.ISLAND,
            display_name=_DISPLAY_NAME,
            description="Freestanding island top with all four edges exposed. No sink.",
            defaults=_DEFAULTS,
            editable_fields=["width", "depth", "thickness", "edge_finish"],
            supported_features=["all_edges_exposed"],
        )

    def build(self, config: TemplateConfig) -> Assembly:
        assembly_id = uuid.uuid4()
        variant     = UnitVariant.STANDARD  # mirror is not meaningful for islands

        island_id  = uuid.uuid4()
        island_top = Part(
            part_id=island_id,
            assembly_id=assembly_id,
            part_type=PartType.ISLAND_TOP,
            name="Island Top",
            dimensions=Dimensions(
                length=config.width,
                depth=config.depth,
                thickness=config.thickness,
            ),
            edges=island_edges(island_id, config.edge_finish),
        )

        return Assembly(
            assembly_id=assembly_id,
            project_id=config.project_id,
            tenant_id=config.tenant_id,
            unit_id=config.unit_id,
            unit_type_id=config.unit_type_id,
            name=config.name or _DISPLAY_NAME,
            assembly_type=AssemblyType.ISLAND,
            variant=variant,
            parts=[island_top],
        )
