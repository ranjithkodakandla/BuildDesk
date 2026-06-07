"""
Configuration Service  (Phase 3)
==================================
Validates a TemplateConfig against the registered template's declared
capabilities, fills in template defaults for omitted fields, and provides
a safe build path that refuses to proceed on validation failure.

Responsibilities:
    validate()      — check feature compatibility (errors + warnings)
    fill_defaults() — merge template defaults with caller-supplied overrides
    build_safe()    — validate then build; raises ValueError on errors

This service is intentionally free of:
    - HTTP / FastAPI concerns  (that's api/template_schemas.py)
    - Database I/O             (repositories handle that)
    - Rendering logic          (FabricationDrawingEngine handles that)

Usage::

    from app.templates.config_service import ConfigurationService
    from app.templates import registry

    svc = ConfigurationService(registry)

    # Validate before building
    result = svc.validate(config)
    if result.valid:
        assembly = svc.build_safe(config)

    # Fill in template defaults for a partial user dict
    config = svc.fill_defaults(
        template_id="SINGLE_VANITY",
        project_id=...,
        tenant_id=...,
        overrides={"width": 55, "mirror": True},
    )
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.models.fabrication import Assembly
from app.templates.base import (
    SinkConfig,
    SinkShape,
    SplashConfig,
    TemplateConfig,
)
from app.templates.registry import TemplateNotFoundError, TemplateRegistry


# ---------------------------------------------------------------------------
# Validation result
# ---------------------------------------------------------------------------

class ConfigValidationResult(BaseModel):
    """
    Output of ConfigurationService.validate().

    valid=True  → config is safe to pass to build_safe().
    valid=False → at least one hard error; do NOT build.
    warnings    → informational; build is still allowed.
    """
    valid:    bool
    errors:   List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    @property
    def has_warnings(self) -> bool:
        return bool(self.warnings)

    def __repr__(self) -> str:
        status = "VALID" if self.valid else "INVALID"
        return (
            f"ConfigValidationResult({status}, "
            f"errors={self.errors}, warnings={self.warnings})"
        )


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class ConfigurationService:
    """
    Validates TemplateConfig objects against the template registry and
    builds Assemblies through the safe path.

    Instantiate once per application (or test suite); the service is stateless.
    Pass the module-level `registry` singleton from app.templates in production.
    """

    def __init__(self, reg: TemplateRegistry) -> None:
        self._registry = reg

    # ------------------------------------------------------------------
    # validate
    # ------------------------------------------------------------------

    def validate(self, config: TemplateConfig) -> ConfigValidationResult:
        """
        Check that config is compatible with the target template.

        Checks (in order):
          1. Template exists in registry.
          2. Requested sink shape is in template.supported_features.
          3. Requested splash sides are in template.supported_features (warns, not errors).
          4. Mirror flag against template.supported_features (warns).
          5. Template-specific invariants (e.g. PLAIN_ISLAND ignores sinks).

        Pydantic field-level validation (bounds, oval axes, etc.) is enforced
        by TemplateConfig itself; this method adds semantic / compatibility checks.
        """
        errors:   List[str] = []
        warnings: List[str] = []

        # ── 1. Template exists ────────────────────────────────────────────────
        if config.template_id not in self._registry:
            available = ", ".join(self._registry.ids())
            errors.append(
                f"Unknown template '{config.template_id}'. "
                f"Available: {available}."
            )
            return ConfigValidationResult(valid=False, errors=errors, warnings=warnings)

        defn     = self._registry.get(config.template_id).definition
        features = set(defn.supported_features)

        # ── 2. Sink feature compatibility ─────────────────────────────────────
        # Two cases:
        #   a) Template declares NO sink support at all → warn, it will silently ignore the sink.
        #   b) Template declares SOME sink support but not the requested type → error.
        _has_any_sink_support = any(f.startswith("sink_") for f in features)

        if config.sink.shape == SinkShape.OVAL:
            if not _has_any_sink_support:
                warnings.append(
                    f"Template '{config.template_id}' does not support sinks. "
                    f"Sink configuration will be ignored."
                )
            elif "sink_oval" not in features:
                errors.append(
                    f"Template '{config.template_id}' does not support oval sinks "
                    f"(supported_features: {sorted(features)})."
                )
        elif config.sink.shape == SinkShape.RECTANGLE:
            if not _has_any_sink_support:
                warnings.append(
                    f"Template '{config.template_id}' does not support sinks. "
                    f"Sink configuration will be ignored."
                )
            elif "sink_rectangle" not in features:
                errors.append(
                    f"Template '{config.template_id}' does not support rectangle sinks "
                    f"(supported_features: {sorted(features)})."
                )

        # ── 3. Splash side compatibility (warnings only) ───────────────────────
        if config.splash.back and "backsplash" not in features:
            warnings.append(
                f"Template '{config.template_id}' does not declare 'backsplash' support; "
                f"back splash piece will still be generated."
            )
        if config.splash.left and "left_splash" not in features:
            warnings.append(
                f"Template '{config.template_id}' does not declare 'left_splash' support."
            )
        if config.splash.right and "right_splash" not in features:
            warnings.append(
                f"Template '{config.template_id}' does not declare 'right_splash' support."
            )

        # ── 4. Mirror compatibility ───────────────────────────────────────────
        if config.mirror and "mirror" not in features:
            warnings.append(
                f"Template '{config.template_id}' does not declare 'mirror' support; "
                f"mirror transform will be applied but visual results are unverified."
            )

        # ── 5. Template-specific invariants ───────────────────────────────────
        if config.template_id == "PLAIN_ISLAND" and config.sink.shape != SinkShape.NONE:
            warnings.append(
                "PLAIN_ISLAND template does not render sinks. "
                "SinkConfig is ignored for this template."
            )

        return ConfigValidationResult(
            valid=not errors,
            errors=errors,
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # fill_defaults
    # ------------------------------------------------------------------

    def fill_defaults(
        self,
        template_id: str,
        project_id: uuid.UUID,
        tenant_id: uuid.UUID,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> TemplateConfig:
        """
        Build a TemplateConfig from template defaults, then apply caller overrides.

        The merge strategy is shallow at the top level and deep for splash/sink:
          - Scalar fields (width, depth, thickness, mirror, edge_finish): overrides win.
          - splash:  if override provides a dict, it is merged with template defaults.
          - sink:    same merge strategy as splash.
          - extra_params: caller dict merged with template defaults.

        Raises TemplateNotFoundError if template_id is not registered.

        Example::

            config = svc.fill_defaults(
                "SINGLE_VANITY", project_id, tenant_id,
                overrides={"width": 55, "mirror": True},
            )
            # width=55, mirror=True; all other fields from SINGLE_VANITY defaults
        """
        template = self._registry.get(template_id)
        defn     = template.definition
        tdefaults = defn.defaults
        overrides = overrides or {}

        # ── Scalar top-level fields ───────────────────────────────────────────
        merged: Dict[str, Any] = {
            "template_id": template_id,
            "project_id":  project_id,
            "tenant_id":   tenant_id,
            "width":       tdefaults.get("width",     60.0),
            "depth":       tdefaults.get("depth",     22.0),
            "thickness":   tdefaults.get("thickness", 1.25),
            "mirror":      tdefaults.get("mirror",    False),
            "edge_finish": tdefaults.get("edge_finish", "polished"),
        }
        # Apply scalar overrides (non-dict overrides only at top level)
        for key in ("width", "depth", "thickness", "mirror", "edge_finish",
                    "name", "unit_id", "unit_type_id"):
            if key in overrides:
                merged[key] = overrides[key]

        # ── splash ────────────────────────────────────────────────────────────
        splash_base = dict(tdefaults.get("splash", {}))
        splash_override = overrides.get("splash", {})
        if isinstance(splash_override, SplashConfig):
            merged["splash"] = splash_override
        elif isinstance(splash_override, dict):
            splash_base.update(splash_override)
            merged["splash"] = SplashConfig(**splash_base)
        else:
            merged["splash"] = SplashConfig(**splash_base) if splash_base else SplashConfig()

        # ── sink ──────────────────────────────────────────────────────────────
        sink_base = {
            k: v for k, v in tdefaults.get("sink", {}).items()
            if k in SinkConfig.model_fields
        }
        sink_override = overrides.get("sink", {})
        if isinstance(sink_override, SinkConfig):
            merged["sink"] = sink_override
        elif isinstance(sink_override, dict):
            sink_base.update(sink_override)
            merged["sink"] = SinkConfig(**sink_base)
        else:
            merged["sink"] = SinkConfig(**sink_base) if sink_base else SinkConfig()

        # ── extra_params ──────────────────────────────────────────────────────
        extra_base = dict(tdefaults.get("extra_params", {}))
        extra_override = overrides.get("extra_params", {})
        if isinstance(extra_override, dict):
            extra_base.update(extra_override)
        merged["extra_params"] = extra_base

        return TemplateConfig(**merged)

    # ------------------------------------------------------------------
    # build_safe
    # ------------------------------------------------------------------

    def build_safe(self, config: TemplateConfig) -> Assembly:
        """
        Validate config then build an Assembly.

        Raises:
            ValueError — if validation produces any hard errors.

        Does NOT raise on warnings; callers should check ConfigValidationResult
        separately if they need to surface warnings to the user.
        """
        result = self.validate(config)
        if not result.valid:
            bullet = "\n  • ".join(result.errors)
            raise ValueError(
                f"TemplateConfig validation failed for '{config.template_id}':\n"
                f"  • {bullet}"
            )
        return self._registry.build(config)
