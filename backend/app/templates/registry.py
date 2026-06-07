"""
Template Registry
=================
Central lookup table for all registered fabrication templates.

Usage::

    from app.templates import registry, TemplateConfig

    config = TemplateConfig(
        template_id="SINGLE_VANITY",
        project_id=...,
        tenant_id=...,
        width=62,
        depth=22,
    )
    assembly = registry.build(config)           # → Assembly
    defs     = registry.all_definitions()       # → List[TemplateDefinition]

Adding a new template:
    1. Create backend/app/templates/<name>.py implementing BaseTemplate.
    2. Import the class in _build_registry() below.
    3. Call reg.register(<YourTemplate>()).
    No other files need to change.
"""
from __future__ import annotations

from typing import Dict, List

from app.models.fabrication import Assembly
from app.templates.base import BaseTemplate, TemplateConfig, TemplateDefinition


class TemplateNotFoundError(KeyError):
    """Raised when a template_id is not registered."""


class TemplateRegistry:
    """
    Central registry for fabrication templates.

    Templates self-register via register().  The module-level `registry`
    singleton is pre-populated with all built-in templates at import time.
    """

    def __init__(self) -> None:
        self._templates: Dict[str, BaseTemplate] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, template: BaseTemplate) -> None:
        """Register a template using its definition.id as the lookup key."""
        self._templates[template.definition.id] = template

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(self, template_id: str) -> BaseTemplate:
        """Return the template for template_id, or raise TemplateNotFoundError."""
        try:
            return self._templates[template_id]
        except KeyError:
            available = ", ".join(sorted(self._templates.keys()))
            raise TemplateNotFoundError(
                f"Template '{template_id}' not found. "
                f"Available templates: {available}"
            ) from None

    def build(self, config: TemplateConfig) -> Assembly:
        """Look up the template by config.template_id and build an Assembly."""
        return self.get(config.template_id).build(config)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def all_definitions(self) -> List[TemplateDefinition]:
        """All template definitions, ordered by category then id."""
        return sorted(
            (t.definition for t in self._templates.values()),
            key=lambda d: (d.category, d.id),
        )

    def ids(self) -> List[str]:
        """Sorted list of registered template IDs."""
        return sorted(self._templates.keys())

    def __len__(self) -> int:
        return len(self._templates)

    def __contains__(self, template_id: str) -> bool:
        return template_id in self._templates


# ---------------------------------------------------------------------------
# Module-level singleton — pre-populated with all built-in templates
# ---------------------------------------------------------------------------

def _build_registry() -> TemplateRegistry:
    """Construct and return the global registry with all built-in templates."""
    # Local imports prevent circular imports at module load time
    from app.templates.compact_vanity import CompactVanityTemplate
    from app.templates.double_vanity import DoubleVanityTemplate
    from app.templates.kitchen_l import KitchenLTemplate
    from app.templates.kitchen_straight import KitchenStraightTemplate
    from app.templates.kitchen_straight_ref import KitchenStraightRefTemplate
    from app.templates.offset_vanity import OffsetVanityTemplate
    from app.templates.plain_island import PlainIslandTemplate
    from app.templates.single_vanity import SingleVanityTemplate

    reg = TemplateRegistry()
    reg.register(KitchenStraightTemplate())
    reg.register(KitchenStraightRefTemplate())
    reg.register(KitchenLTemplate())
    reg.register(PlainIslandTemplate())
    reg.register(SingleVanityTemplate())
    reg.register(OffsetVanityTemplate())
    reg.register(DoubleVanityTemplate())
    reg.register(CompactVanityTemplate())
    return reg


registry: TemplateRegistry = _build_registry()
