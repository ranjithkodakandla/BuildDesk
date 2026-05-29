"""
Smoke Tests — Authentication Foundation Layer
==============================================
Tests all auth requirements:
  ✓ User registration
  ✓ Login / JWT issuance
  ✓ JWT validation via /auth/me
  ✓ Protected route access with valid token
  ✓ Protected route rejection without token
  ✓ Tenant isolation via JWT
  ✓ Invalid credentials
  ✓ Expired token handling
  ✓ Duplicate registration rejection
"""
from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import uuid
from datetime import timedelta

from fastapi.testclient import TestClient

# Use in-memory mode for isolated testing
os.environ["USE_SQL_REPOSITORY"] = "false"
os.environ["APP_ENV"] = "test"
os.environ["JWT_SECRET_KEY"] = "smoke-test-secret-key-do-not-use-in-production"

from app.main import app
from app.auth.jwt import create_access_token, decode_access_token, TokenError
from app.auth.password import hash_password, verify_password

client = TestClient(app, raise_server_exceptions=True)

TENANT_A = str(uuid.uuid4())
TENANT_B = str(uuid.uuid4())

PASS_OK = "SecurePass123!"

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def register(email: str, password: str, tenant_id: str, role: str = "member") -> dict:
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "role": role},
        headers={"X-Tenant-ID": tenant_id},
    )
    return resp

def login(email: str, password: str, tenant_id: str) -> dict:
    return client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
        headers={"X-Tenant-ID": tenant_id},
    )

# ──────────────────────────────────────────────────────────────────────────────
# 1. Password utility tests (unit)
# ──────────────────────────────────────────────────────────────────────────────

def test_password_hash_and_verify():
    hashed = hash_password("MySecret99")
    assert hashed != "MySecret99", "plaintext must NOT be stored"
    assert verify_password("MySecret99", hashed), "correct password must verify"
    assert not verify_password("WrongPass", hashed), "wrong password must NOT verify"
    print("✓ password hash + verify")

# ──────────────────────────────────────────────────────────────────────────────
# 2. JWT utility tests (unit)
# ──────────────────────────────────────────────────────────────────────────────

def test_create_and_decode_jwt():
    uid  = uuid.uuid4()
    tid  = uuid.uuid4()
    tok  = create_access_token(user_id=uid, tenant_id=tid, email="j@test.com", role="member")
    payload = decode_access_token(tok)
    assert payload["sub"]   == str(uid)
    assert payload["tid"]   == str(tid)
    assert payload["email"] == "j@test.com"
    print("✓ JWT create + decode")

def test_expired_token_raises():
    tok = create_access_token(
        user_id=uuid.uuid4(), tenant_id=uuid.uuid4(),
        email="expired@test.com", role="member",
        expires_delta=timedelta(seconds=-1),
    )
    try:
        decode_access_token(tok)
        assert False, "Should have raised TokenError"
    except TokenError:
        pass
    print("✓ expired token raises TokenError")

def test_tampered_token_raises():
    tok = create_access_token(
        user_id=uuid.uuid4(), tenant_id=uuid.uuid4(),
        email="x@test.com", role="member",
    )
    tampered = tok[:-5] + "XXXXX"
    try:
        decode_access_token(tampered)
        assert False, "Should have raised TokenError"
    except TokenError:
        pass
    print("✓ tampered token raises TokenError")

# ──────────────────────────────────────────────────────────────────────────────
# 3. Registration
# ──────────────────────────────────────────────────────────────────────────────

def test_register_success():
    email = f"user-{uuid.uuid4().hex[:6]}@test.com"
    resp = register(email, PASS_OK, TENANT_A)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["email"] == email.lower()
    print("✓ registration returns 201 + token")

def test_register_duplicate_email_rejected():
    email = f"dup-{uuid.uuid4().hex[:6]}@test.com"
    register(email, PASS_OK, TENANT_A)
    resp = register(email, PASS_OK, TENANT_A)
    assert resp.status_code == 409, resp.text
    print("✓ duplicate email → 409 Conflict")

def test_register_same_email_different_tenant_allowed():
    """Same email address may exist in different tenants."""
    email = f"shared-{uuid.uuid4().hex[:6]}@test.com"
    r1 = register(email, PASS_OK, TENANT_A)
    r2 = register(email, PASS_OK, TENANT_B)
    assert r1.status_code == 201, r1.text
    assert r2.status_code == 201, r2.text
    print("✓ same email in different tenants → both 201")

# ──────────────────────────────────────────────────────────────────────────────
# 4. Login
# ──────────────────────────────────────────────────────────────────────────────

def test_login_success():
    email = f"login-{uuid.uuid4().hex[:6]}@test.com"
    register(email, PASS_OK, TENANT_A)
    resp = login(email, PASS_OK, TENANT_A)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "access_token" in data
    print("✓ login returns 200 + token")

def test_login_wrong_password():
    email = f"badpw-{uuid.uuid4().hex[:6]}@test.com"
    register(email, PASS_OK, TENANT_A)
    resp = login(email, "WrongPassword!", TENANT_A)
    assert resp.status_code == 401, resp.text
    print("✓ wrong password → 401")

def test_login_unknown_user():
    resp = login("nobody@test.com", PASS_OK, TENANT_A)
    assert resp.status_code == 401, resp.text
    print("✓ unknown user → 401")

# ──────────────────────────────────────────────────────────────────────────────
# 5. JWT validation via /auth/me
# ──────────────────────────────────────────────────────────────────────────────

def test_me_with_valid_token():
    email = f"me-{uuid.uuid4().hex[:6]}@test.com"
    r = register(email, PASS_OK, TENANT_A)
    token = r.json()["access_token"]
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["email"] == email.lower()
    print("✓ /auth/me returns profile for valid token")

