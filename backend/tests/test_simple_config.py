"""
Phase 3.5 — Simple Configuration Layer Tests
=============================================
Covers:
  1.  SimpleTemplateConfig construction
  2.  SimpleSinkConfig / SimpleSplashConfig defaults
  3.  Sink type mapping (NONE / RECTANGLE / OVAL)
  4.  Sink size presets (small / standard / large)
  5.  Sink position mapping (center / left / right)
  6.  Edge finish mapping (all 4 finishes)
  7.  Mirror pass-through
  8.  Splash pass-through
  9.  Full round-trip: SimpleTemplateConfig → TemplateConfig → Assembly
 10.  UI contracts (all 7 templates, field visibility)
 11.  Preset inspection helpers
"""
from __future__ import annotations

import uuid

import pytest

from app.models.fabrication import (
    AssemblyType, CutoutType, EdgeType, MountType, PartType,
)
from app.templates import registry
from app.templates.base import SinkAlignment, SinkConfig, SinkShape, SplashConfig
from app.templates.config_service import ConfigurationService
from app.templates.simple_config import (
    SimpleEdgeFinish,
    SimpleSinkConfig,
    SimpleSinkPosition,
    SimpleSinkType,
    SimpleSplashConfig,
    SimpleTemplateConfig,
    SinkSize,
)
from app.templates.simple_mapper import (
    SimpleConfigMapper,
    TemplateUIContract,
    UIFieldSpec,
    all_ui_contracts,
    get_ui_contract,
    mapper,
    oval_preset,
    rect_preset,
)

_PID = uuid.uuid4()
_TID = uuid.uuid4()


def _simple(template_id: str = "SINGLE_VANITY", **overrides) -> SimpleTemplateConfig:
    defaults: dict = dict(
        template_id=template_id,
        project_id=_PID,
        tenant_id=_TID,
        width=62, depth=22,
    )
    defaults.update(overrides)
    return SimpleTemplateConfig(**defaults)


# ===========================================================================
# 1. SimpleTemplateConfig construction
# ===========================================================================

