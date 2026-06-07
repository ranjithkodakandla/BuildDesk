"""
Phase 3 — Configuration Schema Tests
======================================
Covers:
  1. SinkConfig model validators (oval axes, corner radius)
  2. TemplateConfigRequest API schema (dimension bounds, sink clearance)
  3. SplashConfigRequest / SinkConfigRequest converters
  4. TemplateConfigRequest.to_template_config()
  5. TemplateConfigResponse.from_template_config()
  6. TemplateDefinitionResponse.from_definition()
  7. ConfigurationService.validate()
  8. ConfigurationService.fill_defaults()
  9. ConfigurationService.build_safe()
 10. Example configs: SingleVanity, OffsetVanity, KitchenStraight
"""
from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from app.api.template_schemas import (
    SinkConfigRequest,
    SplashConfigRequest,
    TemplateConfigRequest,
    TemplateConfigResponse,
    TemplateConfigValidationResponse,
    TemplateDefinitionResponse,
)
from app.models.fabrication import AssemblyType, EdgeType, PartType
from app.templates import registry, SinkAlignment, SinkConfig, SinkShape, SplashConfig, TemplateConfig
from app.templates.config_service import ConfigurationService, ConfigValidationResult
from app.templates.registry import TemplateNotFoundError

_PROJECT_ID = uuid.uuid4()
_TENANT_ID  = uuid.uuid4()

svc = ConfigurationService(registry)


# ===========================================================================
# 1. SinkConfig model validators (base.py)
# ===========================================================================

class TestSinkConfigValidators:

    def test_oval_valid(self):
        sc = SinkConfig(shape=SinkShape.OVAL, major_axis=16, minor_axis=12)
        assert sc.major_axis == 16

    def test_oval_equal_axes_valid(self):
        sc = SinkConfig(shape=SinkShape.OVAL, major_axis=14, minor_axis=14)
        assert sc.major_axis == 14

    def test_oval_major_less_than_minor_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            SinkConfig(shape=SinkShape.OVAL, major_axis=10, minor_axis=14)
        assert "major_axis" in str(exc_info.value)

    def test_rectangle_valid_corner_radius(self):
        sc = SinkConfig(shape=SinkShape.RECTANGLE, width=16, depth=12, corner_radius=4.0)
        assert sc.corner_radius == 4.0

    def test_rectangle_corner_radius_too_large_raises(self):
        # min(16, 12)/2 = 6.0; radius=7 > 6
        with pytest.raises(ValidationError) as exc_info:
            SinkConfig(shape=SinkShape.RECTANGLE, width=16, depth=12, corner_radius=7.0)
        assert "corner_radius" in str(exc_info.value)

    def test_none_shape_no_axis_check(self):
        # NONE shape should not run oval or rectangle checks
        sc = SinkConfig(shape=SinkShape.NONE, major_axis=5, minor_axis=10)
        assert sc.shape == SinkShape.NONE

    def test_rectangle_zero_corner_radius_valid(self):
        sc = SinkConfig(shape=SinkShape.RECTANGLE, width=20, depth=15, corner_radius=0.0)
        assert sc.corner_radius == 0.0


# ===========================================================================
# 2. TemplateConfigRequest — dimension bounds
# ===========================================================================

