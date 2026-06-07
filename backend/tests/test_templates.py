"""
Phase 2 — Template Registry Tests
===================================
Verifies that every template:
  - Is registered in the singleton registry
  - Produces a valid Assembly from its default config
  - Produces the correct assembly_type and part structure
  - Handles mirror=True without error
  - Handles splash=all-off without error
  - Handles sink=NONE without error
"""
from __future__ import annotations

import uuid

import pytest

from app.models.fabrication import (
    Assembly, AssemblyType, CutoutType, EdgeType, MountType,
    Part, PartType, Position,
)
from app.models.hierarchy import UnitVariant
from app.templates import (
    SinkAlignment, SinkConfig, SinkShape, SplashConfig,
    TemplateConfig, registry,
)
from app.templates.registry import TemplateNotFoundError

# ---------------------------------------------------------------------------
# Shared fixture helpers
# ---------------------------------------------------------------------------

_PROJECT_ID = uuid.uuid4()
_TENANT_ID  = uuid.uuid4()


def _cfg(template_id: str, **overrides) -> TemplateConfig:
    """Build a minimal TemplateConfig for a given template, using its defaults."""
    tmpl     = registry.get(template_id)
    defaults = tmpl.definition.defaults

    # Extract dimension defaults from the template's declared defaults
    width     = overrides.pop("width",     defaults.get("width",     62))
    depth     = overrides.pop("depth",     defaults.get("depth",     22))
    thickness = overrides.pop("thickness", defaults.get("thickness", 1.25))

    return TemplateConfig(
        template_id=template_id,
        project_id=_PROJECT_ID,
        tenant_id=_TENANT_ID,
        width=width,
        depth=depth,
        thickness=thickness,
        **overrides,
    )


# ---------------------------------------------------------------------------
# Registry integrity
# ---------------------------------------------------------------------------

EXPECTED_IDS = {
    "KITCHEN_STRAIGHT",
    "KITCHEN_STRAIGHT_REF",
    "KITCHEN_L",
    "PLAIN_ISLAND",
    "SINGLE_VANITY",
    "OFFSET_VANITY",
    "DOUBLE_VANITY",
    "COMPACT_VANITY",
}


def test_registry_has_all_templates():
    assert set(registry.ids()) == EXPECTED_IDS


def test_registry_len():
    assert len(registry) == 8


def test_registry_contains():
    assert "SINGLE_VANITY" in registry
    assert "NONEXISTENT"   not in registry


def test_registry_unknown_raises():
    cfg = _cfg("SINGLE_VANITY")
    cfg.template_id = "DOES_NOT_EXIST"
    with pytest.raises(TemplateNotFoundError):
        registry.build(cfg)


def test_all_definitions_returns_all():
    defs = registry.all_definitions()
    assert len(defs) == 8
    ids = {d.id for d in defs}
    assert ids == EXPECTED_IDS


# ---------------------------------------------------------------------------
# Per-template smoke tests — valid Assembly produced
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("template_id", list(EXPECTED_IDS))
def test_build_returns_assembly(template_id):
    cfg      = _cfg(template_id)
    assembly = registry.build(cfg)
    assert isinstance(assembly, Assembly)
    assert assembly.project_id == _PROJECT_ID
    assert assembly.tenant_id  == _TENANT_ID
    assert len(assembly.parts) >= 1


@pytest.mark.parametrize("template_id", list(EXPECTED_IDS))
def test_build_mirror_does_not_raise(template_id):
    cfg      = _cfg(template_id, mirror=True)
    assembly = registry.build(cfg)
    assert isinstance(assembly, Assembly)


@pytest.mark.parametrize("template_id", list(EXPECTED_IDS))
def test_build_no_splash_does_not_raise(template_id):
    cfg = _cfg(
        template_id,
        splash=SplashConfig(back=False, left=False, right=False, height=4),
    )
    assembly = registry.build(cfg)
    assert isinstance(assembly, Assembly)


@pytest.mark.parametrize("template_id", list(EXPECTED_IDS))
def test_build_no_sink_does_not_raise(template_id):
    cfg = _cfg(template_id, sink=SinkConfig(shape=SinkShape.NONE))
    assembly = registry.build(cfg)
    assert isinstance(assembly, Assembly)


# ---------------------------------------------------------------------------
# Assembly type correctness
# ---------------------------------------------------------------------------

def test_kitchen_straight_assembly_type():
    asm = registry.build(_cfg("KITCHEN_STRAIGHT"))
    assert asm.assembly_type == AssemblyType.KITCHEN


