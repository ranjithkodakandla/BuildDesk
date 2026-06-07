"""
Kitchen Straight Template
=========================
Single straight kitchen run against a wall.

Defaults:
    width=120, depth=25, thickness=1.25
    splash: back only at 4"
    sink:   rectangle, centered

Parts produced:
    1  MAIN_TOP  (full width × depth, optional sink cutout)
    0–1 LOOSE_PIECE back splash
"""
from __future__ import annotations

import uuid

from app.models.fabrication import Assembly, AssemblyType, Dimensions, Part, PartType
from app.models.hierarchy import UnitVariant
from app.templates._helpers import build_sink_cutout, build_splash_parts, wall_edges
from app.templates.base import (
    BaseTemplate,
    SinkAlignment,
    SinkConfig,
    SinkShape,
    SplashConfig,
    TemplateCategory,
    TemplateConfig,
    TemplateDefinition,
)

_ID           = "KITCHEN_STRAIGHT"
_DISPLAY_NAME = "Straight Kitchen"
_DEFAULTS = {
    "width":     96,
    "depth":     25,
    "thickness": 1.25,
    "splash":    {"back": True, "left": False, "right": False, "height": 4.0},
    "sink":      {"shape": "rectangle", "alignment": "center",
                  "width": 33.0, "depth": 16.0, "corner_radius": 1.0},
    "edge_finish": "polished",
    "mirror":    False,
}


class KitchenStraightTemplate(BaseTemplate):
    """
    Straight kitchen run against one wall.

    Front, left, and right edges are polished (exposed).
    Back edge is raw (wall contact).
    Optional back splash at the rear.
    Optional sink cutout (rectangle by default, undermount).
    """

    @property
    def definition(self) -> TemplateDefinition:
        return TemplateDefinition(
            id=_ID,
            category=TemplateCategory.KITCHEN,
            display_name=_DISPLAY_NAME,
            description="Single straight kitchen run with optional sink and back splash.",
            defaults=_DEFAULTS,
            editable_fields=["width", "depth", "thickness", "splash", "sink",
                             "edge_finish", "mirror"],
            supported_features=["backsplash", "sink_rectangle", "sink_oval",
                                 "sink_offset_left", "sink_offset_right", "mirror"],
        )

    def build(self, config: TemplateConfig) -> Assembly:
        assembly_id = uuid.uuid4()
        variant     = UnitVariant.MIRROR if config.mirror else UnitVariant.STANDARD

        main_id  = uuid.uuid4()
        sink     = build_sink_cutout(
            main_id, config.sink, config.width, config.depth, mirror=config.mirror,
        )
        main_top = Part(
            part_id=main_id,
            assembly_id=assembly_id,
            part_type=PartType.MAIN_TOP,
            name="Main Top",
            dimensions=Dimensions(
                length=config.width,
                depth=config.depth,
                thickness=config.thickness,
            ),
            edges=wall_edges(main_id, config.edge_finish, mirror=config.mirror),
            cutouts=[sink] if sink else [],
        )

        splash_parts = build_splash_parts(
            assembly_id, config.splash,
            config.width, config.depth, config.thickness,
            mirror=config.mirror,
        )

        return Assembly(
            assembly_id=assembly_id,
            project_id=config.project_id,
            tenant_id=config.tenant_id,
            unit_id=config.unit_id,
            unit_type_id=config.unit_type_id,
            name=config.name or _DISPLAY_NAME,
            assembly_type=AssemblyType.KITCHEN,
            variant=variant,
            parts=[main_top, *splash_parts],
        )
