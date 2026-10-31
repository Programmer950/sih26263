"""Tests for Authentication, JTI Session Revocation, and RBAC / Tenancy Isolation (Milestone 1B)."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import (
    hash_password,
    verify_password,
    compute_blind_index,
    encrypt_sensitive_field,
    decrypt_sensitive_field,
)
from app.core.permissions import TenantGuard
from app.models import User, Role
import uuid

client = TestClient(app)


def test_argon2id_hashing():
    """Verify Argon2id produces valid hash and verifies correctly."""
    raw = "SecureSecretPassword123!"
    hashed = hash_password(raw)
    assert hashed.startswith("$argon2id$")
    assert verify_password(raw, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_blind_index_determinism():
    """Verify HMAC blind index is deterministic and format-normalized."""
    apaar_1 = "1234-5678-9012"
    apaar_2 = "123456789012"
    apaar_3 = " 1234 5678 9012 "
    idx1 = compute_blind_index(apaar_1)
    idx2 = compute_blind_index(apaar_2)
    idx3 = compute_blind_index(apaar_3)
    assert idx1 == idx2 == idx3
    assert len(idx1) == 64  # SHA-256 hex string


def test_aes_gcm_encryption_roundtrip():
    """Verify AES-256-GCM encrypts and decrypts with key versioning."""
    secret_text = "CONFIDENTIAL_STUDENT_IDENTITY_REF"
    encrypted = encrypt_sensitive_field(secret_text, key_version="v1")
    assert encrypted.startswith("enc:v1:")
    decrypted = decrypt_sensitive_field(encrypted)
    assert decrypted == secret_text


def test_login_success_seeded_accounts():
    """Safeguard 1: Demo login must authenticate actual seeded backend accounts with fixed roles."""
    # 1. Test Apex Admin login
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@apex.edu.in", "password": "Apex@12345"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["role"] == "INSTITUTION_ADMIN"
    assert data["user"]["institution_code"] == "INST-APEX-001"
    assert data["expires_in"] == 900  # 15 minutes

    # 2. Test AICTE Reviewer login
    res_rev = client.post(
        "/api/v1/auth/login",
        json={"email": "reviewer@aicte.gov.in", "password": "Reviewer@12345"},
    )
    assert res_rev.status_code == 200
    data_rev = res_rev.json()
    assert data_rev["user"]["role"] == "REGULATORY_REVIEWER"
    assert data_rev["user"]["institution_id"] is None


def test_login_invalid_credentials():
    """Verify login rejection with incorrect password."""
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@apex.edu.in", "password": "WrongPassword!"},
    )
    assert res.status_code == 401
    assert "Invalid email or password" in res.json()["detail"]


def test_auth_me_and_session_revocation():
    """Safeguard 2: Verify access to /auth/me and immediate server-side JTI revocation upon logout."""
    # Login
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@apex.edu.in", "password": "Apex@12345"},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Access /auth/me
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "admin@apex.edu.in"
    assert me_res.json()["role"] == "INSTITUTION_ADMIN"

    # Logout (revokes token's JTI)
    logout_res = client.post("/api/v1/auth/logout", headers=headers)
    assert logout_res.status_code == 200
    assert logout_res.json()["success"] is True

    # Re-accessing /auth/me with revoked token MUST return 401 Unauthorized
    revoked_res = client.get("/api/v1/auth/me", headers=headers)
    assert revoked_res.status_code == 401
    assert "Session has been terminated" in revoked_res.json()["detail"]


def test_tenant_isolation_guard():
    """Safeguard 3: Enforce tenant isolation; institution admins cannot query other institutions."""
    apex_inst_id = uuid.uuid4()
    other_inst_id = uuid.uuid4()

    # Mock user object for Institution Admin
    mock_role = Role(role_name="INSTITUTION_ADMIN")
    mock_inst_user = User(
        name="Apex Admin",
        email="admin@apex.edu.in",
        password_hash="fake",
        role=mock_role,
        institution_id=apex_inst_id,
    )

    guard = TenantGuard(current_user=mock_inst_user)

    # Scoping without argument returns user's own institution
    assert guard.scope_institution_id() == apex_inst_id

    # Requesting own institution is allowed
    assert guard.scope_institution_id(apex_inst_id) == apex_inst_id

    # Requesting a foreign institution raises 403 Forbidden
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as excinfo:
        guard.scope_institution_id(other_inst_id)
    assert excinfo.value.status_code == 403
    assert "Tenancy Violation" in excinfo.value.detail

    # Regulatory Reviewer may query any institution
    reviewer_role = Role(role_name="REGULATORY_REVIEWER")
    mock_reviewer = User(
        name="AICTE Reviewer",
        email="reviewer@aicte.gov.in",
        password_hash="fake",
        role=reviewer_role,
        institution_id=None,
    )
    rev_guard = TenantGuard(current_user=mock_reviewer)
    assert rev_guard.scope_institution_id(other_inst_id) == other_inst_id
    assert rev_guard.scope_institution_id(None) is None

