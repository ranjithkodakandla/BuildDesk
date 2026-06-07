"""
Single Vanity Template
======================
Standard single-sink bathroom vanity countertop.

Defaults:
    width=62, depth=22, thickness=1.25
    splash: back + left + right at 4"
    sink:   oval, centered

Parts produced:
    1  MAIN_TOP  (full width × depth)
    0–3 LOOSE_PIECE splash pieces (depending on SplashConfig)
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

_ID           = "SINGLE_VANITY"
_DISPLAY_NAME = "Single Vanity"
_DEFAULTS = {
    "width":     62,
    "depth":     22,
    "thickness": 1.25,
    "splash":    {"back": True, "left": True, "right": True, "height": 4.0},
    "sink":      {"shape": "oval", "alignment": "center",
                  "major_axis": 16.0, "minor_axis": 12.0},
    "edge_finish": "polished",
    "mirror":    False,
}


class SingleVanityTemplate(BaseTemplate):
    """
    Single-sink vanity.  One MAIN_TOP + optional splash pieces.
    Sink cutout is centered by default; offset available via SinkConfig.alignment.
    """

    @property
    def definition(self) -> TemplateDefinition:
        return TemplateDefinition(
            id=_ID,
            category=TemplateCategory.VANITY,
            display_name=_DISPLAY_NAME,
            description="Standard single-sink vanity top with optional splashes.",
            defaults=_DEFAULTS,
            editable_fields=["width", "depth", "thickness", "splash", "sink",
                             "edge_finish", "mirror"],
            supported_features=["backsplash", "left_splash", "right_splash",
                                 "sink_oval", "sink_rectangle", "mirror"],
        )

    def build(self, config: TemplateConfig) -> Assembly:
        assembly_id = uuid.uuid4()
        variant     = UnitVariant.MIRROR if config.mirror else UnitVariant.STANDARD

        # ── Main top ────────────────────────────────────────────────────────
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

        # ── Splash pieces ────────────────────────────────────────────────────
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