def test_kitchen_straight_ref_assembly_type():
    asm = registry.build(_cfg("KITCHEN_STRAIGHT_REF"))
    assert asm.assembly_type == AssemblyType.KITCHEN


def test_plain_island_assembly_type():
    asm = registry.build(_cfg("PLAIN_ISLAND"))
    assert asm.assembly_type == AssemblyType.ISLAND


def test_vanity_assembly_types():
    for tid in ("SINGLE_VANITY", "OFFSET_VANITY", "DOUBLE_VANITY", "COMPACT_VANITY"):
        asm = registry.build(_cfg(tid))
        assert asm.assembly_type == AssemblyType.VANITY, tid


# ---------------------------------------------------------------------------
# SingleVanity — detailed structure
# ---------------------------------------------------------------------------

def test_single_vanity_default_structure():
    cfg = TemplateConfig(
        template_id="SINGLE_VANITY",
        project_id=_PROJECT_ID,
        tenant_id=_TENANT_ID,
        width=62,
        depth=22,
        thickness=1.25,
        splash=SplashConfig(back=True, left=True, right=True, height=4),
        sink=SinkConfig(shape=SinkShape.OVAL, alignment=SinkAlignment.CENTER,
                        major_axis=16, minor_axis=12),
    )
    asm = registry.build(cfg)

    # Should have 4 parts: 1 main top + 3 splashes
    assert len(asm.parts) == 4

    main_tops = [p for p in asm.parts if p.part_type == PartType.MAIN_TOP]
    splashes  = [p for p in asm.parts if p.part_type == PartType.LOOSE_PIECE]
    assert len(main_tops) == 1
    assert len(splashes)  == 3

    top = main_tops[0]
    assert top.dimensions.length    == 62
    assert top.dimensions.depth     == 22
    assert top.dimensions.thickness == 1.25


def test_single_vanity_main_top_edges():
    cfg = _cfg("SINGLE_VANITY", width=62, depth=22,
               sink=SinkConfig(shape=SinkShape.NONE))
    asm = registry.build(cfg)
    top = next(p for p in asm.parts if p.part_type == PartType.MAIN_TOP)

    edge_map = {e.position: e.edge_type for e in top.edges}
    assert edge_map[Position.FRONT] == EdgeType.POLISHED
    assert edge_map[Position.BACK]  == EdgeType.RAW
    assert edge_map[Position.LEFT]  == EdgeType.POLISHED
    assert edge_map[Position.RIGHT] == EdgeType.POLISHED


def test_single_vanity_sink_center():
    cfg = TemplateConfig(
        template_id="SINGLE_VANITY",
        project_id=_PROJECT_ID,
        tenant_id=_TENANT_ID,
        width=62,
        depth=22,
        sink=SinkConfig(shape=SinkShape.OVAL, alignment=SinkAlignment.CENTER,
                        major_axis=16, minor_axis=12),
        splash=SplashConfig(back=False, left=False, right=False),
    )
    asm = registry.build(cfg)
    top = next(p for p in asm.parts if p.part_type == PartType.MAIN_TOP)
    assert len(top.cutouts) == 1
    cutout = top.cutouts[0]
    assert cutout.cutout_type  == CutoutType.SINK
    assert cutout.mount_type   == MountType.UNDERMOUNT
    assert cutout.center_x     == pytest.approx(31.0)   # 62/2
    assert cutout.center_y     == pytest.approx(11.0)   # 22/2


def test_single_vanity_splash_dimensions():
    cfg = TemplateConfig(
        template_id="SINGLE_VANITY",
        project_id=_PROJECT_ID,
        tenant_id=_TENANT_ID,
        width=62,
        depth=22,
        splash=SplashConfig(back=True, left=True, right=False, height=4.5),
        sink=SinkConfig(shape=SinkShape.NONE),
    )
    asm = registry.build(cfg)
    splashes = [p for p in asm.parts if p.part_type == PartType.LOOSE_PIECE]
    assert len(splashes) == 2  # back + left only

    bs = next(p for p in splashes if p.name == "Back Splash")
    ls = next(p for p in splashes if p.name == "Left Splash")
    assert bs.dimensions.length == pytest.approx(62)    # matches top width
    assert bs.dimensions.depth  == pytest.approx(4.5)
    assert ls.dimensions.length == pytest.approx(22)    # matches top depth
    assert ls.dimensions.depth  == pytest.approx(4.5)


