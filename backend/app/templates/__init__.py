"""
app.templates — Template-Driven Fabrication Registry
======================================================
Provides a one-step path from user configuration to a fabrication Assembly.

Quick start::

    from app.templates import registry, TemplateConfig, SplashConfig, SinkConfig, SinkShape

    config = TemplateConfig(
        template_id="SINGLE_VANITY",
        project_id=...,
        tenant_id=...,
        width=62,
        depth=22,
        splash=SplashConfig(back=True, left=True, right=True, height=4),
        sink=SinkConfig(shape=SinkShape.OVAL, alignment="center"),
    )
    assembly = registry.build(config)   # → app.models.fabrication.Assembly

Available templates (see registry.all_definitions() for full metadata):
    KITCHEN_STRAIGHT       — Straight kitchen run
    KITCHEN_STRAIGHT_REF   — Straight kitchen with refrigerator zone
    PLAIN_ISLAND           — Freestanding island, all edges exposed
    SINGLE_VANITY          — Standard single-sink vanity
    OFFSET_VANITY          — Single-sink vanity with offset sink
    DOUBLE_VANITY          — Wide vanity with two sinks
    COMPACT_VANITY         — Narrow vanity preset (36")
"""
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
from app.templates.registry import TemplateNotFoundError, TemplateRegistry, registry

__all__ = [
    # Base types
    "BaseTemplate",
    "SinkAlignment",
    "SinkConfig",
    "SinkShape",
    "SplashConfig",
    "TemplateCategory",
    "TemplateConfig",
    "TemplateDefinition",
    # Registry
    "TemplateNotFoundError",
    "TemplateRegistry",
    "registry",
]
