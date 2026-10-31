"""Targeted Tests for Historical Aggregate-to-Roster Reconciliation (PRD Module 9)."""

import uuid
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.models import (
    User,
    Institution,
    Programme,
    SourceSubmission,
    RosterSnapshot,
)

client = TestClient(app)


def login(email, pwd):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    assert r.status_code == 200, f"Login failed for {email}: {r.text}"
    return r.json()["access_token"], r.json()["user"]["institution_id"]


@pytest.fixture(scope="module")
def agg_setup():
    token_apex, apex_inst_id = login("admin@apex.edu.in", "Apex@12345")
    token_poly, poly_inst_id = login("admin@polytechnic.edu.in", "Poly@12345")
    token_rev, _ = login("reviewer@aicte.gov.in", "Reviewer@12345")

    db = SessionLocal()
    apex = db.query(Institution).filter(Institution.id == uuid.UUID(apex_inst_id)).first()
    prog_cse = db.query(Programme).filter(Programme.institution_id == apex.id, Programme.programme_code == "CSE").first()
    user_apex = db.query(User).filter(User.email == "admin@apex.edu.in").first()

    rand_suffix = uuid.uuid4().hex[:6]
    now_utc = datetime.now(timezone.utc)
    # Create valid SourceSubmissions for FK
    sub_120 = SourceSubmission(
        institution_id=apex.id,
        programme_id=prog_cse.id,
        academic_year="2024-25",
        submission_type="ANNUAL_ROSTER",
        submission_status="COMMITTED",
        original_filename="apex_cse_2024_120.csv",
        storage_key=f"storage/apex_cse_120_{rand_suffix}.csv",
        file_fingerprint=f"abc1234567890abcdef1234567890abcdef1234567890abcdef1234567890{rand_suffix[:2]}",
        file_size_bytes=1024,
        uploaded_by_user_id=user_apex.id,
    )
    sub_116 = SourceSubmission(
        institution_id=apex.id,
        programme_id=prog_cse.id,
        academic_year="2024-25",
        submission_type="ANNUAL_ROSTER",
        submission_status="COMMITTED",
        original_filename="apex_cse_2024_116.csv",
        storage_key=f"storage/apex_cse_116_{rand_suffix}.csv",
        file_fingerprint=f"def1234567890abcdef1234567890abcdef1234567890abcdef1234567890{rand_suffix[:2]}",
        file_size_bytes=1024,
        uploaded_by_user_id=user_apex.id,
    )
    db.add(sub_120)
    db.add(sub_116)
    db.flush()

    # Create test snapshots
    snap_120 = RosterSnapshot(
        institution_id=apex.id,
        programme_id=prog_cse.id,
        academic_year="2024-25",
        source_submission_id=sub_120.id,
        observed_headcount=120,
        declared_headcount=120,
        snapshot_hash=f"abc1234567890abcdef1234567890abcdef1234567890abcdef1234567890{rand_suffix[:2]}",
        snapshot_metadata={"population_definition": "ALL_ENROLLED_REGULAR"},
        created_by_user_id=user_apex.id,
        is_authoritative=False,
        lifecycle_status="ACTIVE",
    )
    snap_116 = RosterSnapshot(
        institution_id=apex.id,
        programme_id=prog_cse.id,
        academic_year="2024-25",
        source_submission_id=sub_116.id,
        observed_headcount=116,
        declared_headcount=120,
        snapshot_hash=f"def1234567890abcdef1234567890abcdef1234567890abcdef1234567890{rand_suffix[:2]}",
        snapshot_metadata={"population_definition": "ALL_ENROLLED_REGULAR"},
        created_by_user_id=user_apex.id,
        is_authoritative=False,
        lifecycle_status="ACTIVE",
    )
    db.add(snap_120)
    db.add(snap_116)
    db.commit()
    db.refresh(snap_120)
    db.refresh(snap_116)

    context = {
        "apex_id": apex.id,
        "poly_id": uuid.UUID(poly_inst_id),
        "prog_id": prog_cse.id,
        "token_apex": token_apex,
        "token_poly": token_poly,
        "token_rev": token_rev,
        "snap_120_id": snap_120.id,
        "snap_116_id": snap_116.id,
    }
    db.close()
    return context