class TestTemplateConfigRequestBounds:

    def _base_req(self, **overrides):
        defaults = dict(template_id="SINGLE_VANITY", width=62, depth=22)
        defaults.update(overrides)
        return defaults

    def test_valid_request(self):
        req = TemplateConfigRequest(**self._base_req())
        assert req.width == 62

    def test_width_too_large_raises(self):
        with pytest.raises(ValidationError):
            TemplateConfigRequest(**self._base_req(width=400))

    def test_depth_too_large_raises(self):
        with pytest.raises(ValidationError):
            TemplateConfigRequest(**self._base_req(depth=200))

    def test_width_zero_raises(self):
        with pytest.raises(ValidationError):
            TemplateConfigRequest(**self._base_req(width=0))

    def test_negative_thickness_raises(self):
        with pytest.raises(ValidationError):
            TemplateConfigRequest(**self._base_req(thickness=-1))

    def test_thickness_too_large_raises(self):
        with pytest.raises(ValidationError):
            TemplateConfigRequest(**self._base_req(thickness=10))

    def test_min_width_boundary(self):
        # gt=3.0 means strictly greater than 3
        with pytest.raises(ValidationError):
            TemplateConfigRequest(**self._base_req(width=3.0))
        req = TemplateConfigRequest(**self._base_req(width=3.01))
        assert req.width == pytest.approx(3.01)

    def test_max_width_boundary(self):
        req = TemplateConfigRequest(**self._base_req(width=360.0))
        assert req.width == 360.0


# ===========================================================================
# 3. TemplateConfigRequest — sink clearance validation
# ===========================================================================

class TestSinkClearanceValidation:

    def _req(self, **overrides):
        base = dict(template_id="SINGLE_VANITY", width=62, depth=22)
        base.update(overrides)
        return base

    def test_rectangle_sink_fits(self):
        req = TemplateConfigRequest(
            **self._req(
                sink=SinkConfigRequest(shape=SinkShape.RECTANGLE,
                                       width=30, depth=16)
            )
        )
        assert req.sink.width == 30

    def test_rectangle_sink_too_wide_raises(self):
        # width=62, clearance=3 each side → max_sink_w = 56
        with pytest.raises(ValidationError) as exc_info:
            TemplateConfigRequest(
                **self._req(
                    sink=SinkConfigRequest(shape=SinkShape.RECTANGLE,
                                           width=57, depth=16)
                )
            )
        assert "clearance" in str(exc_info.value).lower() or "sink width" in str(exc_info.value).lower()

    def test_rectangle_sink_too_deep_raises(self):
        # depth=22, clearance=3 each side → max_sink_d = 16
        with pytest.raises(ValidationError) as exc_info:
            TemplateConfigRequest(
                **self._req(
                    sink=SinkConfigRequest(shape=SinkShape.RECTANGLE,
                                           width=20, depth=17)
                )
            )
        assert "sink" in str(exc_info.value).lower()

    def test_oval_sink_fits(self):
        req = TemplateConfigRequest(
            **self._req(
                sink=SinkConfigRequest(shape=SinkShape.OVAL,
                                       major_axis=16, minor_axis=12)
            )
        )
        assert req.sink.major_axis == 16

    def test_oval_major_too_large_raises(self):
        # width=62, max_major = 62 - 6 = 56
        with pytest.raises(ValidationError):
            TemplateConfigRequest(
                **self._req(
                    sink=SinkConfigRequest(shape=SinkShape.OVAL,
                                           major_axis=57, minor_axis=12)
                )
            )

    def test_oval_minor_too_large_raises(self):
        # depth=22, max_minor = 22 - 6 = 16
        with pytest.raises(ValidationError):
            TemplateConfigRequest(
                **self._req(
                    sink=SinkConfigRequest(shape=SinkShape.OVAL,
                                           major_axis=16, minor_axis=17)
                )
            )

    def test_no_sink_skips_clearance_check(self):
        req = TemplateConfigRequest(
            **self._req(sink=SinkConfigRequest(shape=SinkShape.NONE))
        )
        assert req.sink.shape == SinkShape.NONE

    def test_narrow_top_rectangle_clearance(self):
        # width=12, max_sink_w = 12 - 6 = 6; sink.width=8 should fail
        with pytest.raises(ValidationError):
            TemplateConfigRequest(
                template_id="SINGLE_VANITY",
                width=12, depth=10,
                sink=SinkConfigRequest(shape=SinkShape.RECTANGLE,
                                       width=8, depth=4)
            )


# ===========================================================================
# 4. UUID validation on unit_id / unit_type_id
# ===========================================================================

