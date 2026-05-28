"""
Template Resolver
=================
Runtime parameter validation and resolution layer for ShapeTemplates.

Responsibility:
    Given a ShapeTemplate and a raw dimension payload (Dict[str, Any]),
    validate every parameter against its declared rules and return a
    clean, normalised ResolvedDimensions structure ready for GeometryModel
    creation.

This module is intentionally free of:
    - database I/O
    - HTTP / FastAPI concerns
    - geometry computation (no area / perimeter here)
    - PDF or output generation

Validation rules applied (per ShapeParameter):
    required        → error if missing and no default_value
    default         → substitute default_value when parameter is absent
    type coercion   → cast incoming value to the declared parameter_type
    min / max       → enforce bounds on number-type parameters
    allowed_options → reject values not in the list for select-type parameters

Usage::

    resolver = TemplateResolver()
    result = resolver.resolve(template, payload)

    if result.has_errors:
        print(result.errors)
    else:
        geometry = GeometryModel(
            project_id=...,
            tenant_id=...,
            template_id=template.template_id,
            dimensions=result.dimensions,
        )
"""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field

from app.models.shape_template import ShapeParameter, ShapeParameterType, ShapeTemplate


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

class ParameterError(BaseModel):
    """A single validation failure for one parameter."""

    parameter: str = Field(..., description="The ShapeParameter.name that failed")
    message: str = Field(..., description="Human-readable reason for the failure")


class ResolvedDimensions(BaseModel):
    """
    Output of a successful (or partially failed) resolution pass.

    On success:
        has_errors = False
        dimensions = validated, normalised parameter dict
        errors     = []

    On failure:
        has_errors = True
        dimensions = {} (empty; caller must not use it)
        errors     = list of ParameterError
    """

    has_errors: bool = Field(default=False)
    dimensions: Dict[str, Any] = Field(
        default_factory=dict,
        description="Validated parameter map; only populated when has_errors=False",
    )
    errors: List[ParameterError] = Field(
        default_factory=list,
        description="Validation errors; non-empty only when has_errors=True",
    )


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------

class TemplateResolver:
    """
    Stateless service that validates and normalises a raw dimension payload
    against a ShapeTemplate's declared parameters.

    Instantiate once and reuse; it holds no mutable state.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve(
        self,
        template: ShapeTemplate,
        payload: Dict[str, Any],
    ) -> ResolvedDimensions:
        """
        Validate *payload* against *template* and return a ResolvedDimensions.

        Args:
            template: The ShapeTemplate that defines the expected parameters.
            payload:  Raw key-value map from the caller (e.g. API request body).

        Returns:
            ResolvedDimensions with either a clean dimensions dict or a list
            of ParameterError objects describing every validation failure.
        """
        errors: List[ParameterError] = []
        resolved: Dict[str, Any] = {}

        for param in template.parameters:
            value, param_errors = self._resolve_parameter(param, payload)
            errors.extend(param_errors)
            if param_errors:
                continue
            if value is not None:
                resolved[param.name] = value

        if errors:
            return ResolvedDimensions(has_errors=True, errors=errors)

        return ResolvedDimensions(has_errors=False, dimensions=resolved)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_parameter(
        self,
        param: ShapeParameter,
        payload: Dict[str, Any],
    ) -> tuple[Any, List[ParameterError]]:
        """
        Resolve a single parameter from *payload* against *param*.

        Returns:
            (resolved_value, errors)
            resolved_value is None when errors exist.
        """
        errors: List[ParameterError] = []
        raw = payload.get(param.name)

        # ── 1. Missing value handling ───────────────────────────────────
        if raw is None:
            if param.default_value is not None:
                raw = param.default_value
            elif param.required:
                errors.append(ParameterError(
                    parameter=param.name,
                    message=f"'{param.name}' is required but was not provided.",
                ))
                return None, errors
            else:
                # Optional and absent — skip entirely
                return None, []

        # ── 2. Type coercion ────────────────────────────────────────────
        coerced, coerce_error = self._coerce(param, raw)
        if coerce_error:
            errors.append(coerce_error)
            return None, errors
        raw = coerced

        # ── 3. Type-specific validation ─────────────────────────────────
        if param.parameter_type == ShapeParameterType.number:
            errors.extend(self._validate_number(param, raw))

        elif param.parameter_type == ShapeParameterType.select:
            errors.extend(self._validate_select(param, raw))

        # string and boolean have no additional range constraints

        if errors:
            return None, errors

        return raw, []

    # ------------------------------------------------------------------
    # Coercion
    # ------------------------------------------------------------------

    def _coerce(
        self,
        param: ShapeParameter,
        raw: Any,
    ) -> tuple[Any, ParameterError | None]:
        """Attempt to cast *raw* to the declared parameter_type."""

        try:
            if param.parameter_type == ShapeParameterType.number:
                return float(raw), None

            if param.parameter_type == ShapeParameterType.boolean:
                if isinstance(raw, bool):
                    return raw, None
                if isinstance(raw, str):
                    if raw.lower() in ("true", "1", "yes"):
                        return True, None
                    if raw.lower() in ("false", "0", "no"):
                        return False, None
                if isinstance(raw, int):
                    return bool(raw), None
                raise ValueError(f"Cannot coerce {raw!r} to boolean")

            if param.parameter_type in (
                ShapeParameterType.string,
                ShapeParameterType.select,
            ):
                return str(raw), None

        except (ValueError, TypeError) as exc:
            return None, ParameterError(
                parameter=param.name,
                message=(
                    f"'{param.name}' expected type '{param.parameter_type.value}' "
                    f"but received {raw!r} which could not be converted: {exc}"
                ),
            )

        return raw, None

    # ------------------------------------------------------------------
    # Type-specific validators
    # ------------------------------------------------------------------

    def _validate_number(
        self,
        param: ShapeParameter,
        value: float,
    ) -> List[ParameterError]:
        errors: List[ParameterError] = []

        if param.min_value is not None and value < param.min_value:
            errors.append(ParameterError(
                parameter=param.name,
                message=(
                    f"'{param.name}' value {value} is below the minimum "
                    f"allowed value of {param.min_value}."
                ),
            ))

        if param.max_value is not None and value > param.max_value:
            errors.append(ParameterError(
                parameter=param.name,
                message=(
                    f"'{param.name}' value {value} exceeds the maximum "
                    f"allowed value of {param.max_value}."
                ),
            ))

        return errors

    def _validate_select(
        self,
        param: ShapeParameter,
        value: str,
    ) -> List[ParameterError]:
        if not param.allowed_options:
            # No options declared — pass-through (misconfigured template, not user error)
            return []

        if value not in param.allowed_options:
            options_str = ", ".join(f"'{o}'" for o in param.allowed_options)
            return [ParameterError(
                parameter=param.name,
                message=(
                    f"'{param.name}' received invalid option '{value}'. "
                    f"Allowed values: {options_str}."
                ),
            )]

        return []
