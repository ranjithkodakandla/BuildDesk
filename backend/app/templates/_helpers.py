"""
Template Assembly Helpers
=========================
Shared functions used by all fabrication templates.

All functions return domain model objects (Part, EdgeTreatment, Cutout)
that compose into an Assembly.  No rendering logic lives here.
"""
from __future__ import annotations

import uuid
from typing import List, Optional

from app.models.fabrication import (
    Cutout, CutoutType, Dimensions, EdgeTreatment, EdgeType,
    MountType, Part, PartType, Position,
)
from app.templates.base import SinkAlignment, SinkConfig, SinkShape, SplashConfig


# ---------------------------------------------------------------------------
# Edge helpers
# ---------------------------------------------------------------------------

def wall_edges(
    part_id: uuid.UUID,
    edge_finish: EdgeType,
    *,
    mirror: bool = False,
) -> List[EdgeTreatment]:
    """
    Standard wall-mounted countertop edges:
        FRONT = edge_finish
        BACK  = RAW  (against wall)
        LEFT  = edge_finish
        RIGHT = edge_finish

    If mirror=True, LEFT and RIGHT are swapped.
    """
    left  = edge_finish
    right = edge_finish
    if mirror:
        left, right = right, left

    return [
        EdgeTreatment(part_id=part_id, position=Position.FRONT, edge_type=edge_finish),
        EdgeTreatment(part_id=part_id, position=Position.BACK,  edge_type=EdgeType.RAW),
        EdgeTreatment(part_id=part_id, position=Position.LEFT,  edge_type=left),
        EdgeTreatment(part_id=part_id, position=Position.RIGHT, edge_type=right),
    ]


def island_edges(
    part_id: uuid.UUID,
    edge_finish: EdgeType,
) -> List[EdgeTreatment]:
    """
    Island countertop edges: all four sides use edge_finish (all exposed).
    Mirror is irrelevant for a symmetric island.
    """
    return [
        EdgeTreatment(part_id=part_id, position=Position.FRONT, edge_type=edge_finish),
        EdgeTreatment(part_id=part_id, position=Position.BACK,  edge_type=edge_finish),
        EdgeTreatment(part_id=part_id, position=Position.LEFT,  edge_type=edge_finish),
        EdgeTreatment(part_id=part_id, position=Position.RIGHT, edge_type=edge_finish),
    ]


# ---------------------------------------------------------------------------
# Sink cutout helpers
# ---------------------------------------------------------------------------

def build_sink_cutout(
    part_id: uuid.UUID,
    sink_cfg: SinkConfig,
    top_width: float,
    top_depth: float,
    *,
    mirror: bool = False,
) -> Optional[Cutout]:
    """
    Build a single sink Cutout, or return None when shape=NONE.

    Horizontal center (center_x) logic:
        CENTER → top_width / 2
        LEFT   → sink_cfg.offset   (distance from left edge)
        RIGHT  → top_width - sink_cfg.offset
    Mirror flips LEFT ↔ RIGHT alignment before computing center_x.

    Vertical center (center_y) is always top_depth / 2.

    The drawing engine renders the cutout as a red dashed rectangle on
    the main top piece — the shape (OVAL/RECTANGLE) is not yet visually
    differentiated in the engine; bounding-box dimensions are used for both.
    """
    if sink_cfg.shape == SinkShape.NONE:
        return None

    if sink_cfg.shape == SinkShape.RECTANGLE:
        cut_w = sink_cfg.width
        cut_d = sink_cfg.depth
    else:  # OVAL — use bounding box
        cut_w = sink_cfg.major_axis
        cut_d = sink_cfg.minor_axis

    # Resolve alignment (mirror flips left ↔ right)
    alignment = sink_cfg.alignment
    if mirror:
        if alignment == SinkAlignment.LEFT:
            alignment = SinkAlignment.RIGHT
        elif alignment == SinkAlignment.RIGHT:
            alignment = SinkAlignment.LEFT

    if alignment == SinkAlignment.CENTER:
        cx = top_width / 2.0
    elif alignment == SinkAlignment.LEFT:
        cx = sink_cfg.offset
    else:  # RIGHT
        cx = top_width - sink_cfg.offset

    cy = top_depth / 2.0

    return Cutout(
        part_id=part_id,
        cutout_type=CutoutType.SINK,
        mount_type=MountType.UNDERMOUNT,
        dimensions=Dimensions(length=cut_w, depth=cut_d),
        center_x=cx,
        center_y=cy,
    )