class TestUUIDFields:

    def test_valid_uuid_string(self):
        uid = str(uuid.uuid4())
        req = TemplateConfigRequest(
            template_id="SINGLE_VANITY", width=62, depth=22, unit_id=uid,
        )
        assert req.unit_id == uid

    def test_invalid_uuid_string_raises(self):
        with pytest.raises(ValidationError):
            TemplateConfigRequest(
                template_id="SINGLE_VANITY", width=62, depth=22,
                unit_id="not-a-uuid",
            )

    def test_none_uuid_is_allowed(self):
        req = TemplateConfigRequest(
            template_id="SINGLE_VANITY", width=62, depth=22,
            unit_id=None,
        )
        assert req.unit_id is None


# ===========================================================================
# 5. SplashConfigRequest converter
# ===========================================================================

class TestSplashConfigRequestConverter:

    def test_to_splash_config_defaults(self):
        req = SplashConfigRequest()
        sc  = req.to_splash_config()
        assert sc.back   is True
        assert sc.left   is True
        assert sc.right  is True
        assert sc.height == pytest.approx(4.0)

    def test_to_splash_config_custom(self):
        req = SplashConfigRequest(back=True, left=False, right=False, height=6.0)
        sc  = req.to_splash_config()
        assert sc.left   is False
        assert sc.height == pytest.approx(6.0)


# ===========================================================================
# 6. SinkConfigRequest converter
# ===========================================================================

class TestSinkConfigRequestConverter:

    def test_to_sink_config_oval(self):
        req = SinkConfigRequest(
            shape=SinkShape.OVAL,
            alignment=SinkAlignment.CENTER,
            major_axis=16, minor_axis=12,
        )
        sc = req.to_sink_config()
        assert sc.shape      == SinkShape.OVAL
        assert sc.major_axis == 16
        assert sc.minor_axis == 12

    def test_to_sink_config_rectangle(self):
        req = SinkConfigRequest(
            shape=SinkShape.RECTANGLE,
            width=33, depth=18, corner_radius=1.0,
        )
        sc = req.to_sink_config()
        assert sc.shape         == SinkShape.RECTANGLE
        assert sc.corner_radius == 1.0


# ===========================================================================
# 7. TemplateConfigRequest.to_template_config()
# ===========================================================================

class TestToTemplateConfig:

    def test_converts_scalar_fields(self):
        req = TemplateConfigRequest(
            template_id="SINGLE_VANITY",
            name="Master Bath",
            width=62, depth=22, thickness=1.25,
            mirror=False,
            edge_finish=EdgeType.POLISHED,
        )
        cfg = req.to_template_config(_PROJECT_ID, _TENANT_ID)

        assert cfg.template_id  == "SINGLE_VANITY"
        assert cfg.name         == "Master Bath"
        assert cfg.width        == 62
        assert cfg.depth        == 22
        assert cfg.thickness    == 1.25
        assert cfg.mirror       is False
        assert cfg.edge_finish  == EdgeType.POLISHED
        assert cfg.project_id   == _PROJECT_ID
        assert cfg.tenant_id    == _TENANT_ID

    def test_converts_sub_schemas(self):
        req = TemplateConfigRequest(
            template_id="SINGLE_VANITY",
            width=62, depth=22,
            splash=SplashConfigRequest(back=True, left=False, right=False, height=5.0),
            sink=SinkConfigRequest(shape=SinkShape.OVAL, major_axis=16, minor_axis=12),
        )
        cfg = req.to_template_config(_PROJECT_ID, _TENANT_ID)
        assert isinstance(cfg.splash, SplashConfig)
        assert cfg.splash.left   is False
        assert cfg.splash.height == pytest.approx(5.0)
        assert isinstance(cfg.sink, SinkConfig)
        assert cfg.sink.shape    == SinkShape.OVAL

    def test_converts_unit_id(self):
        uid = str(uuid.uuid4())
        req = TemplateConfigRequest(
            template_id="SINGLE_VANITY",
            width=62, depth=22,
            unit_id=uid,
        )
        cfg = req.to_template_config(_PROJECT_ID, _TENANT_ID)
        assert cfg.unit_id == uuid.UUID(uid)

    def test_none_unit_id_stays_none(self):
        req = TemplateConfigRequest(
            template_id="SINGLE_VANITY", width=62, depth=22,
        )
        cfg = req.to_template_config(_PROJECT_ID, _TENANT_ID)
        assert cfg.unit_id is None