def test_me_without_token():
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401, resp.text
    print("✓ /auth/me → 401 without token")

def test_me_with_expired_token():
    uid = uuid.uuid4()
    tok = create_access_token(
        user_id=uid, tenant_id=uuid.UUID(TENANT_A),
        email="exp@test.com", role="member",
        expires_delta=timedelta(seconds=-1),
    )
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tok}"})
    assert resp.status_code == 401, resp.text
    print("✓ /auth/me → 401 for expired token")

# ──────────────────────────────────────────────────────────────────────────────
# 6. Protected route access
# ──────────────────────────────────────────────────────────────────────────────

GEOMETRY_PAYLOAD = {
    "shape_type": "rectangle",
    "project_id": str(uuid.uuid4()),
    "tenant_id":  TENANT_A,
    "dimensions": {"length": 96, "width": 42},
}

def _get_token(tenant_id: str = TENANT_A) -> str:
    email = f"prot-{uuid.uuid4().hex[:6]}@test.com"
    r = register(email, PASS_OK, tenant_id)
    return r.json()["access_token"]

def test_geometry_post_requires_auth():
    resp = client.post("/api/v1/geometry", json=GEOMETRY_PAYLOAD)
    assert resp.status_code == 401, resp.text
    print("✓ POST /geometry → 401 without token")

def test_geometry_post_with_valid_token():
    token = _get_token()
    resp = client.post(
        "/api/v1/geometry",
        json=GEOMETRY_PAYLOAD,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["shape_type"] == "rectangle"
    print("✓ POST /geometry → 200 with valid token")

def test_geometry_get_requires_auth():
    resp = client.get(f"/api/v1/geometry/{uuid.uuid4()}")
    assert resp.status_code == 401, resp.text
    print("✓ GET /geometry/{id} → 401 without token")

def test_svg_export_requires_auth():
    resp = client.post("/api/v1/export/svg", json=GEOMETRY_PAYLOAD)
    assert resp.status_code == 401, resp.text
    print("✓ POST /export/svg → 401 without token")

def test_pdf_export_requires_auth():
    resp = client.post("/api/v1/export/pdf", json=GEOMETRY_PAYLOAD)
    assert resp.status_code == 401, resp.text
    print("✓ POST /export/pdf → 401 without token")

def test_demo_endpoints_remain_public():
    """Demo endpoints must NOT require authentication."""
    resp = client.get("/api/v1/demo/rectangle")
    assert resp.status_code == 200, resp.text
    print("✓ GET /demo/rectangle → 200 (public, no auth required)")

# ──────────────────────────────────────────────────────────────────────────────
# 7. Tenant isolation via JWT
# ──────────────────────────────────────────────────────────────────────────────

def test_tenant_isolation_via_jwt():
    """A geometry created in tenant A must NOT be accessible by tenant B's token."""
    email_a = f"ta-{uuid.uuid4().hex[:6]}@test.com"
    email_b = f"tb-{uuid.uuid4().hex[:6]}@test.com"

    token_a = register(email_a, PASS_OK, TENANT_A).json()["access_token"]
    token_b = register(email_b, PASS_OK, TENANT_B).json()["access_token"]

    # Create geometry as tenant A
    create_resp = client.post(
        "/api/v1/geometry",
        json=GEOMETRY_PAYLOAD,
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert create_resp.status_code == 200, create_resp.text
    geo_id = create_resp.json()["geometry_id"]

    # Tenant B cannot read it
    get_resp = client.get(
        f"/api/v1/geometry/{geo_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert get_resp.status_code == 404, get_resp.text
    print("✓ Tenant B cannot access Tenant A geometry — isolation verified")

# ──────────────────────────────────────────────────────────────────────────────
# 8. Dev mode X-Tenant-ID fallback still works
# ──────────────────────────────────────────────────────────────────────────────

def test_dev_fallback_header():
    """In non-production mode, X-Tenant-ID header should still work as fallback."""
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": f"dev-{uuid.uuid4().hex[:6]}@test.com", "password": PASS_OK},
        headers={"X-Tenant-ID": TENANT_A},  # no Bearer token
    )
    # register itself calls get_current_tenant which accepts the header in dev mode
    assert resp.status_code == 201, resp.text
    print("✓ X-Tenant-ID header fallback works in dev/test mode")

# ──────────────────────────────────────────────────────────────────────────────
# Main runner
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        # Password / JWT unit
        test_password_hash_and_verify,
        test_create_and_decode_jwt,
        test_expired_token_raises,
        test_tampered_token_raises,
        # Registration
        test_register_success,
        test_register_duplicate_email_rejected,
        test_register_same_email_different_tenant_allowed,
        # Login
        test_login_success,
        test_login_wrong_password,
        test_login_unknown_user,
        # /me endpoint
        test_me_with_valid_token,
        test_me_without_token,
        test_me_with_expired_token,
        # Protected routes
        test_geometry_post_requires_auth,
        test_geometry_post_with_valid_token,
        test_geometry_get_requires_auth,
        test_svg_export_requires_auth,
        test_pdf_export_requires_auth,
        test_demo_endpoints_remain_public,
        # Tenant isolation
        test_tenant_isolation_via_jwt,
        # Dev fallback
        test_dev_fallback_header,
    ]

    passed = failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as exc:
            print(f"✗ {t.__name__}: {exc}")
            failed += 1

    total = passed + failed
    print(f"\n{'='*55}")
    print(f"Auth Smoke Tests: {passed}/{total} passed", "✅" if failed == 0 else "❌")
    if failed:
        sys.exit(1)
