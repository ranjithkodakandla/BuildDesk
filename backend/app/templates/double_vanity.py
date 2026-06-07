"""
Double Vanity Template
======================
Wide vanity with two evenly-spaced sink cutouts.

Defaults:
    width=72, depth=22, thickness=1.25
    splash: back + left + right at 4"
    sink:   two oval cutouts at width/4 and 3*width/4

Parts produced:
    1  MAIN_TOP  (full width × depth, two sink cutouts)
    0–3 LOOSE_PIECE splash pieces
"""
from __future__ import annotations

import uuid

from app.models.fabrication import Assembly, AssemblyType, Dimensions, Part, PartType
from app.models.hierarchy import UnitVariant
from app.templates._helpers import build_splash_parts, build_two_sinks, wall_edges
from app.templates.base import (
    BaseTemplate,
    SinkConfig,
    SinkShape,
    SplashConfig,
    TemplateCategory,
    TemplateConfig,
    TemplateDefinition,
)

_ID           = "DOUBLE_VANITY"
_DISPLAY_NAME = "Double Vanity"
_DEFAULTS = {
    "width":     72,
    "depth":     22,
    "thickness": 1.25,
    "splash":    {"back": True, "left": True, "right": True, "height": 4.0},
    "sink":      {"shape": "oval", "alignment": "center",
                  "major_axis": 16.0, "minor_axis": 12.0},
    "edge_finish": "polished",
    "mirror":    False,
}


class DoubleVanityTemplate(BaseTemplate):
    """
    Double-sink vanity.  Two evenly-spaced UNDERMOUNT sinks are placed
    automatically at width/4 and 3*width/4 — no manual positioning required.
    Mirror has no visible effect on the symmetric two-sink layout.
    """

    @property
    def definition(self) -> TemplateDefinition:
        return TemplateDefinition(
            id=_ID,
            category=TemplateCategory.VANITY,
            display_name=_DISPLAY_NAME,
            description="Wide vanity with two evenly-spaced sink cutouts.",
            defaults=_DEFAULTS,
            editable_fields=["width", "depth", "thickness", "splash", "sink",
                             "edge_finish", "mirror"],
            supported_features=["backsplash", "left_splash", "right_splash",
                                 "double_sink", "sink_oval", "sink_rectangle", "mirror"],
        )

    def build(self, config: TemplateConfig) -> Assembly:
        assembly_id = uuid.uuid4()
        variant     = UnitVariant.MIRROR if config.mirror else UnitVariant.STANDARD

        main_id  = uuid.uuid4()
        sinks    = build_two_sinks(
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
            cutouts=sinks,
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
            assembly_type=AssemblyType.VANITY,
            variant=variant,
            parts=[main_top, *splash_parts],
        )