# ===========================================================================
# 8. TemplateConfigResponse
# ===========================================================================

class TestTemplateConfigResponse:

    def test_round_trip(self):
        cfg = TemplateConfig(
            template_id="SINGLE_VANITY",
            project_id=_PROJECT_ID,
            tenant_id=_TENANT_ID,
            name="Bath A",
            width=62, depth=22,
            splash=SplashConfig(back=True, left=True, right=True, height=4),
            sink=SinkConfig(shape=SinkShape.OVAL, major_axis=16, minor_axis=12),
        )
        resp = TemplateConfigResponse.from_template_config(cfg)
        assert resp.template_id    == "SINGLE_VANITY"
        assert resp.name           == "Bath A"
        assert resp.width          == 62
        assert resp.splash.back    is True
        assert resp.sink.shape     == SinkShape.OVAL
        assert resp.sink.major_axis == 16


# ===========================================================================
# 9. TemplateDefinitionResponse
# ===========================================================================

class TestTemplateDefinitionResponse:

    def test_from_definition_vanity(self):
        defn = registry.get("SINGLE_VANITY").definition
        resp = TemplateDefinitionResponse.from_definition(defn)
        assert resp.id           == "SINGLE_VANITY"
        assert resp.category.value == "vanity"
        assert "mirror" in resp.supported_features
        assert "width"  in resp.editable_fields

    def test_all_templates_have_response(self):
        for defn in registry.all_definitions():
            resp = TemplateDefinitionResponse.from_definition(defn)
            assert resp.id == defn.id


# ===========================================================================
# 10. ConfigurationService.validate()
# ===========================================================================

class TestConfigurationServiceValidate:

    def _config(self, template_id="SINGLE_VANITY", **overrides):
        base = dict(
            template_id=template_id,
            project_id=_PROJECT_ID,
            tenant_id=_TENANT_ID,
            width=62, depth=22,
        )
        base.update(overrides)
        return TemplateConfig(**base)

    def test_valid_single_vanity(self):
        result = svc.validate(self._config())
        assert result.valid is True
        assert result.errors == []

    def test_unknown_template_is_invalid(self):
        result = svc.validate(self._config(template_id="DOES_NOT_EXIST"))
        assert result.valid is False
        assert any("Unknown" in e for e in result.errors)

    def test_oval_on_supported_template(self):
        cfg = self._config(
            sink=SinkConfig(shape=SinkShape.OVAL, major_axis=16, minor_axis=12)
        )
        result = svc.validate(cfg)
        assert result.valid is True

    def test_oval_on_plain_island_warning(self):
        cfg = self._config(
            template_id="PLAIN_ISLAND",
            width=84, depth=42,
            sink=SinkConfig(shape=SinkShape.OVAL, major_axis=16, minor_axis=12),
        )
        result = svc.validate(cfg)
        # PLAIN_ISLAND doesn't support sinks → warning (not error, because the
        # template simply ignores it)
        assert result.has_warnings
        assert any("PLAIN_ISLAND" in w for w in result.warnings)

    def test_mirror_on_island_produces_warning(self):
        cfg = self._config(
            template_id="PLAIN_ISLAND",
            width=84, depth=42,
            mirror=True,
        )
        result = svc.validate(cfg)
        # PLAIN_ISLAND doesn't declare mirror support → warning
        assert result.has_warnings

    def test_valid_kitchen_straight(self):
        cfg = TemplateConfig(
            template_id="KITCHEN_STRAIGHT",
            project_id=_PROJECT_ID, tenant_id=_TENANT_ID,
            width=120, depth=25,
            splash=SplashConfig(back=True, left=False, right=False),
            sink=SinkConfig(shape=SinkShape.RECTANGLE, width=33, depth=18, corner_radius=1.0),
        )
        result = svc.validate(cfg)
        assert result.valid is True

    def test_validation_result_repr(self):
        result = ConfigValidationResult(valid=True)
        assert "VALID" in repr(result)


