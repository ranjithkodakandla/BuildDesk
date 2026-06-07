"""
L-Kitchen Template
==================
Two-arm kitchen: a main run along one wall plus a perpendicular return leg.

Production evidence:
    Concord North "Left Kitchen" / "Right Kitchen" pages.
    Total run: ~112" split as ~63" main + ~49" return (or 49"+63" reversed).
    Two-depth geometry confirms two separate countertop pieces.

Geometry:
    Piece 1 — Main Run:  width × depth  (front/left/right exposed, back raw)
    Piece 2 — Return Leg: return_width × depth  (front/far-end exposed, back raw,
                          inner join edge raw)

The two pieces share a corner — the return_width end of the main run butts
against the return leg's join edge.

Defaults:
    width=84, depth=25, return_width=30, thickness=1.25
    splash: back only on main run
    sink:   rectangle, centered on main run

Parts produced:
    1  MAIN_TOP "Main Run"   (full width × depth, optional sink cutout)
    1  MAIN_TOP "Return Leg" (return_width × depth)
    0–1 LOOSE_PIECE back splash on main run
    0–1 LOOSE_PIECE back splash on return leg (if splash.right / left requested)

Mirror behaviour:
    Standard: return leg attaches at the LEFT end of the main run.
    Mirror:   return leg attaches at the RIGHT end of the main run.
    (matches "Left Kitchen" / "Right Kitchen" labelling in Concord drawings)
"""
from __future__ import annotations

import uuid

from app.models.fabrication import (
    Assembly, AssemblyType, Dimensions, Part, PartType,
    EdgeTreatment, EdgeType, Position,
)
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

_ID           = "KITCHEN_L"
_DISPLAY_NAME = "L-Kitchen"

# Return leg default width (the short perpendicular arm, typically 28–35")
_DEFAULT_RETURN = 30.0

_DEFAULTS = {
    "width":     84,
    "depth":     25,
    "thickness": 1.25,
    "splash":    {"back": True, "left": False, "right": False, "height": 4.0},
    "sink":      {"shape": "rectangle", "alignment": "center",
                  "width": 33.0, "depth": 16.0, "corner_radius": 1.0},
    "edge_finish": "polished",
    "mirror":    False,
    "extra_params": {"return_width": _DEFAULT_RETURN},
}


def _l_edges(
    part_id: uuid.UUID,
    edge_finish: EdgeType,
    *,
    is_return_leg: bool,
    mirror: bool,
) -> list[EdgeTreatment]:
    """
    Edge treatments for the L-kitchen's two pieces.

    Main run (standard, mirror=False):
        FRONT = finish  (facing room)
        BACK  = raw     (wall)
        LEFT  = raw     (return leg join)
        RIGHT = finish  (open end)

    Main run (mirror=True):
        FRONT = finish
        BACK  = raw
        LEFT  = finish  (open end)
        RIGHT = raw     (return leg join)

    Return leg (standard):
        FRONT = finish
        BACK  = raw     (wall)
        LEFT  = finish  (far end, exposed)
        RIGHT = raw     (join with main run; hidden)

    Return leg (mirror):
        FRONT = finish
        BACK  = raw
        LEFT  = raw     (join with main run)
        RIGHT = finish  (far end, exposed)
    """
    raw    = EdgeType.RAW
    finish = edge_finish

    if is_return_leg:
        if not mirror:
            left_e, right_e = finish, raw
        else:
            left_e, right_e = raw, finish
    else:
        # Main run
        if not mirror:
            left_e, right_e = raw, finish
        else:
            left_e, right_e = finish, raw

    return [
        EdgeTreatment(part_id=part_id, position=Position.FRONT, edge_type=finish),
        EdgeTreatment(part_id=part_id, position=Position.BACK,  edge_type=raw),
        EdgeTreatment(part_id=part_id, position=Position.LEFT,  edge_type=left_e),
        EdgeTreatment(part_id=part_id, position=Position.RIGHT, edge_type=right_e),
    ]


class KitchenLTemplate(BaseTemplate):
    """
    L-shaped kitchen — main run plus perpendicular return leg.

    Use extra_params["return_width"] to control the depth of the return leg.
    Mirror=True flips the return leg from the left end to the right end of
    the main run (equivalent to "Right Kitchen" vs "Left Kitchen" in field).
    """

    @property
    def definition(self) -> TemplateDefinition:
        return TemplateDefinition(
            id=_ID,
            category=TemplateCategory.KITCHEN,
            display_name=_DISPLAY_NAME,
            description=(
                "Two-arm L-shaped kitchen. Main run plus perpendicular return leg. "
                "Mirror flips the return to the opposite end."
            ),
            defaults=_DEFAULTS,
            editable_fields=["width", "depth", "thickness", "splash", "sink",
                             "edge_finish", "mirror", "return_width"],
            supported_features=["two_piece", "backsplash", "sink_rectangle",
                                 "sink_oval", "mirror", "return_leg"],
        )

    def build(self, config: TemplateConfig) -> Assembly:
        assembly_id = uuid.uuid4()
        variant     = UnitVariant.MIRROR if config.mirror else UnitVariant.STANDARD

        # Resolve return_width from extra_params (fall back to default)
        return_width = float(
            (config.extra_params or {}).get("return_width", _DEFAULT_RETURN)
        )

        # ── Main Run ──────────────────────────────────────────────────────
        main_id  = uuid.uuid4()
        sink     = build_sink_cutout(
            main_id, config.sink, config.width, config.depth, mirror=config.mirror,
        )
        main_top = Part(
            part_id=main_id,
            assembly_id=assembly_id,
            part_type=PartType.MAIN_TOP,
            name="Main Run",
            dimensions=Dimensions(
                length=config.width,
                depth=config.depth,
                thickness=config.thickness,
            ),
            edges=_l_edges(
                main_id, config.edge_finish,
                is_return_leg=False, mirror=config.mirror,
            ),
            cutouts=[sink] if sink else [],
        )

        # ── Return Leg ────────────────────────────────────────────────────
        ret_id  = uuid.uuid4()
        ret_top = Part(
            part_id=ret_id,
            assembly_id=assembly_id,
            part_type=PartType.MAIN_TOP,
            name="Return Leg",
            dimensions=Dimensions(
                length=return_width,
                depth=config.depth,
                thickness=config.thickness,
            ),
            edges=_l_edges(
                ret_id, config.edge_finish,
                is_return_leg=True, mirror=config.mirror,
            ),
            cutouts=[],
        )

        # ── Splash (back of main run only) ───────────────────────────────
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
            parts=[main_top, ret_top, *splash_parts],
        )
