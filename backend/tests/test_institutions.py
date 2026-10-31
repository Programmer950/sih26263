"""Tests for Institution and Programme Management & Tenancy Boundaries (Milestone 1C)."""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@pytest.fixture(scope="module")
def tokens():
    """Logs in seeded users and provides Bearer tokens."""
    # 1. Apex Admin
    res_apex = client.post("/api/v1/auth/login", json={"email": "admin@apex.edu.in", "password": "Apex@12345"})
    assert res_apex.status_code == 200
    apex_token = res_apex.json()["access_token"]
    apex_inst_id = res_apex.json()["user"]["institution_id"]

    # 2. Polytechnic Admin
    res_poly = client.post("/api/v1/auth/login", json={"email": "admin@polytechnic.edu.in", "password": "Poly@12345"})
    assert res_poly.status_code == 200
    poly_token = res_poly.json()["access_token"]
    poly_inst_id = res_poly.json()["user"]["institution_id"]

    # 3. AICTE Reviewer
    res_rev = client.post("/api/v1/auth/login", json={"email": "reviewer@aicte.gov.in", "password": "Reviewer@12345"})
    assert res_rev.status_code == 200
    reviewer_token = res_rev.json()["access_token"]

    # 4. System Admin
    res_sys = client.post("/api/v1/auth/login", json={"email": "sysadmin@aicte.gov.in", "password": "Admin@12345"})
    assert res_sys.status_code == 200
    sys_token = res_sys.json()["access_token"]

    return {
        "apex": {"token": apex_token, "inst_id": apex_inst_id},
        "poly": {"token": poly_token, "inst_id": poly_inst_id},
        "reviewer": {"token": reviewer_token},
        "sysadmin": {"token": sys_token},
    }


def test_list_institutions_tenancy_isolation(tokens):
    """
    Safeguard 3:
    - Reviewer sees all seeded institutions (>= 3).
    - Apex Admin strictly sees only their own institution (1 item).
    """
    # Reviewer
    res_rev = client.get("/api/v1/institutions", headers={"Authorization": f"Bearer {tokens['reviewer']['token']}"})
    assert res_rev.status_code == 200
    data_rev = res_rev.json()
    assert data_rev["total"] >= 3

    # Apex Admin
    res_apex = client.get("/api/v1/institutions", headers={"Authorization": f"Bearer {tokens['apex']['token']}"})
    assert res_apex.status_code == 200
    data_apex = res_apex.json()
    assert data_apex["total"] == 1
    assert data_apex["items"][0]["id"] == tokens["apex"]["inst_id"]


def test_get_institution_detail_idor_protection(tokens):
    """
    Safeguard 3: An institution administrator cannot access another institution's records.
    """
    # Apex admin accessing Apex -> 200 OK
    res_ok = client.get(
        f"/api/v1/institutions/{tokens['apex']['inst_id']}",
        headers={"Authorization": f"Bearer {tokens['apex']['token']}"},
    )
    assert res_ok.status_code == 200
    assert res_ok.json()["institution_code"] in ("INST-APEX-001", "AIT", "APEX")

    # Apex admin accessing Polytechnic -> 403 Forbidden
    res_forbidden = client.get(
        f"/api/v1/institutions/{tokens['poly']['inst_id']}",
        headers={"Authorization": f"Bearer {tokens['apex']['token']}"},
    )
    assert res_forbidden.status_code == 403
    assert "Tenancy Violation" in res_forbidden.json()["detail"]


def test_list_programmes_with_approved_intake(tokens):
    """Verify listing programmes and retrieving versioned approved intake limits."""
    res = client.get(
        f"/api/v1/institutions/{tokens['apex']['inst_id']}/programmes?academic_year=2024-25",
        headers={"Authorization": f"Bearer {tokens['apex']['token']}"},
    )
    assert res.status_code == 200
    programmes = res.json()
    assert len(programmes) >= 3

    cse = next(p for p in programmes if p["programme_code"] in ("CSE", "APEX-CSE"))
    assert "Computer Science" in cse["programme_name"]
    assert cse["approved_intake"] in (120, 180)
    assert cse["academic_year"] == "2024-25"


def test_create_institution_rbac(tokens):
    """Verify only SYSTEM_ADMIN can register institutions."""
    import uuid
    code = f"NEW_{uuid.uuid4().hex[:6]}"
    payload = {
        "institution_code": code,
        "name": "New Technical Institute",
        "category": "ENGINEERING",
        "state": "Gujarat",
        "district": "Ahmedabad",
        "contact_email": f"{code.lower()}@gujarat.edu.in",
    }

    # Attempt as Institution Admin -> 403 Forbidden
    res_fail = client.post(
        "/api/v1/institutions",
        json=payload,
        headers={"Authorization": f"Bearer {tokens['apex']['token']}"},
    )
    assert res_fail.status_code == 403

    # Attempt as System Admin -> 201 Created
    res_ok = client.post(
        "/api/v1/institutions",
        json=payload,
        headers={"Authorization": f"Bearer {tokens['sysadmin']['token']}"},
    )
    assert res_ok.status_code == 201
    assert res_ok.json()["institution_code"] == code.upper()

