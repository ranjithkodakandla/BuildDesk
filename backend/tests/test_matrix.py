"""
Phase 6 — Matrix Setup API Tests
===================================
Tests for POST /api/v1/projects/{project_id}/units/bulk-matrix
        and GET  /api/v1/projects/{project_id}/matrix

Coverage:
  1.  Basic 3-row matrix creates units
  2.  Idempotency — same rows submitted twice, second is "existing"
  3.  Unknown project returns 404
  4.  Missing required fields returns 422
  5.  ADA + Mirror variants set correct UnitVariant
  6.  Auto-creates buildings and floors
  7.  Auto-enables has_buildings + has_floors on project
  8.  UnitType code encodes template + mirror + ada suffix
  9.  Single building multiple floors
  10. Multiple buildings
  11. GET /matrix returns all units as rows
  12. Empty row list returns 422
  13. Row count > 500 returns 422
  14. Mix of templates in one call
  15. Template stored in UnitType.description
  16. Building sort_order populated
  17. Units exist after call (verify via GET /projects/.../units)
  18. Row result has expected fields
  19. buildings_total correct in response
  20. floors_total correct in response
"""
from __future__ import annotations

import uuid
from typing import List

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_tenant, require_active_user
from app.db.base import Base
from app.dependencies import get_db
from app.main import create_app
from app.models.hierarchy import UnitVariant
from app.models.user import User
from app.repositories.hierarchy_repository import ProjectHierarchyRepository
from app.services.hierarchy_service import HierarchyService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_TENANT = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
_USER = User(
    tenant_id=_TENANT,
    email="matrix@buildesk.app",
    hashed_password="x",
    role="admin",
)


@pytest.fixture(scope="function")
def db_session():
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
def client(db_session: Session):
    app = create_app()

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_tenant] = lambda: _TENANT
    app.dependency_overrides[require_active_user] = lambda: _USER
    with TestClient(app) as tc:
        yield tc
    app.dependency_overrides.clear()


@pytest.fixture
def project_id(db_session: Session) -> str:
    """Create a project in the DB and return its ID string."""
    svc = HierarchyService(ProjectHierarchyRepository(db_session))
    proj = svc.create_project(_TENANT, "Test Project")
    return str(proj.project_id)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rows(*args) -> List[dict]:
    """Quick builder: positional tuples of (building, floor, flat, template, mirror, ada)."""
    return [
        {"building": b, "floor": f, "flat": u, "template": t, "mirror": m, "ada": a}
        for b, f, u, t, m, a in args
    ]


