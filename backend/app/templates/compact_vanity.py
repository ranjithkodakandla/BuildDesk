"""
Compact Vanity Template
=======================
Small-width vanity preset.  Back splash only (no side splashes by default
because side walls are close to the sink on narrow units).

Defaults:
    width=36, depth=22, thickness=1.25
    splash: back only at 4"
    sink:   oval, centered
"""
from __future__ import annotations

import uuid

from app.models.fabrication import Assembly, AssemblyType, Dimensions, Part, PartType
from app.models.hierarchy import UnitVariant
from app.templates._helpers import build_sink_cutout, build_splash_parts, wall_edges
from app.templates.base import (
    BaseTemplate,
    SinkConfig,
    SinkShape,
    SplashConfig,
    TemplateCategory,
    TemplateConfig,
    TemplateDefinition,
)

_ID           = "COMPACT_VANITY"
_DISPLAY_NAME = "Compact Vanity"
_DEFAULTS = {
    "width":     36,
    "depth":     22,
    "thickness": 1.25,
    "splash":    {"back": True, "left": False, "right": False, "height": 4.0},
    "sink":      {"shape": "oval", "alignment": "center",
                  "major_axis": 14.0, "minor_axis": 10.0},
    "edge_finish": "polished",
    "mirror":    False,
}


class CompactVanityTemplate(BaseTemplate):
    """
    Compact single-sink vanity.  Identical pipeline to SingleVanity but
    narrower defaults and no side splashes out-of-the-box.
    """

    @property
    def definition(self) -> TemplateDefinition:
        return TemplateDefinition(
            id=_ID,
            category=TemplateCategory.VANITY,
            display_name=_DISPLAY_NAME,
            description="Narrow vanity preset (36\") with back splash only.",
            defaults=_DEFAULTS,
            editable_fields=["width", "depth", "thickness", "splash", "sink",
                             "edge_finish", "mirror"],
            supported_features=["backsplash", "left_splash", "right_splash",
                                 "sink_oval", "sink_rectangle", "mirror"],
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
            assembly_type=AssemblyType.VANITY,
            variant=variant,
            parts=[main_top, *splash_parts],
        )