# ===========================================================================
# 11. ConfigurationService.fill_defaults()
# ===========================================================================

class TestFillDefaults:

    def test_single_vanity_defaults(self):
        cfg = svc.fill_defaults("SINGLE_VANITY", _PROJECT_ID, _TENANT_ID)
        assert cfg.template_id  == "SINGLE_VANITY"
        assert cfg.width        == 62
        assert cfg.depth        == 22
        assert cfg.splash.back  is True
        assert cfg.splash.left  is True
        assert cfg.sink.shape   == SinkShape.OVAL

    def test_compact_vanity_defaults(self):
        cfg = svc.fill_defaults("COMPACT_VANITY", _PROJECT_ID, _TENANT_ID)
        assert cfg.width       == 36
        assert cfg.splash.left is False   # compact has no side splashes by default

    def test_overrides_win(self):
        cfg = svc.fill_defaults(
            "SINGLE_VANITY", _PROJECT_ID, _TENANT_ID,
            overrides={"width": 55, "mirror": True},
        )
        assert cfg.width  == 55
        assert cfg.mirror is True
        assert cfg.depth  == 22   # unchanged from default

    def test_splash_override_merged(self):
        cfg = svc.fill_defaults(
            "SINGLE_VANITY", _PROJECT_ID, _TENANT_ID,
            overrides={"splash": {"left": False, "right": False}},
        )
        assert cfg.splash.back  is True   # template default preserved
        assert cfg.splash.left  is False  # override applied
        assert cfg.splash.right is False  # override applied

    def test_sink_override_merged(self):
        cfg = svc.fill_defaults(
            "SINGLE_VANITY", _PROJECT_ID, _TENANT_ID,
            overrides={"sink": SinkConfig(shape=SinkShape.RECTANGLE,
                                           width=22, depth=16)},
        )
        assert cfg.sink.shape == SinkShape.RECTANGLE
        assert cfg.sink.width == 22

    def test_unknown_template_raises(self):
        with pytest.raises(TemplateNotFoundError):
            svc.fill_defaults("NONEXISTENT", _PROJECT_ID, _TENANT_ID)

    def test_project_and_tenant_set(self):
        cfg = svc.fill_defaults("SINGLE_VANITY", _PROJECT_ID, _TENANT_ID)
        assert cfg.project_id == _PROJECT_ID
        assert cfg.tenant_id  == _TENANT_ID


# ===========================================================================
# 12. ConfigurationService.build_safe()
# ===========================================================================

class TestBuildSafe:

    def _config(self, template_id="SINGLE_VANITY", **overrides):
        return svc.fill_defaults(template_id, _PROJECT_ID, _TENANT_ID,
                                 overrides=overrides)

    def test_build_safe_returns_assembly(self):
        asm = svc.build_safe(self._config())
        assert asm.assembly_type == AssemblyType.VANITY
        assert len(asm.parts) >= 1

    def test_build_safe_invalid_raises_value_error(self):
        bad_cfg = TemplateConfig(
            template_id="DOES_NOT_EXIST",
            project_id=_PROJECT_ID, tenant_id=_TENANT_ID,
            width=62, depth=22,
        )
        with pytest.raises(ValueError) as exc_info:
            svc.build_safe(bad_cfg)
        assert "validation failed" in str(exc_info.value).lower()

    def test_build_safe_all_templates(self):
        for tid in registry.ids():
            cfg = svc.fill_defaults(tid, _PROJECT_ID, _TENANT_ID)
            asm = svc.build_safe(cfg)
            assert len(asm.parts) >= 1