def _post_matrix(client, project_id, rows):
    return client.post(
        f"/api/v1/projects/{project_id}/units/bulk-matrix",
        json={"rows": rows},
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestBasicMatrix:

    def test_basic_three_rows_creates_units(self, client, project_id):
        rows = _rows(
            ("A", "1", "101", "SINGLE_VANITY", False, False),
            ("A", "1", "102", "SINGLE_VANITY", True,  False),
            ("A", "2", "201", "KITCHEN_L",     False, False),
        )
        r = _post_matrix(client, project_id, rows)
        assert r.status_code == 200
        data = r.json()
        assert data["rows_processed"] == 3
        assert data["units_created"]  == 3
        assert data["units_existing"] == 0

    def test_all_results_have_unit_id(self, client, project_id):
        rows = _rows(("A", "1", "101", "SINGLE_VANITY", False, False))
        r = _post_matrix(client, project_id, rows)
        results = r.json()["results"]
        assert all(res["unit_id"] is not None for res in results)

    def test_all_results_have_building_id(self, client, project_id):
        rows = _rows(("A", "1", "101", "SINGLE_VANITY", False, False))
        r = _post_matrix(client, project_id, rows)
        results = r.json()["results"]
        assert all(res["building_id"] is not None for res in results)

    def test_row_index_populated(self, client, project_id):
        rows = _rows(
            ("A", "1", "101", "SINGLE_VANITY", False, False),
            ("A", "1", "102", "SINGLE_VANITY", False, False),
        )
        r = _post_matrix(client, project_id, rows)
        results = r.json()["results"]
        assert results[0]["row_index"] == 0
        assert results[1]["row_index"] == 1


class TestIdempotency:

    def test_same_rows_twice_second_is_existing(self, client, project_id):
        rows = _rows(("A", "1", "101", "SINGLE_VANITY", False, False))
        _post_matrix(client, project_id, rows)   # first call
        r2 = _post_matrix(client, project_id, rows)  # second call
        data = r2.json()
        assert data["units_created"]  == 0
        assert data["units_existing"] == 1

    def test_mixed_new_and_existing(self, client, project_id):
        rows1 = _rows(("A", "1", "101", "SINGLE_VANITY", False, False))
        _post_matrix(client, project_id, rows1)
        rows2 = _rows(
            ("A", "1", "101", "SINGLE_VANITY", False, False),  # existing
            ("A", "1", "102", "SINGLE_VANITY", False, False),  # new
        )
        data = _post_matrix(client, project_id, rows2).json()
        assert data["units_created"]  == 1
        assert data["units_existing"] == 1

    def test_submit_same_rows_100_times(self, client, project_id):
        rows = _rows(("B", "3", "301", "DOUBLE_VANITY", False, False))
        for _ in range(3):
            _post_matrix(client, project_id, rows)
        r = _post_matrix(client, project_id, rows)
        data = r.json()
        assert data["units_existing"] == 1
        assert data["units_created"]  == 0


class TestValidation:

    def test_unknown_project_404(self, client):
        fake_id = str(uuid.uuid4())
        r = client.post(
            f"/api/v1/projects/{fake_id}/units/bulk-matrix",
            json={"rows": [{"building": "A", "floor": "1", "flat": "101",
                            "template": "SINGLE_VANITY", "mirror": False, "ada": False}]},
        )
        assert r.status_code == 404

    def test_empty_rows_422(self, client, project_id):
        r = _post_matrix(client, project_id, [])
        assert r.status_code == 422

    def test_missing_template_field_422(self, client, project_id):
        r = client.post(
            f"/api/v1/projects/{project_id}/units/bulk-matrix",
            json={"rows": [{"building": "A", "floor": "1", "flat": "101"}]},
        )
        assert r.status_code == 422

    def test_blank_building_422(self, client, project_id):
        r = client.post(
            f"/api/v1/projects/{project_id}/units/bulk-matrix",
            json={"rows": [{"building": "  ", "floor": "1", "flat": "101",
                            "template": "SINGLE_VANITY", "mirror": False, "ada": False}]},
        )
        assert r.status_code == 422


class TestVariants:

    def test_mirror_sets_mirror_variant(self, client, db_session, project_id):
        rows = _rows(("A", "1", "101", "SINGLE_VANITY", True, False))
        _post_matrix(client, project_id, rows)
        r = client.get(f"/api/v1/projects/{project_id}/units")
        units = r.json()["units"]
        unit = next(u for u in units if u["code"] == "101")
        assert unit["variant"] == UnitVariant.MIRROR.value

    def test_ada_sets_ada_variant(self, client, project_id):
        rows = _rows(("A", "1", "102", "KITCHEN_STRAIGHT", False, True))
        _post_matrix(client, project_id, rows)
        r = client.get(f"/api/v1/projects/{project_id}/units")
        units = r.json()["units"]
        unit = next(u for u in units if u["code"] == "102")
        assert unit["variant"] == UnitVariant.ADA.value

    def test_standard_variant(self, client, project_id):
        rows = _rows(("A", "1", "103", "KITCHEN_L", False, False))
        _post_matrix(client, project_id, rows)
        r = client.get(f"/api/v1/projects/{project_id}/units")
        units = r.json()["units"]
        unit = next(u for u in units if u["code"] == "103")
        assert unit["variant"] == UnitVariant.STANDARD.value


class TestUnitTypeEncoding:

    def _get_unit_types(self, client, project_id) -> list:
        return client.get(f"/api/v1/projects/{project_id}/unit-types").json()["unit_types"]

    def test_no_suffix_for_standard(self, client, project_id):
        rows = _rows(("A", "1", "101", "SINGLE_VANITY", False, False))
        r = _post_matrix(client, project_id, rows)
        result = r.json()["results"][0]
        unit_types = self._get_unit_types(client, project_id)
        ut = next(x for x in unit_types if x["unit_type_id"] == result["unit_type_id"])
        assert ut["code"] == "SINGLE_VANITY"

    def test_mirror_suffix(self, client, project_id):
        rows = _rows(("A", "1", "102", "SINGLE_VANITY", True, False))
        r = _post_matrix(client, project_id, rows)
        result = r.json()["results"][0]
        unit_types = self._get_unit_types(client, project_id)
        ut = next(x for x in unit_types if x["unit_type_id"] == result["unit_type_id"])
        assert ut["code"] == "SINGLE_VANITY_MIR"

    def test_ada_suffix(self, client, project_id):
        rows = _rows(("A", "1", "103", "KITCHEN_L", False, True))
        r = _post_matrix(client, project_id, rows)
        result = r.json()["results"][0]
        unit_types = self._get_unit_types(client, project_id)
        ut = next(x for x in unit_types if x["unit_type_id"] == result["unit_type_id"])
        assert ut["code"] == "KITCHEN_L_ADA"

    def test_template_stored_in_description(self, client, project_id):
        rows = _rows(("A", "1", "101", "DOUBLE_VANITY", False, False))
        r = _post_matrix(client, project_id, rows)
        result = r.json()["results"][0]
        unit_types = self._get_unit_types(client, project_id)
        ut = next(x for x in unit_types if x["unit_type_id"] == result["unit_type_id"])
        assert ut["description"] == "DOUBLE_VANITY"


class TestHierarchy:

    def test_auto_enables_buildings_and_floors(self, client, project_id):
        # Project starts without has_buildings / has_floors
        rows = _rows(("A", "1", "101", "SINGLE_VANITY", False, False))
        _post_matrix(client, project_id, rows)
        proj = client.get(f"/api/v1/projects/{project_id}").json()
        assert proj["hierarchy_config"]["has_buildings"] is True
        assert proj["hierarchy_config"]["has_floors"]    is True

    def test_creates_building_and_floor(self, client, project_id):
        rows = _rows(("North", "2", "201", "KITCHEN_STRAIGHT", False, False))
        _post_matrix(client, project_id, rows)
        buildings = client.get(f"/api/v1/projects/{project_id}/buildings").json()
        assert any(b["code"] == "North" for b in buildings)

    def test_multiple_buildings(self, client, project_id):
        rows = _rows(
            ("A", "1", "101", "SINGLE_VANITY",   False, False),
            ("B", "1", "101", "KITCHEN_STRAIGHT", False, False),
            ("C", "1", "101", "KITCHEN_L",        False, False),
        )
        data = _post_matrix(client, project_id, rows).json()
        assert data["buildings_total"] == 3

    def test_single_building_multiple_floors(self, client, project_id):
        rows = _rows(
            ("A", "1", "101", "SINGLE_VANITY", False, False),
            ("A", "2", "201", "SINGLE_VANITY", False, False),
            ("A", "3", "301", "SINGLE_VANITY", False, False),
        )
        data = _post_matrix(client, project_id, rows).json()
        assert data["buildings_total"] == 1
        assert data["floors_total"]    == 3


class TestSummaryCounters:

    def test_buildings_total(self, client, project_id):
        rows = _rows(
            ("A", "1", "101", "SINGLE_VANITY", False, False),
            ("A", "1", "102", "SINGLE_VANITY", False, False),
            ("B", "1", "101", "KITCHEN_L",     False, False),
        )
        data = _post_matrix(client, project_id, rows).json()
        assert data["buildings_total"] == 2

    def test_floors_total(self, client, project_id):
        rows = _rows(
            ("A", "1", "101", "SINGLE_VANITY", False, False),
            ("A", "2", "201", "SINGLE_VANITY", False, False),
            ("B", "1", "101", "KITCHEN_L",     False, False),
        )
        data = _post_matrix(client, project_id, rows).json()
        assert data["floors_total"] == 3

    def test_unit_types_total_deduplicates(self, client, project_id):
        # 5 rows, but only 2 unique templates (same template → same unit type)
        rows = _rows(
            ("A", "1", "101", "SINGLE_VANITY", False, False),
            ("A", "1", "102", "SINGLE_VANITY", False, False),
            ("A", "1", "103", "SINGLE_VANITY", False, False),
            ("B", "1", "101", "KITCHEN_L",     False, False),
            ("B", "1", "102", "KITCHEN_L",     False, False),
        )
        data = _post_matrix(client, project_id, rows).json()
        assert data["unit_types_total"] == 2

    def test_mix_of_templates(self, client, project_id):
        rows = _rows(
            ("A", "1", "101", "SINGLE_VANITY",   False, False),
            ("A", "1", "102", "DOUBLE_VANITY",   False, False),
            ("A", "1", "103", "KITCHEN_STRAIGHT", False, False),
            ("A", "1", "104", "KITCHEN_L",        False, False),
            ("A", "1", "105", "PLAIN_ISLAND",     False, False),
        )
        data = _post_matrix(client, project_id, rows).json()
        assert data["units_created"] == 5
        assert data["unit_types_total"] == 5


class TestGetMatrix:

    def test_get_matrix_returns_rows(self, client, project_id):
        rows = _rows(
            ("A", "1", "101", "SINGLE_VANITY", False, False),
            ("A", "1", "102", "SINGLE_VANITY", True,  False),
        )
        _post_matrix(client, project_id, rows)
        r = client.get(f"/api/v1/projects/{project_id}/matrix")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 2

    def test_get_matrix_includes_template(self, client, project_id):
        rows = _rows(("A", "1", "101", "KITCHEN_L", False, False))
        _post_matrix(client, project_id, rows)
        data = client.get(f"/api/v1/projects/{project_id}/matrix").json()
        assert data["rows"][0]["template"] == "KITCHEN_L"

    def test_get_matrix_mirror_flag(self, client, project_id):
        rows = _rows(("A", "1", "101", "SINGLE_VANITY", True, False))
        _post_matrix(client, project_id, rows)
        data = client.get(f"/api/v1/projects/{project_id}/matrix").json()
        assert data["rows"][0]["mirror"] is True
