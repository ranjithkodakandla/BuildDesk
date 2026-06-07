"""
Simple Config Mapper + Template UI Contracts  (Phase 3.5)
==========================================================
Two responsibilities in one module:

1. SimpleConfigMapper
   Converts SimpleTemplateConfig → TemplateConfig, resolving user-facing
   simplifications (sink size presets, edge finish labels) into the concrete
   geometry values that TemplateConfig and the template builders expect.

2. TemplateUIContract / get_ui_contract()
   Declares which fields to show in the Basic Mode UI for each template.
   The Phase 6 frontend reads these contracts to render the correct form
   without hard-coding per-template field visibility.

Nothing in this module touches the renderer, PDF exporter, SVG exporter,
or any database layer.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from app.models.fabrication import EdgeType
from app.templates.base import (
    SinkAlignment,
    SinkConfig,
    SinkShape,
    SplashConfig,
    TemplateConfig,
)
from app.templates.simple_config import (
    SimpleEdgeFinish,
    SimpleSinkConfig,
    SimpleSinkPosition,
    SimpleSinkType,
    SimpleSplashConfig,
    SimpleTemplateConfig,
    SinkSize,
)


# ---------------------------------------------------------------------------
# Sink dimension presets
# (hidden from users — they choose small / standard / large)
# ---------------------------------------------------------------------------

_RECT_PRESETS: Dict[str, Dict[str, float]] = {
    "small":    {"width": 28.0, "depth": 14.0, "corner_radius": 1.0},
    "standard": {"width": 33.0, "depth": 16.0, "corner_radius": 1.0},
    "large":    {"width": 36.0, "depth": 18.0, "corner_radius": 1.5},
}

_OVAL_PRESETS: Dict[str, Dict[str, float]] = {
    "small":    {"major_axis": 14.0, "minor_axis": 10.0},
    "standard": {"major_axis": 16.0, "minor_axis": 12.0},
    "large":    {"major_axis": 19.0, "minor_axis": 14.0},
}

# Offset from the nearer edge for LEFT / RIGHT positioned sinks (inches).
# E.g. LEFT at 10" means the sink center is 10" from the left edge.
_SINK_OFFSET_IN: float = 10.0

# Edge finish label → EdgeType
_EDGE_FINISH_MAP: Dict[SimpleEdgeFinish, EdgeType] = {
    SimpleEdgeFinish.POLISHED: EdgeType.POLISHED,
    SimpleEdgeFinish.EASED:    EdgeType.EASED,
    SimpleEdgeFinish.MITER:    EdgeType.MITER,
    SimpleEdgeFinish.FLAT:     EdgeType.FLAT,
}


# ---------------------------------------------------------------------------
# Mapper
# ---------------------------------------------------------------------------

class SimpleConfigMapper:
    """
    Converts SimpleTemplateConfig → TemplateConfig.

    Stateless; instantiate once and reuse.
    """

    def to_template_config(self, simple: SimpleTemplateConfig) -> TemplateConfig:
        """
        Map every user-facing SimpleTemplateConfig field to the corresponding
        internal TemplateConfig field.

        Mapping table:
            width, depth, thickness, mirror  → 1-to-1 pass-through
            edge_finish (SimpleEdgeFinish)   → EdgeType via _EDGE_FINISH_MAP
            splash (SimpleSplashConfig)      → SplashConfig (same structure)
            sink.type + position + size      → SinkConfig with resolved dimensions
        """
        return TemplateConfig(
            template_id=simple.template_id,
            project_id=simple.project_id,
            tenant_id=simple.tenant_id,
            name=simple.name,
            unit_id=simple.unit_id,
            unit_type_id=simple.unit_type_id,
            width=simple.width,
            depth=simple.depth,
            thickness=simple.thickness,
            mirror=simple.mirror,
            edge_finish=_EDGE_FINISH_MAP[simple.edge_finish],
            splash=self._map_splash(simple.splash),
            sink=self._map_sink(simple.sink),
        )

    # ------------------------------------------------------------------
    # Splash
    # ------------------------------------------------------------------

    def _map_splash(self, s: SimpleSplashConfig) -> SplashConfig:
        """Direct structural mapping — no translation needed."""
        return SplashConfig(
            back=s.back,
            left=s.left,
            right=s.right,
            height=s.height,
        )

    # ------------------------------------------------------------------
    # Sink
    # ------------------------------------------------------------------

    def _map_sink(self, s: SimpleSinkConfig) -> SinkConfig:
        """
        Resolve (type, position, size) → SinkConfig with concrete dimensions.

        NONE  → SinkConfig(shape=NONE)
        RECTANGLE / OVAL → look up preset dimensions from size key,
                           convert position → SinkAlignment + offset.
        """
        if s.type == SimpleSinkType.NONE:
            return SinkConfig(shape=SinkShape.NONE)

        alignment = _position_to_alignment(s.position)
        offset    = _SINK_OFFSET_IN if s.position != SimpleSinkPosition.CENTER else 12.0

        if s.type == SimpleSinkType.RECTANGLE:
            p = _RECT_PRESETS[s.size.value]
            return SinkConfig(
                shape=SinkShape.RECTANGLE,
                alignment=alignment,
                width=p["width"],
                depth=p["depth"],
                corner_radius=p["corner_radius"],
                offset=offset,
            )

        # OVAL
        p = _OVAL_PRESETS[s.size.value]
        return SinkConfig(
            shape=SinkShape.OVAL,
            alignment=alignment,
            major_axis=p["major_axis"],
            minor_axis=p["minor_axis"],
            offset=offset,
        )


def _position_to_alignment(pos: SimpleSinkPosition) -> SinkAlignment:
    return {
        SimpleSinkPosition.CENTER: SinkAlignment.CENTER,
        SimpleSinkPosition.LEFT:   SinkAlignment.LEFT,
        SimpleSinkPosition.RIGHT:  SinkAlignment.RIGHT,
    }[pos]


# ---------------------------------------------------------------------------
# Public preset inspection helpers (used by tests and future docs/UI)
# ---------------------------------------------------------------------------

def rect_preset(size: SinkSize) -> Dict[str, float]:
    """Return the rectangle sink dimensions for a given size preset."""
    return dict(_RECT_PRESETS[size.value])


def oval_preset(size: SinkSize) -> Dict[str, float]:
    """Return the oval sink dimensions for a given size preset."""
    return dict(_OVAL_PRESETS[size.value])


# ---------------------------------------------------------------------------
# Template UI Contracts
# ---------------------------------------------------------------------------

UIFieldType = Literal["number", "boolean", "select"]


class UIFieldSpec(BaseModel):
    """
    Specification for a single form field in the Basic Mode UI.
    The Phase 6 frontend renders fields from this contract rather than
    hard-coding per-template forms.
    """
    key:        str          # dot-path in SimpleTemplateConfig: e.g. "sink.type"
    label:      str          # human label shown in the form
    field_type: UIFieldType
    visible:    bool         = True   # show this field by default
    required:   bool         = True
    unit:       Optional[str] = None  # "inches" or None
    options:    Optional[List[str]] = None   # for select fields
    hint:       Optional[str] = None  # tooltip or helper text


class TemplateUIContract(BaseModel):
    """
    Declares the Basic Mode UI form for one template.

    The frontend reads this to know which fields to display and
    what labels, options, and hints to use — without any template-specific
    logic embedded in the UI layer.
    """
    template_id:      str
    display_name:     str
    category:         str
    dimension_term:   str          # "Width" or "Length" depending on template
    fields:           List[UIFieldSpec]

    @property
    def visible_fields(self) -> List[UIFieldSpec]:
        return [f for f in self.fields if f.visible]


# ---------------------------------------------------------------------------
# Per-template UI contracts
# ---------------------------------------------------------------------------

_EDGE_OPTIONS    = ["polished", "eased", "miter", "flat"]
_SINK_TYPE_OPT   = ["none", "oval", "rectangle"]
_SINK_POS_OPT    = ["center", "left", "right"]
_SINK_SIZE_OPT   = ["small", "standard", "large"]


def _num(key: str, label: str, *, hint: str = "") -> UIFieldSpec:
    return UIFieldSpec(key=key, label=label, field_type="number",
                       unit="inches", hint=hint or None)


def _bool(key: str, label: str, *, hint: str = "") -> UIFieldSpec:
    return UIFieldSpec(key=key, label=label, field_type="boolean",
                       hint=hint or None)


def _sel(key: str, label: str, options: List[str], *, hint: str = "") -> UIFieldSpec:
    return UIFieldSpec(key=key, label=label, field_type="select",
                       options=options, hint=hint or None)


def _hidden(key: str, label: str, field_type: UIFieldType,
            options: Optional[List[str]] = None) -> UIFieldSpec:
    return UIFieldSpec(key=key, label=label, field_type=field_type,
                       visible=False, required=False, options=options)


_CONTRACTS: Dict[str, TemplateUIContract] = {

    "KITCHEN_L": TemplateUIContract(
        template_id="KITCHEN_L",
        display_name="L-Kitchen",
        category="kitchen",
        dimension_term="Main Length",
        fields=[
            _num("width",          "Main Length",
                 hint="Length of the main countertop run"),
            _num("depth",          "Depth",
                 hint="Front-to-back depth (standard kitchen: 25\")"),
            _num("thickness",      "Thickness"),
            _bool("splash.back",   "Back Splash"),
            _bool("splash.left",   "Left Splash"),
            _bool("splash.right",  "Right Splash"),
            _num("splash.height",  "Splash Height"),
            _sel("sink.type",      "Sink Type",     _SINK_TYPE_OPT),
            _sel("sink.position",  "Sink Position", _SINK_POS_OPT,
                 hint="Position in the main run"),
            _sel("sink.size",      "Sink Size",     _SINK_SIZE_OPT),
            _sel("edge_finish",    "Edge Finish",   _EDGE_OPTIONS),
            _bool("mirror",        "Mirror",
                  hint="Flips return leg to opposite end (Left ↔ Right Kitchen)"),
        ],
    ),

    "SINGLE_VANITY": TemplateUIContract(
        template_id="SINGLE_VANITY",
        display_name="Single Vanity",
        category="vanity",
        dimension_term="Width",
        fields=[
            _num("width",          "Width",         hint="Total countertop width"),
            _num("depth",          "Depth",         hint="Front-to-back measurement"),
            _num("thickness",      "Thickness",     hint="Stone slab thickness"),
            _bool("splash.back",   "Back Splash"),
            _bool("splash.left",   "Left Splash"),
            _bool("splash.right",  "Right Splash"),
            _num("splash.height",  "Splash Height", hint="Height of splash pieces"),
            _sel("sink.type",      "Sink Type",     _SINK_TYPE_OPT),
            _sel("sink.size",      "Sink Size",     _SINK_SIZE_OPT),
            _sel("edge_finish",    "Edge Finish",   _EDGE_OPTIONS),
            _bool("mirror",        "Mirror"),
            # Sink position hidden for single vanity — always center
            _hidden("sink.position", "Sink Position", "select", _SINK_POS_OPT),
        ],
    ),

    "OFFSET_VANITY": TemplateUIContract(
        template_id="OFFSET_VANITY",
        display_name="Offset Vanity",
        category="vanity",
        dimension_term="Width",
        fields=[
            _num("width",          "Width"),
            _num("depth",          "Depth"),
            _num("thickness",      "Thickness"),
            _bool("splash.back",   "Back Splash"),
            _bool("splash.left",   "Left Splash"),
            _bool("splash.right",  "Right Splash"),
            _num("splash.height",  "Splash Height"),
            _sel("sink.type",      "Sink Type",     _SINK_TYPE_OPT),
            _sel("sink.position",  "Sink Position", _SINK_POS_OPT,
                 hint="Left or right of center"),
            _sel("sink.size",      "Sink Size",     _SINK_SIZE_OPT),
            _sel("edge_finish",    "Edge Finish",   _EDGE_OPTIONS),
            _bool("mirror",        "Mirror",
                  hint="Flips sink position automatically"),
        ],
    ),

    "DOUBLE_VANITY": TemplateUIContract(
        template_id="DOUBLE_VANITY",
        display_name="Double Vanity",
        category="vanity",
        dimension_term="Width",
        fields=[
            _num("width",          "Width",
                 hint="Two sinks placed automatically at ¼ and ¾ of width"),
            _num("depth",          "Depth"),
            _num("thickness",      "Thickness"),
            _bool("splash.back",   "Back Splash"),
            _bool("splash.left",   "Left Splash"),
            _bool("splash.right",  "Right Splash"),
            _num("splash.height",  "Splash Height"),
            _sel("sink.type",      "Sink Type",     _SINK_TYPE_OPT,
                 hint="Same type used for both sinks"),
            _sel("sink.size",      "Sink Size",     _SINK_SIZE_OPT),
            _sel("edge_finish",    "Edge Finish",   _EDGE_OPTIONS),
            _bool("mirror",        "Mirror"),
            # Position hidden — double vanity always places sinks symmetrically
            _hidden("sink.position", "Sink Position", "select", _SINK_POS_OPT),
        ],
    ),

    "COMPACT_VANITY": TemplateUIContract(
        template_id="COMPACT_VANITY",
        display_name="Compact Vanity",
        category="vanity",
        dimension_term="Width",
        fields=[
            _num("width",          "Width",
                 hint="Narrow preset — default 36\""),
            _num("depth",          "Depth"),
            _num("thickness",      "Thickness"),
            _bool("splash.back",   "Back Splash"),
            _bool("splash.left",   "Left Splash"),
            _bool("splash.right",  "Right Splash"),
            _num("splash.height",  "Splash Height"),
            _sel("sink.type",      "Sink Type",     _SINK_TYPE_OPT),
            _sel("sink.size",      "Sink Size",     _SINK_SIZE_OPT),
            _sel("edge_finish",    "Edge Finish",   _EDGE_OPTIONS),
            _bool("mirror",        "Mirror"),
            _hidden("sink.position", "Sink Position", "select", _SINK_POS_OPT),
        ],
    ),

    "KITCHEN_STRAIGHT": TemplateUIContract(
        template_id="KITCHEN_STRAIGHT",
        display_name="Straight Kitchen",
        category="kitchen",
        dimension_term="Length",   # kitchens use "Length"
        fields=[
            _num("width",          "Length",
                 hint="Total run of countertop"),
            _num("depth",          "Depth",
                 hint="Standard kitchen depth is 25\""),
            _num("thickness",      "Thickness"),
            _bool("splash.back",   "Back Splash"),
            _bool("splash.left",   "Left Splash"),
            _bool("splash.right",  "Right Splash"),
            _num("splash.height",  "Splash Height"),
            _sel("sink.type",      "Sink Type",     _SINK_TYPE_OPT),
            _sel("sink.position",  "Sink Position", _SINK_POS_OPT,
                 hint="Center is most common for kitchens"),
            _sel("sink.size",      "Sink Size",     _SINK_SIZE_OPT),
            _sel("edge_finish",    "Edge Finish",   _EDGE_OPTIONS),
            _bool("mirror",        "Mirror"),
        ],
    ),

    "KITCHEN_STRAIGHT_REF": TemplateUIContract(
        template_id="KITCHEN_STRAIGHT_REF",
        display_name="Straight Kitchen + REF",
        category="kitchen",
        dimension_term="Length",
        fields=[
            _num("width",          "Length",
                 hint="Full run including refrigerator zone"),
            _num("depth",          "Depth"),
            _num("thickness",      "Thickness"),
            _bool("splash.back",   "Back Splash"),
            _bool("splash.left",   "Left Splash"),
            _bool("splash.right",  "Right Splash"),
            _num("splash.height",  "Splash Height"),
            _sel("sink.type",      "Sink Type",     _SINK_TYPE_OPT),
            _sel("sink.position",  "Sink Position", _SINK_POS_OPT),
            _sel("sink.size",      "Sink Size",     _SINK_SIZE_OPT),
            _sel("edge_finish",    "Edge Finish",   _EDGE_OPTIONS),
            _bool("mirror",        "Mirror",
                  hint="Moves refrigerator zone to opposite end"),
        ],
    ),

    "PLAIN_ISLAND": TemplateUIContract(
        template_id="PLAIN_ISLAND",
        display_name="Plain Island",
        category="island",
        dimension_term="Length",
        fields=[
            _num("width",          "Length",
                 hint="Longest dimension of the island"),
            _num("depth",          "Depth"),
            _num("thickness",      "Thickness"),
            _sel("edge_finish",    "Edge Finish",   _EDGE_OPTIONS,
                 hint="Applied to all four exposed edges"),
            _bool("mirror",        "Mirror"),
            # Splash and sink hidden — islands have no wall contact / no standard sink
            _hidden("splash.back",    "Back Splash",   "boolean"),
            _hidden("splash.left",    "Left Splash",   "boolean"),
            _hidden("splash.right",   "Right Splash",  "boolean"),
            _hidden("splash.height",  "Splash Height", "number"),
            _hidden("sink.type",      "Sink Type",     "select", _SINK_TYPE_OPT),
            _hidden("sink.position",  "Sink Position", "select", _SINK_POS_OPT),
            _hidden("sink.size",      "Sink Size",     "select", _SINK_SIZE_OPT),
        ],
    ),
}


def get_ui_contract(template_id: str) -> TemplateUIContract:
    """
    Return the UI contract for a given template.

    Raises KeyError if template_id is not found.
    All 7 built-in templates have contracts defined above.
    """
    try:
        return _CONTRACTS[template_id]
    except KeyError:
        available = ", ".join(sorted(_CONTRACTS.keys()))
        raise KeyError(
            f"No UI contract for template '{template_id}'. "
            f"Available: {available}"
        ) from None


def all_ui_contracts() -> List[TemplateUIContract]:
    """Return all UI contracts, ordered by category then template_id."""
    return sorted(_CONTRACTS.values(), key=lambda c: (c.category, c.template_id))


# ---------------------------------------------------------------------------
# Module-level mapper singleton
# ---------------------------------------------------------------------------

mapper: SimpleConfigMapper = SimpleConfigMapper()
