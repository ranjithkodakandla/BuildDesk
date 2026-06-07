"""
Template Configuration API Schemas  (Phase 3)
==============================================
Pydantic request / response models for the template-driven fabrication API.

These schemas sit between HTTP input and the internal TemplateConfig.
They add:
  - Strict upper-bound validation (production-safe dimension limits)
  - Cross-field validation (sink must fit within countertop)
  - String UUIDs for JSON API compatibility
  - to_template_config() converters for the service layer

Internal model path:
    HTTP JSON
      → TemplateConfigRequest  (this file — validates + normalises)
      → to_template_config()
      → TemplateConfig          (base.py — drives template builders)
      → registry.build(config)
      → Assembly                (fed to drawing engine)

Response model path:
    Assembly / TemplateDefinition
      → TemplateDefinitionResponse / TemplateConfigValidationResponse
      → JSON
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.fabrication import EdgeType
from app.templates.base import (
    SinkAlignment,
    SinkConfig,
    SinkShape,
    SplashConfig,
    TemplateCategory,
    TemplateConfig,
    TemplateDefinition,
)

# ---------------------------------------------------------------------------
# Dimension limits enforced at the API boundary
# (internal TemplateConfig trusts callers; API schema does not)
# ---------------------------------------------------------------------------
_MAX_WIDTH_IN     = 360.0   # 30 ft — absolute maximum countertop run
_MAX_DEPTH_IN     = 120.0   # 10 ft — absolute maximum depth (bar / island)
_MAX_THICKNESS_IN = 6.0     # thick laminated or waterfall edges
_MIN_DIM_IN       = 3.0     # minimum meaningful countertop span
_SINK_CLEARANCE   = 3.0     # minimum stone on each side of a sink cutout


# ---------------------------------------------------------------------------
# Sub-schemas
# ---------------------------------------------------------------------------

class SplashConfigRequest(BaseModel):
    """
    Splash piece configuration sent by the API client.
    Mirrors SplashConfig; re-declared here so API docs show full field details.
    """
    back:   bool  = Field(default=True,  description="Include back splash piece")
    left:   bool  = Field(default=True,  description="Include left side splash piece")
    right:  bool  = Field(default=True,  description="Include right side splash piece")
    height: float = Field(
        default=4.0, ge=1.0, le=12.0,
        description="Splash piece height in inches (1–12\")",
    )

    def to_splash_config(self) -> SplashConfig:
        return SplashConfig(
            back=self.back, left=self.left, right=self.right, height=self.height,
        )


class SinkConfigRequest(BaseModel):
    """
    Sink cutout configuration sent by the API client.
    Cross-field validation (size vs countertop) is done at TemplateConfigRequest level.
    """
    shape:     SinkShape     = Field(default=SinkShape.NONE,
                                     description="Sink cutout shape")
    alignment: SinkAlignment = Field(default=SinkAlignment.CENTER,
                                     description="Horizontal placement within the top")

    # Rectangle
    width:         float = Field(default=16.0, ge=4.0,  le=96.0,
                                 description="Sink width in inches (rectangle)")
    depth:         float = Field(default=12.0, ge=4.0,  le=60.0,
                                 description="Sink depth in inches (rectangle)")
    corner_radius: float = Field(default=0.0,  ge=0.0,  le=6.0,
                                 description="Rectangle sink corner radius (0 = square)")

    # Oval
    major_axis: float = Field(default=16.0, ge=4.0, le=96.0,
                              description="Oval sink longer axis in inches")
    minor_axis: float = Field(default=12.0, ge=4.0, le=60.0,
                              description="Oval sink shorter axis in inches")

    # Offset (for LEFT / RIGHT alignment)
    offset: float = Field(default=12.0, ge=2.0, le=60.0,
                          description="Distance from nearer edge for LEFT/RIGHT alignment")

    @model_validator(mode="after")
    def _check_oval_axes(self) -> "SinkConfigRequest":
        if self.shape == SinkShape.OVAL and self.major_axis < self.minor_axis:
            raise ValueError(
                f"Oval sink major_axis ({self.major_axis}\") must be ≥ "
                f"minor_axis ({self.minor_axis}\")."
            )
        return self

    @model_validator(mode="after")
    def _check_corner_radius(self) -> "SinkConfigRequest":
        if self.shape == SinkShape.RECTANGLE:
            half_min = min(self.width, self.depth) / 2.0
            if self.corner_radius > half_min:
                raise ValueError(
                    f"corner_radius ({self.corner_radius}\") exceeds half of the "
                    f"smaller sink dimension ({half_min:.2f}\")."
                )
        return self

    def to_sink_config(self) -> SinkConfig:
        return SinkConfig(
            shape=self.shape,
            alignment=self.alignment,
            width=self.width,
            depth=self.depth,
            corner_radius=self.corner_radius,
            major_axis=self.major_axis,
            minor_axis=self.minor_axis,
            offset=self.offset,
        )


# ---------------------------------------------------------------------------
# Primary request schema
# ---------------------------------------------------------------------------

class TemplateConfigRequest(BaseModel):
    """
    API request body for template-driven assembly generation.

    Differences from internal TemplateConfig:
      - project_id / tenant_id NOT included (injected from auth context in the route)
      - unit_id / unit_type_id are strings (UUID validation done here)
      - Strict upper bounds on all dimension fields
      - Cross-field validation: sink must fit in countertop with _SINK_CLEARANCE margin
    """
    template_id: str = Field(
        min_length=1, max_length=100,
        description="Template identifier (e.g. 'SINGLE_VANITY')",
    )
    name: str = Field(
        default="", max_length=200,
        description="Assembly name; falls back to template display_name if empty",
    )
    unit_id:      Optional[str] = Field(default=None, description="Optional unit UUID")
    unit_type_id: Optional[str] = Field(default=None, description="Optional unit-type UUID")

    # ── Dimensions ────────────────────────────────────────────────────────────
    width: float = Field(
        gt=_MIN_DIM_IN, le=_MAX_WIDTH_IN,
        description=f"Horizontal span in inches ({_MIN_DIM_IN}–{_MAX_WIDTH_IN}\")",
    )
    depth: float = Field(
        gt=_MIN_DIM_IN, le=_MAX_DEPTH_IN,
        description=f"Front-to-back depth in inches ({_MIN_DIM_IN}–{_MAX_DEPTH_IN}\")",
    )
    thickness: float = Field(
        default=1.25, gt=0.0, le=_MAX_THICKNESS_IN,
        description=f"Slab thickness in inches (>0–{_MAX_THICKNESS_IN}\")",
    )

    # ── Options ───────────────────────────────────────────────────────────────
    mirror:      bool               = Field(default=False)
    splash:      SplashConfigRequest = Field(default_factory=SplashConfigRequest)
    sink:        SinkConfigRequest   = Field(default_factory=SinkConfigRequest)
    edge_finish: EdgeType           = Field(default=EdgeType.POLISHED)

    # Template-specific extras (e.g. ref_width for KITCHEN_STRAIGHT_REF)
    extra_params: Dict[str, Any] = Field(default_factory=dict)

    # ── UUID validators ───────────────────────────────────────────────────────

    @field_validator("unit_id", "unit_type_id", mode="before")
    @classmethod
    def _validate_optional_uuid(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        try:
            uuid.UUID(str(v))
        except ValueError:
            raise ValueError(f"'{v}' is not a valid UUID.")
        return str(v)

    # ── Cross-field: sink must fit within countertop ──────────────────────────

    @model_validator(mode="after")
    def _sink_fits_in_top(self) -> "TemplateConfigRequest":
        """
        Ensure the sink cutout leaves at least _SINK_CLEARANCE\" of stone on
        each side.  Prevents physically impossible configurations from reaching
        the template builder.

        Clearance applies to both width and depth dimensions.
        """
        sink = self.sink
        if sink.shape == SinkShape.NONE:
            return self

        max_sink_w = self.width - 2.0 * _SINK_CLEARANCE
        max_sink_d = self.depth - 2.0 * _SINK_CLEARANCE

        if sink.shape == SinkShape.RECTANGLE:
            if sink.width > max_sink_w:
                raise ValueError(
                    f"Sink width {sink.width}\" leaves less than {_SINK_CLEARANCE}\" "
                    f"of stone on each side of the {self.width}\" countertop "
                    f"(maximum sink width: {max_sink_w:.1f}\")."
                )
            if sink.depth > max_sink_d:
                raise ValueError(
                    f"Sink depth {sink.depth}\" leaves less than {_SINK_CLEARANCE}\" "
                    f"of stone on each side of the {self.depth}\" countertop "
                    f"(maximum sink depth: {max_sink_d:.1f}\")."
                )

        elif sink.shape == SinkShape.OVAL:
            if sink.major_axis > max_sink_w:
                raise ValueError(
                    f"Oval major_axis {sink.major_axis}\" leaves less than "
                    f"{_SINK_CLEARANCE}\" of stone on each side of the {self.width}\" "
                    f"countertop (maximum: {max_sink_w:.1f}\")."
                )
            if sink.minor_axis > max_sink_d:
                raise ValueError(
                    f"Oval minor_axis {sink.minor_axis}\" leaves less than "
                    f"{_SINK_CLEARANCE}\" of stone on each side of the {self.depth}\" "
                    f"countertop (maximum: {max_sink_d:.1f}\")."
                )

        return self

    # ── Converter ─────────────────────────────────────────────────────────────

    def to_template_config(
        self,
        project_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> TemplateConfig:
        """
        Convert this API request to the internal TemplateConfig.

        project_id and tenant_id come from the authenticated request context
        (injected by the route handler in Phase 4) — they are NOT part of the
        HTTP request body.
        """
        return TemplateConfig(
            template_id=self.template_id,
            project_id=project_id,
            tenant_id=tenant_id,
            name=self.name,
            unit_id=uuid.UUID(self.unit_id) if self.unit_id else None,
            unit_type_id=uuid.UUID(self.unit_type_id) if self.unit_type_id else None,
            width=self.width,
            depth=self.depth,
            thickness=self.thickness,
            mirror=self.mirror,
            splash=self.splash.to_splash_config(),
            sink=self.sink.to_sink_config(),
            edge_finish=self.edge_finish,
            extra_params=self.extra_params,
        )


# ---------------------------------------------------------------------------
# Response schemas (used in Phase 4 routes)
# ---------------------------------------------------------------------------

class SplashConfigResponse(BaseModel):
    back:   bool
    left:   bool
    right:  bool
    height: float


class SinkConfigResponse(BaseModel):
    shape:      SinkShape
    alignment:  SinkAlignment
    width:      float
    depth:      float
    major_axis: float
    minor_axis: float
    offset:     float


class TemplateConfigResponse(BaseModel):
    """
    Echoes back the normalised configuration after template generation.
    Returned by POST /templates/{id}/generate in Phase 4.
    """
    template_id:  str
    name:         str
    width:        float
    depth:        float
    thickness:    float
    mirror:       bool
    splash:       SplashConfigResponse
    sink:         SinkConfigResponse
    edge_finish:  EdgeType
    extra_params: Dict[str, Any]

    @classmethod
    def from_template_config(cls, cfg: TemplateConfig) -> "TemplateConfigResponse":
        return cls(
            template_id=cfg.template_id,
            name=cfg.name,
            width=cfg.width,
            depth=cfg.depth,
            thickness=cfg.thickness,
            mirror=cfg.mirror,
            splash=SplashConfigResponse(
                back=cfg.splash.back,
                left=cfg.splash.left,
                right=cfg.splash.right,
                height=cfg.splash.height,
            ),
            sink=SinkConfigResponse(
                shape=cfg.sink.shape,
                alignment=cfg.sink.alignment,
                width=cfg.sink.width,
                depth=cfg.sink.depth,
                major_axis=cfg.sink.major_axis,
                minor_axis=cfg.sink.minor_axis,
                offset=cfg.sink.offset,
            ),
            edge_finish=cfg.edge_finish,
            extra_params=cfg.extra_params,
        )


class TemplateDefinitionResponse(BaseModel):
    """
    Template metadata returned by GET /templates and GET /templates/{id}.
    Used to populate the template picker UI in Phase 6.
    """
    id:                 str
    category:           TemplateCategory
    display_name:       str
    description:        str
    defaults:           Dict[str, Any]
    editable_fields:    List[str]
    supported_features: List[str]

    @classmethod
    def from_definition(cls, defn: TemplateDefinition) -> "TemplateDefinitionResponse":
        return cls(
            id=defn.id,
            category=defn.category,
            display_name=defn.display_name,
            description=defn.description,
            defaults=defn.defaults,
            editable_fields=defn.editable_fields,
            supported_features=defn.supported_features,
        )


class ConfigValidationErrorDetail(BaseModel):
    field:   Optional[str] = None
    message: str


class TemplateConfigValidationResponse(BaseModel):
    """
    Response from POST /templates/validate (Phase 4).
    Separates hard errors (reject) from warnings (proceed with caution).
    """
    valid:    bool
    errors:   List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
