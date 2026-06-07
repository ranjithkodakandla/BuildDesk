"""
Offset Vanity Template
======================
Single-sink vanity where the sink can be offset to the left or right.
Identical to SingleVanity in structure; differs only in defaults
(sink alignment = LEFT, offset = 12").

Defaults:
    width=62, depth=22, thickness=1.25
    splash: back + left + right at 4"
    sink:   oval, left-aligned at 12" from left edge
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

_ID           = "OFFSET_VANITY"
_DISPLAY_NAME = "Offset Vanity"
_DEFAULTS = {
    "width":     62,
    "depth":     22,
    "thickness": 1.25,
    "splash":    {"back": True, "left": True, "right": True, "height": 4.0},
    "sink":      {"shape": "oval", "alignment": "left",
                  "major_axis": 16.0, "minor_axis": 12.0, "offset": 12.0},
    "edge_finish": "polished",
    "mirror":    False,
}


class OffsetVanityTemplate(BaseTemplate):
    """
    Offset single-sink vanity.  Same structure as SingleVanity; default
    sink placement is left-of-centre so the counter has a larger open section.
    Use mirror=True to flip to right-of-centre.
    """

    @property
    def definition(self) -> TemplateDefinition:
        return TemplateDefinition(
            id=_ID,
            category=TemplateCategory.VANITY,
            display_name=_DISPLAY_NAME,
            description="Single-sink vanity with left or right offset sink placement.",
            defaults=_DEFAULTS,
            editable_fields=["width", "depth", "thickness", "splash", "sink",
                             "edge_finish", "mirror"],
            supported_features=["backsplash", "left_splash", "right_splash",
                                 "sink_oval", "sink_rectangle",
                                 "sink_offset_left", "sink_offset_right", "mirror"],
        )

    def build(self, config: TemplateConfig) -> Assembly:
        assembly_id = uuid.uuid4()
        variant     = UnitVariant.MIRROR if config.mirror else UnitVariant.STANDARD

        main_id = uuid.uuid4()
        sink    = build_sink_cutout(
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
            assembly_type=AssemblyType.VANITY,
            variant=variant,
            parts=[main_top, *splash_parts],
        )