def test_create_and_list_aggregate_declaration(agg_setup):
    """Verifies declaration creation and listing with tenant boundaries."""
    token = agg_setup["token_apex"]
    payload = {
        "institution_id": str(agg_setup["apex_id"]),
        "programme_id": str(agg_setup["prog_id"]),
        "academic_year": "2024-25",
        "reporting_period": "ANNUAL_FINAL",
        "declared_count": 120,
        "population_definition": "ALL_ENROLLED_REGULAR",
        "student_status_definition": "ACTIVE_ON_ROLL",
        "counting_methodology": "HEADCOUNT",
        "reporting_source": "AICTE_MANDATORY_DISCLOSURE",
        "source_reference": "MD-2024-APEX-CSE-01",
    }
    res = client.post(
        "/api/v1/reconciliation/aggregate/declarations",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert res.status_code == 201
    decl = res.json()
    assert decl["declared_count"] == 120
    assert decl["source_reference"] == "MD-2024-APEX-CSE-01"

    # List declarations
    res_list = client.get(
        "/api/v1/reconciliation/aggregate/declarations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1


def test_reconcile_exact_match(agg_setup):
    """PRD Module 9: Declared 120 vs Snapshot 120 yields EXACT_MATCH and 0 variance."""
    token = agg_setup["token_apex"]
    decl_res = client.post(
        "/api/v1/reconciliation/aggregate/declarations",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "institution_id": str(agg_setup["apex_id"]),
            "programme_id": str(agg_setup["prog_id"]),
            "academic_year": "2024-25",
            "declared_count": 120,
        },
    )
    assert decl_res.status_code == 201
    decl_id = decl_res.json()["id"]

    rec_res = client.post(
        "/api/v1/reconciliation/aggregate/reconcile",
        headers={"Authorization": f"Bearer {token}"},
        json={"declaration_id": decl_id, "roster_snapshot_id": str(agg_setup["snap_120_id"])},
    )
    assert rec_res.status_code == 200
    data = rec_res.json()
    assert data["comparability_status"] == "COMPARABLE"
    assert data["variance"] == 0
    assert data["outcome_status"] == "EXACT_MATCH"
    assert data["discrepancy_case_id"] is None


def test_reconcile_declared_excess_variance(agg_setup):
    """PRD Module 9: Declared 120 vs Snapshot 116 yields DECLARED_EXCESS (-4 variance) and creates discrepancy case."""
    token = agg_setup["token_apex"]
    decl_res = client.post(
        "/api/v1/reconciliation/aggregate/declarations",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "institution_id": str(agg_setup["apex_id"]),
            "programme_id": str(agg_setup["prog_id"]),
            "academic_year": "2024-25",
            "declared_count": 120,
        },
    )
    assert decl_res.status_code == 201
    decl_id = decl_res.json()["id"]

    rec_res = client.post(
        "/api/v1/reconciliation/aggregate/reconcile",
        headers={"Authorization": f"Bearer {token}"},
        json={"declaration_id": decl_id, "roster_snapshot_id": str(agg_setup["snap_116_id"])},
    )
    assert rec_res.status_code == 200
    data = rec_res.json()
    assert data["comparability_status"] == "COMPARABLE"
    assert data["variance"] == -4
    assert data["outcome_status"] == "DECLARED_EXCESS"
    assert data["discrepancy_case_id"] is not None


def test_reconcile_roster_excess_variance(agg_setup):
    """PRD Module 9: Declared 110 vs Snapshot 116 yields ROSTER_EXCESS (+6 variance)."""
    token = agg_setup["token_apex"]
    decl_res = client.post(
        "/api/v1/reconciliation/aggregate/declarations",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "institution_id": str(agg_setup["apex_id"]),
            "programme_id": str(agg_setup["prog_id"]),
            "academic_year": "2024-25",
            "declared_count": 110,
        },
    )
    assert decl_res.status_code == 201
    decl_id = decl_res.json()["id"]

    rec_res = client.post(
        "/api/v1/reconciliation/aggregate/reconcile",
        headers={"Authorization": f"Bearer {token}"},
        json={"declaration_id": decl_id, "roster_snapshot_id": str(agg_setup["snap_116_id"])},
    )
    assert rec_res.status_code == 200
    data = rec_res.json()
    assert data["comparability_status"] == "COMPARABLE"
    assert data["variance"] == 6
    assert data["outcome_status"] == "ROSTER_EXCESS"


def test_reconcile_incomparable_population_definitions(agg_setup):
    """PRD Module 9: Incompatible population definition returns NON_COMPARABLE."""
    token = agg_setup["token_apex"]
    decl_res = client.post(
        "/api/v1/reconciliation/aggregate/declarations",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "institution_id": str(agg_setup["apex_id"]),
            "programme_id": str(agg_setup["prog_id"]),
            "academic_year": "2024-25",
            "declared_count": 100,
            "population_definition": "PART_TIME_ONLY",
        },
    )
    assert decl_res.status_code == 201
    decl_id = decl_res.json()["id"]

    rec_res = client.post(
        "/api/v1/reconciliation/aggregate/reconcile",
        headers={"Authorization": f"Bearer {token}"},
        json={"declaration_id": decl_id, "roster_snapshot_id": str(agg_setup["snap_120_id"])},
    )
    assert rec_res.status_code == 200
    data = rec_res.json()
    assert data["comparability_status"] == "NON_COMPARABLE"
    assert data["outcome_status"] == "INCOMPARABLE"
    assert "Population definition incompatible" in data["explanation"]


def test_reconcile_tenant_isolation_blocked(agg_setup):
    """Polytechnic Admin cannot reconcile Apex declarations or snapshots."""
    token_poly = agg_setup["token_poly"]
    decl_res = client.post(
        "/api/v1/reconciliation/aggregate/declarations",
        headers={"Authorization": f"Bearer {agg_setup['token_apex']}"},
        json={
            "institution_id": str(agg_setup["apex_id"]),
            "programme_id": str(agg_setup["prog_id"]),
            "academic_year": "2024-25",
            "declared_count": 120,
        },
    )
    assert decl_res.status_code == 201
    decl_id = decl_res.json()["id"]

    rec_res = client.post(
        "/api/v1/reconciliation/aggregate/reconcile",
        headers={"Authorization": f"Bearer {token_poly}"},
        json={"declaration_id": decl_id, "roster_snapshot_id": str(agg_setup["snap_120_id"])},
    )
    assert rec_res.status_code == 403


def test_reconcile_missing_declaration_returns_404(agg_setup):
    """Missing declaration returns 404."""
    fake_id = str(uuid.uuid4())
    res = client.post(
        "/api/v1/reconciliation/aggregate/reconcile",
        headers={"Authorization": f"Bearer {agg_setup['token_rev']}"},
        json={"declaration_id": fake_id, "roster_snapshot_id": str(agg_setup["snap_120_id"])},
    )
    assert res.status_code == 404
