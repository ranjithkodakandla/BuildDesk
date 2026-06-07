"""
Kitchen Straight + REF Template
=================================
Straight kitchen run that includes a refrigerator zone.

The REF zone is a section at one end of the counter that is typically
shallower (counter does not extend over the fridge) or simply notated.

Phase 2: produces the same MAIN_TOP as KitchenStraight plus a
FabricationNote marking the REF zone width.  Geometric splitting of the
slab into run + REF section is deferred to Phase 4 (geometry adapter).

extra_params supported:
    ref_width (float, inches) — width of the refrigerator zone, default 36"

Defaults:
    width=120, depth=25, thickness=1.25
    splash: back only at 4"
    sink:   rectangle, centered
    ref_width=36  (via extra_params)
"""
from __future__ import annotations

import uuid

from app.models.fabrication import (
    Assembly, AssemblyType, Dimensions, FabricationNote, Part, PartType,
)
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

_ID           = "KITCHEN_STRAIGHT_REF"
_DISPLAY_NAME = "Straight Kitchen + REF"
_DEFAULTS = {
    "width":     108,
    "depth":     25,
    "thickness": 1.25,
    "splash":    {"back": True, "left": False, "right": False, "height": 4.0},
    "sink":      {"shape": "rectangle", "alignment": "center",
                  "width": 33.0, "depth": 16.0, "corner_radius": 1.0},
    "edge_finish": "polished",
    "mirror":    False,
    "extra_params": {"ref_width": 36},
}


class KitchenStraightRefTemplate(BaseTemplate):
    """
    Straight kitchen with refrigerator zone annotation.

    The REF width is read from config.extra_params["ref_width"] (default 36").
    A FabricationNote is added to the assembly stating the REF zone position.
    Full geometric splitting into two slab pieces is implemented in Phase 4.
    """

    @property
    def definition(self) -> TemplateDefinition:
        return TemplateDefinition(
            id=_ID,
            category=TemplateCategory.KITCHEN,
            display_name=_DISPLAY_NAME,
            description=(
                "Straight kitchen run with a refrigerator zone at one end. "
                "REF width set via extra_params.ref_width (default 36\")."
            ),
            defaults=_DEFAULTS,
            editable_fields=["width", "depth", "thickness", "splash", "sink",
                             "edge_finish", "mirror", "extra_params"],
            supported_features=["backsplash", "sink_rectangle", "sink_oval",
                                 "sink_offset_left", "sink_offset_right",
                                 "refrigerator_zone", "mirror"],
        )

    def build(self, config: TemplateConfig) -> Assembly:
        assembly_id = uuid.uuid4()
        variant     = UnitVariant.MIRROR if config.mirror else UnitVariant.STANDARD
        ref_width   = float(config.extra_params.get("ref_width", 36))

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

        ref_side = "right" if not config.mirror else "left"
        ref_note = FabricationNote(
            assembly_id=assembly_id,
            content=(
                f"REFRIGERATOR ZONE: {ref_width}\" at {ref_side} end. "
                f"Verify fridge opening before fabrication."
            ),
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
            notes=[ref_note],
        )