# ===========================================================================
# 13. Example configs — SingleVanity / OffsetVanity / KitchenStraight
# ===========================================================================

class TestExampleConfigs:

    def test_single_vanity_full_config(self):
        """Full SingleVanity configuration as a fabricator would submit it."""
        req = TemplateConfigRequest(
            template_id="SINGLE_VANITY",
            name="Master Bath",
            width=62,
            depth=22,
            thickness=1.25,
            mirror=False,
            splash=SplashConfigRequest(back=True, left=True, right=True, height=4.0),
            sink=SinkConfigRequest(
                shape=SinkShape.OVAL,
                alignment=SinkAlignment.CENTER,
                major_axis=16.0,
                minor_axis=12.0,
            ),
            edge_finish=EdgeType.POLISHED,
        )
        cfg = req.to_template_config(_PROJECT_ID, _TENANT_ID)
        result = svc.validate(cfg)
        asm = svc.build_safe(cfg)

        assert result.valid         is True
        assert asm.assembly_type    == AssemblyType.VANITY
        assert len(asm.parts)       == 4   # main top + 3 splashes
        top = next(p for p in asm.parts if p.part_type == PartType.MAIN_TOP)
        assert top.dimensions.length == pytest.approx(62)

    def test_offset_vanity_full_config(self):
        """OffsetVanity with left-aligned sink — mirror=True to flip to right."""
        req = TemplateConfigRequest(
            template_id="OFFSET_VANITY",
            name="Guest Bath",
            width=62,
            depth=22,
            mirror=True,
            splash=SplashConfigRequest(back=True, left=True, right=True, height=4.0),
            sink=SinkConfigRequest(
                shape=SinkShape.OVAL,
                alignment=SinkAlignment.LEFT,
                major_axis=16.0,
                minor_axis=12.0,
                offset=12.0,
            ),
            edge_finish=EdgeType.POLISHED,
        )
        cfg = req.to_template_config(_PROJECT_ID, _TENANT_ID)
        result = svc.validate(cfg)
        asm = svc.build_safe(cfg)

        assert result.valid      is True
        top = next(p for p in asm.parts if p.part_type == PartType.MAIN_TOP)
        cutout = top.cutouts[0]
        # mirror flips LEFT → RIGHT: center_x = 62 - 12 = 50
        assert cutout.center_x == pytest.approx(50.0)

    def test_kitchen_straight_full_config(self):
        """KitchenStraight with back splash and rectangle sink."""
        req = TemplateConfigRequest(
            template_id="KITCHEN_STRAIGHT",
            name="Kitchen Run A",
            width=120,
            depth=25,
            thickness=1.25,
            mirror=False,
            splash=SplashConfigRequest(back=True, left=False, right=False, height=4.0),
            sink=SinkConfigRequest(
                shape=SinkShape.RECTANGLE,
                alignment=SinkAlignment.CENTER,
                width=33.0,
                depth=16.0,     # 16 < 25 - 6 = 19 ✓ fits
                corner_radius=1.0,
            ),
            edge_finish=EdgeType.POLISHED,
        )
        cfg = req.to_template_config(_PROJECT_ID, _TENANT_ID)
        result = svc.validate(cfg)
        asm = svc.build_safe(cfg)

        assert result.valid         is True
        assert asm.assembly_type    == AssemblyType.KITCHEN
        splashes = [p for p in asm.parts if p.part_type == PartType.LOOSE_PIECE]
        assert len(splashes)        == 1   # back splash only
        top = next(p for p in asm.parts if p.part_type == PartType.MAIN_TOP)
        assert top.dimensions.length == pytest.approx(120)
        assert len(top.cutouts)      == 1
        assert top.cutouts[0].center_x == pytest.approx(60.0)   # centered