# ---------------------------------------------------------------------------
# Mirror tests
# ---------------------------------------------------------------------------

def test_single_vanity_mirror_variant():
    cfg = _cfg("SINGLE_VANITY", mirror=True,
               sink=SinkConfig(shape=SinkShape.NONE))
    asm = registry.build(cfg)
    assert asm.variant == UnitVariant.MIRROR


def test_single_vanity_standard_variant():
    cfg = _cfg("SINGLE_VANITY", mirror=False,
               sink=SinkConfig(shape=SinkShape.NONE))
    asm = registry.build(cfg)
    assert asm.variant == UnitVariant.STANDARD


def test_mirror_flips_sink_alignment():
    """LEFT-aligned sink becomes RIGHT-aligned under mirror."""
    cfg = TemplateConfig(
        template_id="OFFSET_VANITY",
        project_id=_PROJECT_ID,
        tenant_id=_TENANT_ID,
        width=62,
        depth=22,
        mirror=True,
        sink=SinkConfig(shape=SinkShape.OVAL, alignment=SinkAlignment.LEFT,
                        major_axis=16, minor_axis=12, offset=12),
        splash=SplashConfig(back=False, left=False, right=False),
    )
    asm    = registry.build(cfg)
    top    = next(p for p in asm.parts if p.part_type == PartType.MAIN_TOP)
    cutout = top.cutouts[0]
    # mirror=True converts LEFT→RIGHT: center_x = 62 - 12 = 50
    assert cutout.center_x == pytest.approx(50.0)


# ---------------------------------------------------------------------------
# Double Vanity — two sinks
# ---------------------------------------------------------------------------

def test_double_vanity_has_two_sinks():
    cfg = TemplateConfig(
        template_id="DOUBLE_VANITY",
        project_id=_PROJECT_ID,
        tenant_id=_TENANT_ID,
        width=72,
        depth=22,
        splash=SplashConfig(back=False, left=False, right=False),
        sink=SinkConfig(shape=SinkShape.OVAL, major_axis=16, minor_axis=12),
    )
    asm = registry.build(cfg)
    top = next(p for p in asm.parts if p.part_type == PartType.MAIN_TOP)
    assert len(top.cutouts) == 2
    centers = sorted(c.center_x for c in top.cutouts)
    assert centers[0] == pytest.approx(18.0)   # 72/4
    assert centers[1] == pytest.approx(54.0)   # 3*72/4


# ---------------------------------------------------------------------------
# Island — all edges exposed, no sink by default
# ---------------------------------------------------------------------------

def test_plain_island_all_edges_polished():
    cfg = _cfg("PLAIN_ISLAND", width=84, depth=42)
    asm = registry.build(cfg)
    top = next(p for p in asm.parts if p.part_type == PartType.ISLAND_TOP)
    edge_types = {e.edge_type for e in top.edges}
    assert edge_types == {EdgeType.POLISHED}   # all 4 edges


def test_plain_island_no_splash_parts():
    cfg = _cfg("PLAIN_ISLAND", width=84, depth=42)
    asm = registry.build(cfg)
    assert all(p.part_type == PartType.ISLAND_TOP for p in asm.parts)


# ---------------------------------------------------------------------------
# Kitchen + REF — note present
# ---------------------------------------------------------------------------

def test_kitchen_straight_ref_has_note():
    cfg = _cfg("KITCHEN_STRAIGHT_REF",
               extra_params={"ref_width": 36})
    asm = registry.build(cfg)
    assert len(asm.notes) >= 1
    assert any("REFRIGERATOR" in n.content for n in asm.notes)


def test_kitchen_straight_ref_note_respects_ref_width():
    cfg = _cfg("KITCHEN_STRAIGHT_REF",
               extra_params={"ref_width": 42})
    asm = registry.build(cfg)
    note = next(n for n in asm.notes if "REFRIGERATOR" in n.content)
    assert "42" in note.content


# ---------------------------------------------------------------------------
# Assembly name fallback
# ---------------------------------------------------------------------------

def test_assembly_name_fallback_to_display_name():
    cfg = _cfg("SINGLE_VANITY")   # no explicit name
    asm = registry.build(cfg)
    assert asm.name == "Single Vanity"


def test_assembly_name_override():
    cfg = _cfg("SINGLE_VANITY")
    cfg.name = "Master Bath"
    asm = registry.build(cfg)
    assert asm.name == "Master Bath"