def build_two_sinks(
    part_id: uuid.UUID,
    sink_cfg: SinkConfig,
    top_width: float,
    top_depth: float,
    *,
    mirror: bool = False,
) -> List[Cutout]:
    """
    Build two evenly-spaced sink cutouts for double-vanity layouts.

    Sinks are placed at top_width / 4 and 3 * top_width / 4.
    Mirror has no visible effect on a symmetric double sink layout.
    """
    if sink_cfg.shape == SinkShape.NONE:
        return []

    if sink_cfg.shape == SinkShape.RECTANGLE:
        cut_w, cut_d = sink_cfg.width, sink_cfg.depth
    else:
        cut_w, cut_d = sink_cfg.major_axis, sink_cfg.minor_axis

    cy = top_depth / 2.0
    dims = Dimensions(length=cut_w, depth=cut_d)

    return [
        Cutout(
            part_id=part_id,
            cutout_type=CutoutType.SINK,
            mount_type=MountType.UNDERMOUNT,
            dimensions=dims,
            center_x=top_width / 4.0,
            center_y=cy,
        ),
        Cutout(
            part_id=part_id,
            cutout_type=CutoutType.SINK,
            mount_type=MountType.UNDERMOUNT,
            dimensions=dims,
            center_x=3.0 * top_width / 4.0,
            center_y=cy,
        ),
    ]


# ---------------------------------------------------------------------------
# Splash part helpers
# ---------------------------------------------------------------------------

def build_splash_parts(
    assembly_id: uuid.UUID,
    splash_cfg: SplashConfig,
    top_width: float,
    top_depth: float,
    thickness: float,
    *,
    mirror: bool = False,
) -> List[Part]:
    """
    Build separate LOOSE_PIECE splash Parts from SplashConfig.

    The drawing engine (fabrication_drawing_engine.py) identifies splash parts
    by their shallow depth (≤ _SPLASH_MAX_DEPTH_IN = 5.5") and renders them
    in the top zone above the main countertop.

    Dimensions:
        Back splash:  length=top_width,  depth=splash_cfg.height
        Left splash:  length=top_depth,  depth=splash_cfg.height
        Right splash: length=top_depth,  depth=splash_cfg.height

    Mirror flips which side gets a left vs right splash.
    """
    parts: List[Part] = []
    h = splash_cfg.height

    # Resolve mirror
    make_left  = splash_cfg.left  if not mirror else splash_cfg.right
    make_right = splash_cfg.right if not mirror else splash_cfg.left

    if splash_cfg.back:
        parts.append(Part(
            part_id=uuid.uuid4(),
            assembly_id=assembly_id,
            part_type=PartType.LOOSE_PIECE,
            name="Back Splash",
            dimensions=Dimensions(length=top_width, depth=h, thickness=thickness),
        ))

    if make_left:
        parts.append(Part(
            part_id=uuid.uuid4(),
            assembly_id=assembly_id,
            part_type=PartType.LOOSE_PIECE,
            name="Left Splash",
            dimensions=Dimensions(length=top_depth, depth=h, thickness=thickness),
        ))

    if make_right:
        parts.append(Part(
            part_id=uuid.uuid4(),
            assembly_id=assembly_id,
            part_type=PartType.LOOSE_PIECE,
            name="Right Splash",
            dimensions=Dimensions(length=top_depth, depth=h, thickness=thickness),
        ))

    return parts
