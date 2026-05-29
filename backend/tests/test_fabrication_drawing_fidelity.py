"""Drawing fidelity helpers — inch/mm dims, annotations, shop layout."""

from __future__ import annotations

import uuid

from app.exporters.fabrication_drawing_engine import (
    FabricationDrawingEngine,
    _parse_part_annotations,
    _piece_index_from_name,
    format_dimension_inch_mm,
)
from app.models.fabrication import Dimensions, Part, PartType


def test_format_dimension_inch_mm():
    assert format_dimension_inch_mm(28.5) == '28.5" [724]'
    assert format_dimension_inch_mm(31, precision=0) == '31" [787]'
    assert format_dimension_inch_mm(4.0) == '4" [102]'


def test_piece_index_from_name():
    assert _piece_index_from_name("Piece 3 — Main Top", 0) == 3
    assert _piece_index_from_name("Splash A", 5) == 5


def test_parse_part_annotations():
    ann = _parse_part_annotations("R1/8 corners; grain horizontal; break corner")
    assert ann["grain"] is True
    assert ann["break_corners"] is True
    assert "R1/8" in ann["radii"]


def test_shop_sheet_layout_splits_rows():
    engine = FabricationDrawingEngine()
    aid = uuid.uuid4()

    def mk(name: str, length: float, depth: float) -> Part:
        return Part(
            assembly_id=aid,
            part_type=PartType.MAIN_TOP,
            name=name,
            dimensions=Dimensions(length=length, depth=depth),
        )

    splashes = [mk("Piece 4", 28.5, 4.0), mk("Piece 5", 31.0, 4.0)]
    mains = [mk("Piece 1", 28.5, 30.0), mk("Piece 3", 40.5, 30.0)]
    parts = mains[:1] + splashes + mains[1:]
    layout = engine._compute_shop_sheet_layout(parts, zone_w=500.0, zone_h=300.0)
    assert layout["scale"] > 0
    assert len(layout["positions"]) == len(parts)
    ys = {p.name: layout["positions"][i][1] for i, p in enumerate(parts)}
    assert ys["Piece 4"] > ys["Piece 1"]
    assert ys["Piece 5"] > ys["Piece 1"]
