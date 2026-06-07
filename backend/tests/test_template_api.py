"""
Phase 4 — Template Generation API Tests
=========================================
Tests the full HTTP pipeline for all template endpoints:

    GET  /api/v1/templates
    GET  /api/v1/templates/{template_id}
    POST /api/v1/templates/generate
    POST /api/v1/templates/preview
    POST /api/v1/templates/pdf

All endpoints are stateless in Phase 4 (no DB writes).
Auth is overridden via FastAPI dependency injection.

Coverage:
  1.  List templates — all 7 returned
  2.  List templates — category filter
  3.  Get template detail — valid id
  4.  Get template detail — unknown id → 404
  5.  Generate — valid SingleVanity → 200 Assembly JSON
  6.  Generate — all 7 templates → 200
  7.  Generate — unknown template → 422
  8.  Generate — invalid config (oval on PLAIN_ISLAND) → 200 + warning
  9.  Preview — returns image/svg+xml
  10. Preview — SVG contains expected elements
  11. PDF — returns application/pdf
  12. PDF — response is non-empty bytes
  13. Sink preset mapping (small/standard/large in response)
  14. Splash toggle behavior (back-only kitchen)
  15. Mirror flag propagated to assembly variant
  16. UI contract included in template list
  17. UI contract field visibility
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_tenant, require_active_user
from app.main import create_app
from app.models.user import User
from app.templates import registry

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_TENANT_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_USER = User(
    tenant_id=_TENANT_ID,
    email="test@buildesk.app",
    hashed_password="x",
    role="admin",
)


@pytest.fixture(scope="module")
def client() -> TestClient:
    """
    Shared TestClient with auth dependencies overridden.
    No DB required — all template endpoints are stateless in Phase 4.
    """
    app = create_app()
    app.dependency_overrides[get_current_tenant] = lambda: _TENANT_ID
    app.dependency_overrides[require_active_user] = lambda: _USER
    return TestClient(app)


# ---------------------------------------------------------------------------
# Shared request builders
# ---------------------------------------------------------------------------

def _single_vanity_body(**overrides) -> dict:
    base = {
        "template_id": "SINGLE_VANITY",
        "width": 62,
        "depth": 22,
        "splash": {"back": True, "left": True, "right": True, "height": 4},
        "sink": {"type": "oval", "position": "center", "size": "standard"},
        "edge_finish": "polished",
        "mirror": False,
    }
    base.update(overrides)
    return base


def _kitchen_body(**overrides) -> dict:
    base = {
        "template_id": "KITCHEN_STRAIGHT",
        "width": 120,
        "depth": 25,
        "splash": {"back": True, "left": False, "right": False, "height": 4},
        "sink": {"type": "rectangle", "position": "center", "size": "standard"},
        "edge_finish": "polished",
    }
    base.update(overrides)
    return base


# ===========================================================================
# 1–2. GET /api/v1/templates
# ===========================================================================

class TestListTemplates:

    def test_returns_all_templates(self, client: TestClient):
        r = client.get("/api/v1/templates")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 8
        ids = {item["definition"]["id"] for item in data}
        assert ids == set(registry.ids())

    def test_each_item_has_definition_and_contract(self, client: TestClient):
        r = client.get("/api/v1/templates")
        for item in r.json():
            assert "definition"  in item
            assert "ui_contract" in item
            defn = item["definition"]
            assert "id"           in defn
            assert "display_name" in defn
            assert "category"     in defn
            assert "defaults"     in defn

    def test_category_filter_vanity(self, client: TestClient):
        r = client.get("/api/v1/templates?category=vanity")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 4
        for item in data:
            assert item["definition"]["category"] == "vanity"

    def test_category_filter_kitchen(self, client: TestClient):
        r = client.get("/api/v1/templates?category=kitchen")
        data = r.json()
        assert len(data) == 3

    def test_category_filter_island(self, client: TestClient):
        r = client.get("/api/v1/templates?category=island")
        data = r.json()
        assert len(data) == 1
        assert data[0]["definition"]["id"] == "PLAIN_ISLAND"

    def test_unknown_category_returns_empty(self, client: TestClient):
        r = client.get("/api/v1/templates?category=nonexistent")
        assert r.status_code == 200
        assert r.json() == []


# ===========================================================================
# 3–4. GET /api/v1/templates/{template_id}
# ===========================================================================

class TestGetTemplate:

    def test_single_vanity_detail(self, client: TestClient):
        r = client.get("/api/v1/templates/SINGLE_VANITY")
        assert r.status_code == 200
        data = r.json()
        assert data["definition"]["id"]           == "SINGLE_VANITY"
        assert data["definition"]["display_name"] == "Single Vanity"
        assert data["definition"]["category"]     == "vanity"

    def test_definition_has_defaults(self, client: TestClient):
        r = client.get("/api/v1/templates/SINGLE_VANITY")
        defaults = r.json()["definition"]["defaults"]
        assert defaults["width"] == 62
        assert defaults["depth"] == 22

    def test_definition_has_supported_features(self, client: TestClient):
        r = client.get("/api/v1/templates/SINGLE_VANITY")
        features = r.json()["definition"]["supported_features"]
        assert "sink_oval"   in features
        assert "backsplash"  in features
        assert "mirror"      in features

    def test_ui_contract_included(self, client: TestClient):
        r = client.get("/api/v1/templates/SINGLE_VANITY")
        contract = r.json()["ui_contract"]
        assert contract["template_id"]  == "SINGLE_VANITY"
        assert contract["dimension_term"] == "Width"
        assert len(contract["fields"])  > 0

    def test_kitchen_uses_length_term(self, client: TestClient):
        r = client.get("/api/v1/templates/KITCHEN_STRAIGHT")
        assert r.json()["ui_contract"]["dimension_term"] == "Length"

    def test_plain_island_detail(self, client: TestClient):
        r = client.get("/api/v1/templates/PLAIN_ISLAND")
        assert r.status_code == 200
        assert r.json()["definition"]["category"] == "island"

    def test_unknown_template_returns_404(self, client: TestClient):
        r = client.get("/api/v1/templates/DOES_NOT_EXIST")
        assert r.status_code == 404

    def test_all_templates_individually(self, client: TestClient):
        for tid in registry.ids():
            r = client.get(f"/api/v1/templates/{tid}")
            assert r.status_code == 200, f"Template {tid} returned {r.status_code}"


# ===========================================================================
# 5–8. POST /api/v1/templates/generate
# ===========================================================================

class TestGenerateAssembly:

    def test_single_vanity_returns_200(self, client: TestClient):
        r = client.post("/api/v1/templates/generate", json=_single_vanity_body())
        assert r.status_code == 200

    def test_single_vanity_response_structure(self, client: TestClient):
        r = client.post("/api/v1/templates/generate", json=_single_vanity_body())
        data = r.json()
        assert data["template_id"]  == "SINGLE_VANITY"
        assert data["assembly_type"] == "vanity"
        assert data["part_count"]   == 4      # main top + 3 splashes
        assert data["variant"]      == "standard"
        assert isinstance(data["assembly_id"], str)
        assert isinstance(data["parts"], list)

    def test_parts_contain_expected_types(self, client: TestClient):
        r    = client.post("/api/v1/templates/generate", json=_single_vanity_body())
        parts = r.json()["parts"]
        types = [p["part_type"] for p in parts]
        assert "main_top"     in types
        assert "loose_piece"  in types   # splash pieces

    def test_main_top_dimensions(self, client: TestClient):
        r = client.post("/api/v1/templates/generate", json=_single_vanity_body())
        parts = r.json()["parts"]
        main = next(p for p in parts if p["part_type"] == "main_top")
        assert main["length"]    == pytest.approx(62)
        assert main["depth"]     == pytest.approx(22)
        assert main["cutout_count"] == 1    # oval sink

    def test_all_7_templates_generate(self, client: TestClient):
        for tid in registry.ids():
            defn = registry.get(tid).definition.defaults
            body = {
                "template_id": tid,
                "width":       defn.get("width", 60),
                "depth":       defn.get("depth", 22),
                "sink":        {"type": "none"},
                "splash":      {"back": False, "left": False, "right": False, "height": 4},
            }
            r = client.post("/api/v1/templates/generate", json=body)
            assert r.status_code == 200, f"{tid} returned {r.status_code}: {r.text}"

    def test_unknown_template_returns_422(self, client: TestClient):
        r = client.post("/api/v1/templates/generate",
                        json={"template_id": "FAKE_TEMPLATE", "width": 62, "depth": 22})
        assert r.status_code == 422

    def test_missing_required_field_returns_422(self, client: TestClient):
        # Missing width
        r = client.post("/api/v1/templates/generate",
                        json={"template_id": "SINGLE_VANITY", "depth": 22})
        assert r.status_code == 422

    def test_plain_island_with_sink_returns_200_with_warning(self, client: TestClient):
        """PLAIN_ISLAND ignores sinks — generates OK but with warning."""
        r = client.post("/api/v1/templates/generate", json={
            "template_id": "PLAIN_ISLAND",
            "width": 84, "depth": 42,
            "sink": {"type": "oval", "position": "center", "size": "standard"},
        })
        assert r.status_code == 200
        data = r.json()
        assert len(data["warnings"]) >= 1
        assert any("PLAIN_ISLAND" in w for w in data["warnings"])

    def test_mirror_flag_sets_variant(self, client: TestClient):
        r = client.post("/api/v1/templates/generate",
                        json=_single_vanity_body(mirror=True))
        assert r.status_code == 200
        assert r.json()["variant"] == "MIR"

    def test_kitchen_straight_structure(self, client: TestClient):
        r = client.post("/api/v1/templates/generate", json=_kitchen_body())
        data = r.json()
        assert data["assembly_type"] == "kitchen"
        assert data["template_id"]   == "KITCHEN_STRAIGHT"
        parts = data["parts"]
        main  = next(p for p in parts if p["part_type"] == "main_top")
        assert main["length"] == pytest.approx(120)
        assert main["cutout_count"] == 1   # rectangle sink

    def test_double_vanity_two_cutouts(self, client: TestClient):
        r = client.post("/api/v1/templates/generate", json={
            "template_id": "DOUBLE_VANITY",
            "width": 72, "depth": 22,
            "sink": {"type": "oval", "size": "standard"},
            "splash": {"back": False, "left": False, "right": False, "height": 4},
        })
        assert r.status_code == 200
        parts = r.json()["parts"]
        main = next(p for p in parts if p["part_type"] == "main_top")
        assert main["cutout_count"] == 2


# ===========================================================================
# 13. Sink preset mapping (dimensions in generate response)
# ===========================================================================

class TestSinkPresetMapping:

    def _get_main_top(self, client: TestClient, body: dict) -> dict:
        r = client.post("/api/v1/templates/generate", json=body)
        assert r.status_code == 200
        return next(
            p for p in r.json()["parts"] if p["part_type"] == "main_top"
        )

    def test_no_sink_zero_cutouts(self, client: TestClient):
        body = _single_vanity_body(sink={"type": "none"})
        top  = self._get_main_top(client, body)
        assert top["cutout_count"] == 0

    def test_rectangle_sink_has_cutout(self, client: TestClient):
        body = _single_vanity_body(
            sink={"type": "rectangle", "position": "center", "size": "standard"}
        )
        top = self._get_main_top(client, body)
        assert top["cutout_count"] == 1

    def test_oval_sink_has_cutout(self, client: TestClient):
        body = _single_vanity_body(
            sink={"type": "oval", "position": "center", "size": "standard"}
        )
        top = self._get_main_top(client, body)
        assert top["cutout_count"] == 1

    def test_large_sink_also_has_cutout(self, client: TestClient):
        body = _single_vanity_body(
            sink={"type": "oval", "position": "center", "size": "large"}
        )
        top = self._get_main_top(client, body)
        assert top["cutout_count"] == 1


# ===========================================================================
# 14. Splash toggle behavior
# ===========================================================================

class TestSplashToggle:

    def _part_count(self, client: TestClient, body: dict) -> int:
        r = client.post("/api/v1/templates/generate", json=body)
        assert r.status_code == 200
        return r.json()["part_count"]

    def test_all_splashes_on_4_parts(self, client: TestClient):
        body = _single_vanity_body(
            splash={"back": True, "left": True, "right": True, "height": 4}
        )
        assert self._part_count(client, body) == 4

    def test_back_only_2_parts(self, client: TestClient):
        body = _single_vanity_body(
            splash={"back": True, "left": False, "right": False, "height": 4}
        )
        assert self._part_count(client, body) == 2   # main top + BS

    def test_no_splash_1_part(self, client: TestClient):
        body = _single_vanity_body(
            splash={"back": False, "left": False, "right": False, "height": 4}
        )
        assert self._part_count(client, body) == 1   # main top only

    def test_kitchen_back_splash_only(self, client: TestClient):
        body = _kitchen_body(
            splash={"back": True, "left": False, "right": False, "height": 4}
        )
        r = client.post("/api/v1/templates/generate", json=body)
        assert r.status_code == 200
        splash_parts = [
            p for p in r.json()["parts"] if p["part_type"] == "loose_piece"
        ]
        assert len(splash_parts) == 1
        assert "Back" in splash_parts[0]["name"]


# ===========================================================================
# 9–12. POST /api/v1/templates/preview
# ===========================================================================

class TestPreview:

    def test_preview_returns_200(self, client: TestClient):
        r = client.post("/api/v1/templates/preview", json=_single_vanity_body())
        assert r.status_code == 200

    def test_preview_content_type(self, client: TestClient):
        r = client.post("/api/v1/templates/preview", json=_single_vanity_body())
        assert "image/svg+xml" in r.headers["content-type"]

    def test_preview_is_valid_svg(self, client: TestClient):
        r = client.post("/api/v1/templates/preview", json=_single_vanity_body())
        svg = r.text
        assert svg.startswith("<svg") or "<?xml" in svg
        assert "</svg>" in svg

    def test_preview_contains_rect_elements(self, client: TestClient):
        r = client.post("/api/v1/templates/preview", json=_single_vanity_body())
        assert "<rect" in r.text

    def test_preview_contains_text_elements(self, client: TestClient):
        r = client.post("/api/v1/templates/preview", json=_single_vanity_body())
        assert "<text" in r.text

    def test_preview_all_templates(self, client: TestClient):
        for tid in registry.ids():
            defn = registry.get(tid).definition.defaults
            body = {
                "template_id": tid,
                "width": defn.get("width", 60),
                "depth": defn.get("depth", 22),
                "sink":   {"type": "none"},
                "splash": {"back": False, "left": False, "right": False, "height": 4},
            }
            r = client.post("/api/v1/templates/preview", json=body)
            assert r.status_code == 200, f"Preview for {tid} failed: {r.text[:200]}"
            assert "<svg" in r.text or "</svg>" in r.text


# ===========================================================================
# 11–12. POST /api/v1/templates/pdf
# ===========================================================================

class TestPDF:

    def test_pdf_returns_200(self, client: TestClient):
        r = client.post("/api/v1/templates/pdf", json=_single_vanity_body())
        assert r.status_code == 200

    def test_pdf_content_type(self, client: TestClient):
        r = client.post("/api/v1/templates/pdf", json=_single_vanity_body())
        assert "application/pdf" in r.headers["content-type"]

    def test_pdf_non_empty(self, client: TestClient):
        r = client.post("/api/v1/templates/pdf", json=_single_vanity_body())
        assert len(r.content) > 500    # a real PDF is at least several hundred bytes

    def test_pdf_starts_with_header(self, client: TestClient):
        r = client.post("/api/v1/templates/pdf", json=_single_vanity_body())
        assert r.content[:4] == b"%PDF"   # standard PDF file header

    def test_pdf_all_templates(self, client: TestClient):
        for tid in registry.ids():
            defn = registry.get(tid).definition.defaults
            body = {
                "template_id": tid,
                "width": defn.get("width", 60),
                "depth": defn.get("depth", 22),
                "sink":   {"type": "none"},
                "splash": {"back": False, "left": False, "right": False, "height": 4},
            }
            r = client.post("/api/v1/templates/pdf", json=body)
            assert r.status_code == 200, f"PDF for {tid} failed"
            assert r.content[:4] == b"%PDF", f"PDF for {tid} is not a valid PDF"

    def test_pdf_content_disposition(self, client: TestClient):
        r = client.post("/api/v1/templates/pdf", json=_single_vanity_body(name="Bath A"))
        cd = r.headers.get("content-disposition", "")
        assert "Bath A.pdf" in cd or "SINGLE_VANITY" in cd


# ===========================================================================
# 16–17. UI contract in API response
# ===========================================================================

class TestUIContractInAPI:

    def test_single_vanity_sink_position_hidden(self, client: TestClient):
        r = client.get("/api/v1/templates/SINGLE_VANITY")
        fields = r.json()["ui_contract"]["fields"]
        pos = next((f for f in fields if f["key"] == "sink.position"), None)
        assert pos is not None
        assert pos["visible"] is False

    def test_offset_vanity_sink_position_visible(self, client: TestClient):
        r = client.get("/api/v1/templates/OFFSET_VANITY")
        fields = r.json()["ui_contract"]["fields"]
        pos = next(f for f in fields if f["key"] == "sink.position")
        assert pos["visible"] is True

    def test_plain_island_splash_fields_hidden(self, client: TestClient):
        r = client.get("/api/v1/templates/PLAIN_ISLAND")
        fields = r.json()["ui_contract"]["fields"]
        splash = [f for f in fields if f["key"].startswith("splash.") and not f["visible"]]
        assert len(splash) == 4

    def test_kitchen_uses_length_label(self, client: TestClient):
        r = client.get("/api/v1/templates/KITCHEN_STRAIGHT")
        fields = r.json()["ui_contract"]["fields"]
        width_field = next(f for f in fields if f["key"] == "width")
        assert width_field["label"] == "Length"

    def test_all_select_fields_have_options(self, client: TestClient):
        for tid in registry.ids():
            r = client.get(f"/api/v1/templates/{tid}")
            fields = r.json()["ui_contract"]["fields"]
            for f in fields:
                if f["field_type"] == "select" and f["visible"]:
                    assert f["options"], f"{tid}.{f['key']}: visible select with no options"


# ===========================================================================
# Phase 8 — POST /api/v1/templates/save  (Connected Workflow)
# ===========================================================================

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.dependencies import get_db
from app.repositories.hierarchy_repository import ProjectHierarchyRepository
from app.services.hierarchy_service import HierarchyService

_SAVE_TENANT = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
_SAVE_USER = User(
    tenant_id=_SAVE_TENANT,
    email="save@buildesk.app",
    hashed_password="x",
    role="admin",
)


@pytest.fixture(scope="function")
def save_db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def save_client(save_db_session: Session):
    app = create_app()

    def override_db():
        yield save_db_session

    app.dependency_overrides[get_db]                = override_db
    app.dependency_overrides[get_current_tenant]    = lambda: _SAVE_TENANT
    app.dependency_overrides[require_active_user]   = lambda: _SAVE_USER
    with TestClient(app) as tc:
        yield tc
    app.dependency_overrides.clear()


@pytest.fixture
def save_project_id(save_db_session: Session) -> str:
    svc  = HierarchyService(ProjectHierarchyRepository(save_db_session))
    proj = svc.create_project(_SAVE_TENANT, "Save Test Project")
    return str(proj.project_id)


class TestSaveAssembly:
    """Phase 8 — POST /api/v1/templates/save persists Assembly to DB."""

    def test_save_creates_assembly_201(self, save_client, save_project_id):
        body = {
            "template_id": "SINGLE_VANITY",
            "project_id":  save_project_id,
            "width": 62,
            "depth": 22,
            "splash": {"back": True, "left": True, "right": True, "height": 4},
            "sink": {"type": "oval", "position": "center", "size": "standard"},
            "edge_finish": "polished",
        }
        r = save_client.post("/api/v1/templates/save", json=body)
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["template_id"]  == "SINGLE_VANITY"
        assert data["assembly_id"]  is not None
        assert data["part_count"]   >= 1
        assert data["assembly_type"] == "vanity"

    def test_save_assembly_retrievable_from_db(self, save_client, save_project_id):
        body = {
            "template_id": "KITCHEN_STRAIGHT",
            "project_id":  save_project_id,
            "width": 96,
            "depth": 25,
            "splash": {"back": True, "left": False, "right": False, "height": 4},
            "sink": {"type": "rectangle", "position": "center", "size": "standard"},
            "edge_finish": "polished",
        }
        r = save_client.post("/api/v1/templates/save", json=body)
        assert r.status_code == 201
        assembly_id = r.json()["assembly_id"]

        # Verify the assembly is now in the DB via GET /assemblies
        r2 = save_client.get(f"/api/v1/assemblies/{assembly_id}")
        assert r2.status_code == 200
        assert r2.json()["assembly_id"] == assembly_id

    def test_save_without_project_id_returns_422(self, save_client):
        body = {
            "template_id": "SINGLE_VANITY",
            "width": 62,
            "depth": 22,
            "sink": {"type": "none"},
            "splash": {"back": False, "left": False, "right": False, "height": 4},
        }
        r = save_client.post("/api/v1/templates/save", json=body)
        assert r.status_code == 422