class TestSimpleTemplateConfig:

    def test_defaults_applied(self):
        cfg = _simple()
        assert cfg.thickness    == pytest.approx(1.25)
        assert cfg.mirror       is False
        assert cfg.edge_finish  == SimpleEdgeFinish.POLISHED
        assert cfg.splash.back  is True
        assert cfg.splash.left  is True
        assert cfg.splash.right is True
        assert cfg.splash.height == pytest.approx(4.0)
        assert cfg.sink.type    == SimpleSinkType.NONE
        assert cfg.sink.position == SimpleSinkPosition.CENTER
        assert cfg.sink.size    == SinkSize.STANDARD

    def test_custom_dimensions(self):
        cfg = _simple(width=55, depth=20, thickness=1.5)
        assert cfg.width     == 55
        assert cfg.depth     == 20
        assert cfg.thickness == pytest.approx(1.5)

    def test_thickness_too_large_raises(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            _simple(thickness=10.0)

    def test_mirror_flag(self):
        cfg = _simple(mirror=True)
        assert cfg.mirror is True

    def test_all_template_ids_accepted(self):
        for tid in registry.ids():
            defaults = registry.get(tid).definition.defaults
            cfg = _simple(
                template_id=tid,
                width=defaults.get("width", 60),
                depth=defaults.get("depth", 22),
            )
            assert cfg.template_id == tid


# ===========================================================================
# 2. Preset inspection helpers
# ===========================================================================

class TestPresets:

    def test_rect_small(self):
        p = rect_preset(SinkSize.SMALL)
        assert p["width"] == pytest.approx(28.0)
        assert p["depth"] == pytest.approx(14.0)

    def test_rect_standard(self):
        p = rect_preset(SinkSize.STANDARD)
        assert p["width"] == pytest.approx(33.0)
        assert p["depth"] == pytest.approx(16.0)

    def test_rect_large(self):
        p = rect_preset(SinkSize.LARGE)
        assert p["width"] == pytest.approx(36.0)
        assert p["depth"] == pytest.approx(18.0)

    def test_oval_small(self):
        p = oval_preset(SinkSize.SMALL)
        assert p["major_axis"] == pytest.approx(14.0)
        assert p["minor_axis"] == pytest.approx(10.0)
        assert p["major_axis"] >= p["minor_axis"]

    def test_oval_standard(self):
        p = oval_preset(SinkSize.STANDARD)
        assert p["major_axis"] == pytest.approx(16.0)
        assert p["minor_axis"] == pytest.approx(12.0)

    def test_oval_large(self):
        p = oval_preset(SinkSize.LARGE)
        assert p["major_axis"] == pytest.approx(19.0)
        assert p["minor_axis"] == pytest.approx(14.0)

    def test_all_oval_presets_major_gte_minor(self):
        for size in SinkSize:
            p = oval_preset(size)
            assert p["major_axis"] >= p["minor_axis"], f"Oval {size}: major < minor"

    def test_larger_preset_is_bigger(self):
        small    = rect_preset(SinkSize.SMALL)
        standard = rect_preset(SinkSize.STANDARD)
        large    = rect_preset(SinkSize.LARGE)
        assert small["width"] < standard["width"] < large["width"]


# ===========================================================================
# 3. Sink type mapping — NONE
# ===========================================================================

class TestSinkNoneMapping:

    def test_none_produces_no_sink(self):
        cfg = _simple(sink=SimpleSinkConfig(type=SimpleSinkType.NONE))
        tc  = mapper.to_template_config(cfg)
        assert tc.sink.shape == SinkShape.NONE

    def test_default_sink_is_none(self):
        cfg = _simple()
        tc  = mapper.to_template_config(cfg)
        assert tc.sink.shape == SinkShape.NONE


# ===========================================================================
# 4. Sink type mapping — RECTANGLE
# ===========================================================================

class TestRectangleSinkMapping:

    def _rect(self, size=SinkSize.STANDARD, position=SimpleSinkPosition.CENTER):
        return SimpleSinkConfig(type=SimpleSinkType.RECTANGLE,
                                size=size, position=position)

    def test_shape_is_rectangle(self):
        tc = mapper.to_template_config(_simple(sink=self._rect()))
        assert tc.sink.shape == SinkShape.RECTANGLE

    def test_standard_dimensions(self):
        tc = mapper.to_template_config(_simple(sink=self._rect(SinkSize.STANDARD)))
        assert tc.sink.width == pytest.approx(33.0)
        assert tc.sink.depth == pytest.approx(16.0)

    def test_small_dimensions(self):
        tc = mapper.to_template_config(_simple(sink=self._rect(SinkSize.SMALL)))
        assert tc.sink.width == pytest.approx(28.0)

    def test_large_dimensions(self):
        tc = mapper.to_template_config(_simple(sink=self._rect(SinkSize.LARGE)))
        assert tc.sink.width == pytest.approx(36.0)

    def test_corner_radius_set(self):
        tc = mapper.to_template_config(_simple(sink=self._rect()))
        assert tc.sink.corner_radius > 0

    def test_center_alignment(self):
        tc = mapper.to_template_config(
            _simple(sink=self._rect(position=SimpleSinkPosition.CENTER))
        )
        assert tc.sink.alignment == SinkAlignment.CENTER

    def test_left_alignment(self):
        tc = mapper.to_template_config(
            _simple(sink=self._rect(position=SimpleSinkPosition.LEFT))
        )
        assert tc.sink.alignment == SinkAlignment.LEFT

    def test_right_alignment(self):
        tc = mapper.to_template_config(
            _simple(sink=self._rect(position=SimpleSinkPosition.RIGHT))
        )
        assert tc.sink.alignment == SinkAlignment.RIGHT


# ===========================================================================
# 5. Sink type mapping — OVAL
# ===========================================================================

class TestOvalSinkMapping:

    def _oval(self, size=SinkSize.STANDARD, position=SimpleSinkPosition.CENTER):
        return SimpleSinkConfig(type=SimpleSinkType.OVAL,
                                size=size, position=position)

    def test_shape_is_oval(self):
        tc = mapper.to_template_config(_simple(sink=self._oval()))
        assert tc.sink.shape == SinkShape.OVAL

    def test_standard_axes(self):
        tc = mapper.to_template_config(_simple(sink=self._oval(SinkSize.STANDARD)))
        assert tc.sink.major_axis == pytest.approx(16.0)
        assert tc.sink.minor_axis == pytest.approx(12.0)

    def test_small_axes(self):
        tc = mapper.to_template_config(_simple(sink=self._oval(SinkSize.SMALL)))
        assert tc.sink.major_axis == pytest.approx(14.0)
        assert tc.sink.minor_axis == pytest.approx(10.0)

    def test_large_axes(self):
        tc = mapper.to_template_config(_simple(sink=self._oval(SinkSize.LARGE)))
        assert tc.sink.major_axis == pytest.approx(19.0)
        assert tc.sink.minor_axis == pytest.approx(14.0)

    def test_major_always_gte_minor(self):
        for size in SinkSize:
            tc = mapper.to_template_config(_simple(sink=self._oval(size)))
            assert tc.sink.major_axis >= tc.sink.minor_axis

    def test_center_alignment(self):
        tc = mapper.to_template_config(
            _simple(sink=self._oval(position=SimpleSinkPosition.CENTER))
        )
        assert tc.sink.alignment == SinkAlignment.CENTER

    def test_left_alignment(self):
        tc = mapper.to_template_config(
            _simple(sink=self._oval(position=SimpleSinkPosition.LEFT))
        )
        assert tc.sink.alignment == SinkAlignment.LEFT


# ===========================================================================
# 6. Edge finish mapping
# ===========================================================================

class TestEdgeFinishMapping:

    def test_polished(self):
        tc = mapper.to_template_config(_simple(edge_finish=SimpleEdgeFinish.POLISHED))
        assert tc.edge_finish == EdgeType.POLISHED

    def test_eased(self):
        tc = mapper.to_template_config(_simple(edge_finish=SimpleEdgeFinish.EASED))
        assert tc.edge_finish == EdgeType.EASED

    def test_miter(self):
        tc = mapper.to_template_config(_simple(edge_finish=SimpleEdgeFinish.MITER))
        assert tc.edge_finish == EdgeType.MITER

    def test_flat(self):
        tc = mapper.to_template_config(_simple(edge_finish=SimpleEdgeFinish.FLAT))
        assert tc.edge_finish == EdgeType.FLAT

    def test_all_finishes_mapped(self):
        for finish in SimpleEdgeFinish:
            tc = mapper.to_template_config(_simple(edge_finish=finish))
            assert isinstance(tc.edge_finish, EdgeType)


# ===========================================================================
# 7. Mirror pass-through
# ===========================================================================

class TestMirrorPassthrough:

    def test_mirror_true(self):
        tc = mapper.to_template_config(_simple(mirror=True))
        assert tc.mirror is True

    def test_mirror_false(self):
        tc = mapper.to_template_config(_simple(mirror=False))
        assert tc.mirror is False


# ===========================================================================
# 8. Splash pass-through
# ===========================================================================

class TestSplashPassthrough:

    def test_all_on(self):
        s  = SimpleSplashConfig(back=True, left=True, right=True, height=4.0)
        tc = mapper.to_template_config(_simple(splash=s))
        assert tc.splash.back   is True
        assert tc.splash.left   is True
        assert tc.splash.right  is True
        assert tc.splash.height == pytest.approx(4.0)

    def test_back_only(self):
        s  = SimpleSplashConfig(back=True, left=False, right=False, height=6.0)
        tc = mapper.to_template_config(_simple(splash=s))
        assert tc.splash.back   is True
        assert tc.splash.left   is False
        assert tc.splash.right  is False
        assert tc.splash.height == pytest.approx(6.0)

    def test_all_off(self):
        s  = SimpleSplashConfig(back=False, left=False, right=False)
        tc = mapper.to_template_config(_simple(splash=s))
        assert tc.splash.back  is False


# ===========================================================================
# 9. Full round-trip: SimpleTemplateConfig → Assembly
# ===========================================================================

class TestRoundTrip:

    def test_single_vanity_oval_center(self):
        simple = _simple(
            template_id="SINGLE_VANITY",
            width=62, depth=22,
            sink=SimpleSinkConfig(type=SimpleSinkType.OVAL,
                                  position=SimpleSinkPosition.CENTER,
                                  size=SinkSize.STANDARD),
            splash=SimpleSplashConfig(back=True, left=True, right=True, height=4),
        )
        tc  = mapper.to_template_config(simple)
        asm = registry.build(tc)

        assert asm.assembly_type == AssemblyType.VANITY
        assert len(asm.parts)    == 4   # main top + 3 splashes
        top = next(p for p in asm.parts if p.part_type == PartType.MAIN_TOP)
        assert len(top.cutouts) == 1
        assert top.cutouts[0].center_x == pytest.approx(31.0)  # centered

    def test_offset_vanity_left_sink_mirror(self):
        simple = _simple(
            template_id="OFFSET_VANITY",
            width=62, depth=22,
            mirror=True,
            sink=SimpleSinkConfig(type=SimpleSinkType.OVAL,
                                  position=SimpleSinkPosition.LEFT,
                                  size=SinkSize.STANDARD),
            splash=SimpleSplashConfig(back=False, left=False, right=False),
        )
        tc  = mapper.to_template_config(simple)
        asm = registry.build(tc)
        top = next(p for p in asm.parts if p.part_type == PartType.MAIN_TOP)
        # LEFT position → SinkAlignment.LEFT; mirror flips to RIGHT → 62 - 10 = 52
        assert top.cutouts[0].center_x == pytest.approx(52.0)

    def test_double_vanity_two_sinks(self):
        simple = _simple(
            template_id="DOUBLE_VANITY",
            width=72, depth=22,
            sink=SimpleSinkConfig(type=SimpleSinkType.OVAL, size=SinkSize.STANDARD),
            splash=SimpleSplashConfig(back=False, left=False, right=False),
        )
        tc  = mapper.to_template_config(simple)
        asm = registry.build(tc)
        top = next(p for p in asm.parts if p.part_type == PartType.MAIN_TOP)
        assert len(top.cutouts) == 2

    def test_kitchen_straight_rectangle_sink(self):
        simple = _simple(
            template_id="KITCHEN_STRAIGHT",
            width=120, depth=25,
            sink=SimpleSinkConfig(type=SimpleSinkType.RECTANGLE,
                                  position=SimpleSinkPosition.CENTER,
                                  size=SinkSize.STANDARD),
            splash=SimpleSplashConfig(back=True, left=False, right=False),
        )
        tc  = mapper.to_template_config(simple)
        asm = registry.build(tc)
        assert asm.assembly_type == AssemblyType.KITCHEN
        top = next(p for p in asm.parts if p.part_type == PartType.MAIN_TOP)
        assert top.cutouts[0].dimensions.length == pytest.approx(33.0)

    def test_plain_island_no_sink_parts(self):
        simple = _simple(
            template_id="PLAIN_ISLAND",
            width=84, depth=42,
            sink=SimpleSinkConfig(type=SimpleSinkType.NONE),
        )
        tc  = mapper.to_template_config(simple)
        asm = registry.build(tc)
        assert asm.assembly_type == AssemblyType.ISLAND
        top = next(p for p in asm.parts if p.part_type == PartType.ISLAND_TOP)
        assert top.cutouts == []

    def test_all_templates_build_without_error(self):
        for tid in registry.ids():
            defn = registry.get(tid).definition
            simple = _simple(
                template_id=tid,
                width=defn.defaults.get("width", 60),
                depth=defn.defaults.get("depth", 22),
                sink=SimpleSinkConfig(type=SimpleSinkType.NONE),
                splash=SimpleSplashConfig(back=False, left=False, right=False),
            )
            tc  = mapper.to_template_config(simple)
            asm = registry.build(tc)
            assert len(asm.parts) >= 1, f"Template {tid} produced no parts"

    def test_eased_edge_on_kitchen(self):
        simple = _simple(
            template_id="KITCHEN_STRAIGHT",
            width=120, depth=25,
            edge_finish=SimpleEdgeFinish.EASED,
        )
        tc  = mapper.to_template_config(simple)
        asm = registry.build(tc)
        top = next(p for p in asm.parts if p.part_type == PartType.MAIN_TOP)
        front_edge = next(e for e in top.edges if e.position.value == "front")
        assert front_edge.edge_type == EdgeType.EASED


# ===========================================================================
# 10. UI Contracts
# ===========================================================================

class TestUIContracts:

    def test_all_templates_have_contract(self):
        for tid in registry.ids():
            contract = get_ui_contract(tid)
            assert contract.template_id == tid

    def test_unknown_template_raises(self):
        with pytest.raises(KeyError):
            get_ui_contract("DOES_NOT_EXIST")

    def test_all_ui_contracts_returns_all(self):
        contracts = all_ui_contracts()
        assert len(contracts) == 8
        ids = {c.template_id for c in contracts}
        assert ids == set(registry.ids())

    def test_single_vanity_sink_position_hidden(self):
        contract = get_ui_contract("SINGLE_VANITY")
        pos_field = next(f for f in contract.fields if f.key == "sink.position")
        assert pos_field.visible is False

    def test_offset_vanity_sink_position_visible(self):
        contract = get_ui_contract("OFFSET_VANITY")
        pos_field = next(f for f in contract.fields if f.key == "sink.position")
        assert pos_field.visible is True

    def test_plain_island_splash_hidden(self):
        contract = get_ui_contract("PLAIN_ISLAND")
        splash_fields = [f for f in contract.fields
                         if f.key.startswith("splash.") and not f.visible]
        assert len(splash_fields) == 4   # back, left, right, height all hidden

    def test_plain_island_sink_hidden(self):
        contract = get_ui_contract("PLAIN_ISLAND")
        sink_fields = [f for f in contract.fields
                       if f.key.startswith("sink.") and not f.visible]
        assert len(sink_fields) == 3   # type, position, size all hidden

    def test_kitchen_uses_length_term(self):
        contract = get_ui_contract("KITCHEN_STRAIGHT")
        assert contract.dimension_term == "Length"

    def test_vanity_uses_width_term(self):
        for tid in ("SINGLE_VANITY", "DOUBLE_VANITY", "COMPACT_VANITY", "OFFSET_VANITY"):
            assert get_ui_contract(tid).dimension_term == "Width"

    def test_visible_fields_helper(self):
        contract = get_ui_contract("SINGLE_VANITY")
        visible = contract.visible_fields
        assert all(f.visible for f in visible)
        hidden  = [f for f in contract.fields if not f.visible]
        assert len(visible) + len(hidden) == len(contract.fields)

    def test_kitchen_ref_has_all_controls(self):
        contract = get_ui_contract("KITCHEN_STRAIGHT_REF")
        visible_keys = {f.key for f in contract.visible_fields}
        assert "sink.position" in visible_keys
        assert "mirror"        in visible_keys

    def test_double_vanity_position_hidden(self):
        contract = get_ui_contract("DOUBLE_VANITY")
        pos_field = next(f for f in contract.fields if f.key == "sink.position")
        assert pos_field.visible is False   # symmetric layout needs no position choice

    def test_edge_finish_options_present(self):
        for tid in registry.ids():
            contract = get_ui_contract(tid)
            ef_field = next(
                (f for f in contract.fields if f.key == "edge_finish"), None
            )
            assert ef_field is not None, f"{tid}: no edge_finish field"
            assert "polished" in ef_field.options

    def test_select_fields_have_options(self):
        for contract in all_ui_contracts():
            for field in contract.fields:
                if field.field_type == "select" and field.visible:
                    assert field.options, (
                        f"{contract.template_id}.{field.key}: visible select with no options"
                    )
