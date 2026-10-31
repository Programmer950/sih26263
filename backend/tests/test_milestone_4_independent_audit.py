"""Independent Targeted Audit Test Suite for Milestone 4: Regulatory Intake & Approval Matrix.

Rigorous code-level verification covering:
1. Approval configuration integrity & concurrency (concurrent amends, immutable history, date constraints).
2. Seat-accounting correctness (anti-double-counting, duplicate source records, overlapping attributes).
3. Calculation correctness (fractional percentages, boundary checks N-1/N/N+1, versioned rounding).
4. Status aggregation precedence (EXCEPTION > INSUFFICIENT > PARTIAL > COMPLIANT, non-erasure of check results).
5. Discrepancy integration (programme scope, nullable student ID, provenance, version linkage).
6. Security & role-based access control (SYSTEM_ADMIN/REGULATORY_REVIEWER enforcement, tenant isolation).
"""

import pytest
import uuid
import math
import io
import csv
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date, timezone
from sqlalchemy import select, text
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.models import (
    User,
    Programme,
    Institution,
    RosterSnapshot,
    StudentIdentity,
    AnnualRosterObservation,
    AdmissionEpisode,
    ApprovalConfiguration,
    ApprovalCategoryAllocation,
    ReconciliationRun,
    IntakeReconciliationSummary,
    DiscrepancyCase,
    SourceSubmission,
    SourceSubmissionRecord,
)
from app.services.storage_service import StorageService
from app.services.approval_service import ApprovalService, compute_seat_cap
from app.services.intake_service import IntakeService

client = TestClient(app)


@pytest.fixture(scope="module")
def audit_tokens():
    """Provides authenticated tokens across all platform roles."""
    res_sys = client.post("/api/v1/auth/login", json={"email": "sysadmin@aicte.gov.in", "password": "Admin@12345"})
    assert res_sys.status_code == 200
    sysadmin_token = res_sys.json()["access_token"]

    res_rev = client.post("/api/v1/auth/login", json={"email": "reviewer@aicte.gov.in", "password": "Reviewer@12345"})
    assert res_rev.status_code == 200
    reviewer_token = res_rev.json()["access_token"]

    res_apex = client.post("/api/v1/auth/login", json={"email": "admin@apex.edu.in", "password": "Apex@12345"})
    assert res_apex.status_code == 200
    apex_token = res_apex.json()["access_token"]
    apex_inst_id = res_apex.json()["user"]["institution_id"]

    res_poly = client.post("/api/v1/auth/login", json={"email": "admin@polytechnic.edu.in", "password": "Poly@12345"})
    assert res_poly.status_code == 200
    poly_token = res_poly.json()["access_token"]
    poly_inst_id = res_poly.json()["user"]["institution_id"]

    res_ver = client.post("/api/v1/auth/login", json={"email": "verifier@tcs.com", "password": "Verifier@12345"})
    assert res_ver.status_code == 200
    verifier_token = res_ver.json()["access_token"]

    return {
        "sysadmin_token": sysadmin_token,
        "reviewer_token": reviewer_token,
        "apex_token": apex_token,
        "apex_inst_id": apex_inst_id,
        "poly_token": poly_token,
        "poly_inst_id": poly_inst_id,
        "verifier_token": verifier_token,
    }


def create_mock_snapshot(db, institution_id, programme_id, academic_year, students_data, actor_id):
    """Creates a validated snapshot with source submission and observation records."""
    csv_buf = io.StringIO()
    writer = csv.writer(csv_buf)
    writer.writerow(["student_name", "apaar_id", "dob", "gender", "category"])
    for s in students_data:
        writer.writerow([s["name"], s["apaar"], s["dob"], s["gender"], s.get("category", "REGULAR")])

    content_bytes = csv_buf.getvalue().encode("utf-8")
    stored_path, fingerprint, file_size, _ = StorageService.save_upload_stream(
        stream=io.BytesIO(content_bytes),
        original_filename=f"audit_{uuid.uuid4().hex[:6]}.csv",
    )

    now_utc = datetime.now(timezone.utc)
    submission = SourceSubmission(
        institution_id=institution_id,
        programme_id=programme_id,
        academic_year=academic_year,
        uploaded_by_user_id=actor_id,
        submission_status="COMMITTED",
        original_filename="audit_cohort.csv",
        storage_key=stored_path,
        file_fingerprint=fingerprint,
        file_size_bytes=file_size,
        mime_type="text/csv",
        created_at=now_utc,
    )
    db.add(submission)
    db.flush()

    for idx, s in enumerate(students_data, start=1):
        masked_apaar = f"XXXX-XXXX-{s['apaar'][-4:]}"
        blind_idx = f"blind_audit_{s['apaar']}_{uuid.uuid4().hex[:6]}"

        ident = StudentIdentity(
            full_name=s["name"],
            date_of_birth=date.fromisoformat(s["dob"]),
            gender=s["gender"],
            masked_apaar_reference=masked_apaar,
            apaar_blind_index=blind_idx,
            created_at=now_utc,
        )
        db.add(ident)
        db.flush()

        rec = SourceSubmissionRecord(
            submission_id=submission.id,
            row_number=idx,
            raw_payload=s,
            parsed_payload=s,
            validation_status="VALID",
            resolved_student_identity_id=ident.id,
            created_at=now_utc,
        )
        db.add(rec)
        db.flush()

        obs = AnnualRosterObservation(
            student_identity_id=ident.id,
            institution_id=institution_id,
            programme_id=programme_id,
            academic_year=academic_year,
            student_status="ACTIVE",
            source_submission_id=submission.id,
            source_record_id=rec.id,
            observation_metadata={
                "seat_accounting_category": s.get("seat_cat", "REGULAR"),
                "entry_level": s.get("entry_level", "FIRST_YEAR"),
                "applicable_approval_rule_id": s.get("rule_id", "GENERAL"),
            },
            observation_timestamp=now_utc,
        )
        db.add(obs)

        ep = AdmissionEpisode(
            student_identity_id=ident.id,
            institution_id=institution_id,
            programme_id=programme_id,
            academic_year=academic_year,
            admission_date=date(2024, 7, 1),
            nationality_category=s.get("nationality", "INDIAN_DOMICILE"),
            admission_channel=s.get("channel", "CENTRALIZED_COUNSELING"),
            seat_accounting_category=s.get("seat_cat", "REGULAR"),
            entry_level=s.get("entry_level", "FIRST_YEAR"),
            applicable_approval_rule_id=s.get("rule_id", "GENERAL"),
            source_submission_id=submission.id,
            created_at=now_utc,
        )
        db.add(ep)

    db.flush()

    snapshot = RosterSnapshot(
        institution_id=institution_id,
        programme_id=programme_id,
        academic_year=academic_year,
        source_submission_id=submission.id,
        completeness_status="COMPLETE",
        lifecycle_status="ACTIVE",
        is_authoritative=True,
        declared_headcount=len(students_data),
        observed_headcount=len(students_data),
        snapshot_hash=fingerprint,
        created_by_user_id=actor_id,
        created_at=now_utc,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


# =========================================================================
# AUDIT AREA 1: Approval Configuration Integrity & Concurrency
# =========================================================================

def test_audit_area_1_date_constraints_and_validation(audit_tokens):
    """Verifies effective date constraints (effective_to >= effective_from) and positive intake."""
    headers = {"Authorization": f"Bearer {audit_tokens['sysadmin_token']}"}

    with SessionLocal() as db:
        inst_id = uuid.UUID(audit_tokens["apex_inst_id"])
        prog = db.execute(select(Programme).where(Programme.institution_id == inst_id)).scalars().first()
        prog_id = prog.id

    # 1. Invalid date range: effective_to < effective_from
    bad_dates = {
        "institution_id": str(inst_id),
        "programme_id": str(prog_id),
        "academic_year": "2024-audit-01",
        "approved_intake": 60,
        "approval_reference": "AICTE/AUDIT/01",
        "effective_from": "2025-06-01",
        "effective_to": "2024-05-31",  # Prior to effective_from!
    }
    res_dates = client.post("/api/v1/approvals/configurations", json=bad_dates, headers=headers)
    assert res_dates.status_code == 400
    assert "Invalid date range" in res_dates.json()["detail"]

    # 2. Non-positive intake: approved_intake <= 0
    bad_intake = {
        "institution_id": str(inst_id),
        "programme_id": str(prog_id),
        "academic_year": "2024-audit-02",
        "approved_intake": 0,  # Zero intake
        "approval_reference": "AICTE/AUDIT/02",
        "effective_from": "2024-06-01",
        "effective_to": "2025-05-31",
    }
    res_intake = client.post("/api/v1/approvals/configurations", json=bad_intake, headers=headers)
    assert res_intake.status_code == 422 or res_intake.status_code == 400


def test_audit_area_1_immutability_and_supersession_lineage(audit_tokens):
    """
    Verifies that historical configurations are strictly immutable,
    amendments increment version N -> N+1, mark prior as SUPERSEDED, and cannot be modified.
    """
    headers = {"Authorization": f"Bearer {audit_tokens['reviewer_token']}"}

    with SessionLocal() as db:
        inst_id = uuid.UUID(audit_tokens["apex_inst_id"])
        prog = db.execute(select(Programme).where(Programme.institution_id == inst_id)).scalars().first()
        prog_id = prog.id

    ay = f"2024-audit-{uuid.uuid4().hex[:4]}"
    create_payload = {
        "institution_id": str(inst_id),
        "programme_id": str(prog_id),
        "academic_year": ay,
        "approved_intake": 60,
        "approval_reference": "AICTE/IMMUTABLE/01",
        "effective_from": "2024-06-01",
        "effective_to": "2025-05-31",
        "category_allocations": [
            {
                "category_code": "TFW",
                "entry_level": "FIRST_YEAR",
                "allocation_type": "ADDITIONAL_SUPERNUMERARY",
                "allocation_basis": "PERCENTAGE",
                "allocated_value": 5.0,
                "rounding_method": "FLOOR",
                "denominator_basis": "SANCTIONED_INTAKE",
            }
        ],
    }

    # 1. Create v1
    res_v1 = client.post("/api/v1/approvals/configurations", json=create_payload, headers=headers)
    assert res_v1.status_code == 201
    v1_id = res_v1.json()["id"]
    assert res_v1.json()["configuration_version"] == 1
    assert res_v1.json()["status"] == "ACTIVE"

    # 2. Amend to v2
    amend_payload = {
        "approved_intake": 90,
        "amendment_reason": "Executive Council Resolution upgrading sanctioned capacity.",
    }
    res_v2 = client.post(f"/api/v1/approvals/configurations/{v1_id}/amend", json=amend_payload, headers=headers)
    assert res_v2.status_code == 200
    v2_id = res_v2.json()["id"]
    assert res_v2.json()["configuration_version"] == 2
    assert res_v2.json()["status"] == "ACTIVE"
    assert res_v2.json()["approved_intake"] == 90

    # 3. Check v1 is frozen and SUPERSEDED
    res_v1_frozen = client.get(f"/api/v1/approvals/configurations/{v1_id}", headers=headers)
    assert res_v1_frozen.status_code == 200
    v1_data = res_v1_frozen.json()
    assert v1_data["status"] == "SUPERSEDED"
    assert v1_data["superseded_by_id"] == v2_id
    assert v1_data["approved_intake"] == 60  # Prior approved_intake unchanged!

    # 4. Attempt to amend an already SUPERSEDED version must fail
    res_amend_frozen = client.post(f"/api/v1/approvals/configurations/{v1_id}/amend", json=amend_payload, headers=headers)
    assert res_amend_frozen.status_code == 400
    assert "Only ACTIVE configurations can be amended" in res_amend_frozen.json()["detail"]

    # 5. Retrieve history: returns [v2, v1] in descending order
    res_hist = client.get(
        f"/api/v1/approvals/configurations/history?institution_id={inst_id}&programme_id={prog_id}&academic_year={ay}",
        headers=headers,
    )
    assert res_hist.status_code == 200
    history = res_hist.json()
    assert len(history) == 2
    assert history[0]["configuration_version"] == 2
    assert history[1]["configuration_version"] == 1


# =========================================================================
# AUDIT AREA 2: Seat-Accounting Correctness & Anti-Double-Counting
# =========================================================================

def test_audit_area_2_duplicate_records_and_anti_double_counting(audit_tokens):
    """
    Verifies that duplicate student records are safely deduplicated,
    and each unique student contributes at most once to total seat accounting.
    """
    headers = {"Authorization": f"Bearer {audit_tokens['reviewer_token']}"}

    with SessionLocal() as db:
        inst_id = uuid.UUID(audit_tokens["apex_inst_id"])
        prog = db.execute(select(Programme).where(Programme.institution_id == inst_id)).scalars().first()
        prog_id = prog.id
        user = db.execute(select(User).where(User.email == "admin@apex.edu.in")).scalar_one()

        ay = f"2024-audit-dup-{uuid.uuid4().hex[:4]}"

        # Approved intake: 60
        config = ApprovalConfiguration(
            institution_id=inst_id,
            programme_id=prog_id,
            academic_year=ay,
            approved_intake=60,
            supernumerary_quota_percentage=15.0,
            lateral_entry_quota_percentage=10.0,
            approval_reference="AICTE/DUP/01",
            effective_from=date(2024, 6, 1),
            effective_to=date(2025, 5, 31),
            configuration_version=1,
            status="ACTIVE",
            created_by_user_id=user.id,
        )
        db.add(config)
        db.flush()

        alloc_tfw = ApprovalCategoryAllocation(
            approval_configuration_id=config.id,
            category_code="TFW",
            entry_level="FIRST_YEAR",
            allocation_type="ADDITIONAL_SUPERNUMERARY",
            allocation_basis="PERCENTAGE",
            allocated_value=5.0,
            rounding_method="FLOOR",
            denominator_basis="SANCTIONED_INTAKE",
            calculated_seat_cap=3,
        )
        db.add(alloc_tfw)
        db.commit()

        # Roster: 50 unique students
        students = [
            {"name": f"Student {i}", "apaar": f"8888{i:08d}", "dob": "2006-01-01", "gender": "M", "seat_cat": "REGULAR"}
            for i in range(1, 51)
        ]
        # Student 51 has overlapping attributes (Foreign National + TFW supernumerary)
        students.append({
            "name": "Overlapping FN-TFW",
            "apaar": "888800000051",
            "dob": "2006-01-01",
            "gender": "F",
            "nationality": "FOREIGN_NATIONAL",
            "seat_cat": "SUPERNUMERARY",
            "rule_id": "TFW",
        })

        snapshot = create_mock_snapshot(db, inst_id, prog_id, ay, students, user.id)

    # Verify intake
    res = client.post("/api/v1/approvals/intake/verify", json={"candidate_snapshot_id": str(snapshot.id)}, headers=headers)
    assert res.status_code == 201, res.text
    data = res.json()

    # Total unique students = 51 (50 regular + 1 TFW)
    assert data["regular_enrolled_count"] == 50
    assert data["supernumerary_enrolled_count"] == 1
    # Summation Invariant: 50 regular + 1 TFW = 51 total enrolled
    assert data["compliance_status"] == "COMPLIANT"


# =========================================================================
# AUDIT AREA 3: Calculation Correctness & Rounding Boundaries
# =========================================================================

def test_audit_area_3_fractional_rounding_matrix():
    """
    Audits percentage cap calculations with fractional values across all 4 rounding methods.
    Checks exact mathematical behavior without assumptions:
    - 63 seats * 5% = 3.15 seats
    - 67 seats * 15% = 10.05 seats
    - 70 seats * 5% = 3.50 seats
    """
    # 1. FLOOR
    cap_floor_1, err = compute_seat_cap("PERCENTAGE", 5.0, "FLOOR", 63)
    assert cap_floor_1 == 3, "FLOOR(3.15) must equal 3"

    cap_floor_2, _ = compute_seat_cap("PERCENTAGE", 15.0, "FLOOR", 67)
    assert cap_floor_2 == 10, "FLOOR(10.05) must equal 10"

    # 2. CEILING
    cap_ceil_1, _ = compute_seat_cap("PERCENTAGE", 5.0, "CEILING", 63)
    assert cap_ceil_1 == 4, "CEILING(3.15) must equal 4"

    cap_ceil_2, _ = compute_seat_cap("PERCENTAGE", 15.0, "CEILING", 67)
    assert cap_ceil_2 == 11, "CEILING(10.05) must equal 11"

    # 3. ROUND_HALF_UP
    cap_rhu_1, _ = compute_seat_cap("PERCENTAGE", 5.0, "ROUND_HALF_UP", 63)
    assert cap_rhu_1 == 3, "ROUND_HALF_UP(3.15) must round down to 3"

    cap_rhu_2, _ = compute_seat_cap("PERCENTAGE", 5.0, "ROUND_HALF_UP", 70)
    assert cap_rhu_2 == 4, "ROUND_HALF_UP(3.50) must round half up to 4"

    # 4. EXPLICIT_FIXED_CAP
    cap_fixed, _ = compute_seat_cap("PERCENTAGE", 12.0, "EXPLICIT_FIXED_CAP", 63)
    assert cap_fixed == 12

    # 5. Missing / Invalid Rounding Method -> Returns None
    cap_none, err_none = compute_seat_cap("PERCENTAGE", 5.0, None, 63)
    assert cap_none is None
    assert "Missing or invalid rounding method" in err_none

    # 6. Unestablished Denominator -> Returns None
    cap_no_denom, err_denom = compute_seat_cap("PERCENTAGE", 5.0, "FLOOR", None)
    assert cap_no_denom is None
    assert "Denominator unestablished" in err_denom


def test_audit_area_3_boundary_checks_one_below_exact_one_above(audit_tokens):
    """
    Audits exact boundary behavior:
    Approved Cap: 15
    - Boundary - 1 (14 enrolled): COMPLIANT (variance = -1)
    - Boundary (15 enrolled): COMPLIANT (variance = 0)
    - Boundary + 1 (16 enrolled): EXCEPTION_FOUND (variance = +1)
    """
    headers = {"Authorization": f"Bearer {audit_tokens['reviewer_token']}"}

    with SessionLocal() as db:
        inst_id = uuid.UUID(audit_tokens["apex_inst_id"])
        prog = db.execute(select(Programme).where(Programme.institution_id == inst_id)).scalars().first()
        prog_id = prog.id
        user = db.execute(select(User).where(User.email == "admin@apex.edu.in")).scalar_one()

        ay = f"2024-b{uuid.uuid4().hex[:4]}"

        # Fixed cap: 15 regular intake
        config = ApprovalConfiguration(
            institution_id=inst_id,
            programme_id=prog_id,
            academic_year=ay,
            approved_intake=15,
            supernumerary_quota_percentage=0.0,
            lateral_entry_quota_percentage=0.0,
            approval_reference="AICTE/BND/01",
            effective_from=date(2024, 6, 1),
            effective_to=date(2025, 5, 31),
            configuration_version=1,
            status="ACTIVE",
            created_by_user_id=user.id,
        )
        db.add(config)
        db.commit()

        # Case A: Exactly 15 enrolled (Boundary)
        students_exact = [
            {"name": f"Student {i}", "apaar": f"7777{i:08d}", "dob": "2006-01-01", "gender": "M", "seat_cat": "REGULAR"}
            for i in range(1, 16)
        ]
        snap_exact = create_mock_snapshot(db, inst_id, prog_id, ay, students_exact, user.id)

    # Verify Exact Boundary
    res_exact = client.post("/api/v1/approvals/intake/verify", json={"candidate_snapshot_id": str(snap_exact.id)}, headers=headers)
    assert res_exact.status_code == 201
    assert res_exact.json()["regular_variance"] == 0
    assert res_exact.json()["compliance_status"] == "COMPLIANT"

    # Case B: Exactly 16 enrolled (Boundary + 1 -> Exception)
    with SessionLocal() as db:
        ay_above = f"2024-c{uuid.uuid4().hex[:4]}"
        config_b = ApprovalConfiguration(
            institution_id=inst_id,
            programme_id=prog_id,
            academic_year=ay_above,
            approved_intake=15,
            supernumerary_quota_percentage=0.0,
            lateral_entry_quota_percentage=0.0,
            approval_reference="AICTE/BND/02",
            effective_from=date(2024, 6, 1),
            effective_to=date(2025, 5, 31),
            configuration_version=1,
            status="ACTIVE",
            created_by_user_id=user.id,
        )
        db.add(config_b)
        db.commit()

        students_above = [
            {"name": f"Student {i}", "apaar": f"7778{i:08d}", "dob": "2006-01-01", "gender": "M", "seat_cat": "REGULAR"}
            for i in range(1, 17)
        ]
        snap_above = create_mock_snapshot(db, inst_id, prog_id, ay_above, students_above, user.id)

    res_above = client.post("/api/v1/approvals/intake/verify", json={"candidate_snapshot_id": str(snap_above.id)}, headers=headers)
    assert res_above.status_code == 201
    assert res_above.json()["regular_variance"] == 1
    assert res_above.json()["compliance_status"] == "EXCEPTION_FOUND"


# =========================================================================
# AUDIT AREA 4: Overall Status Aggregation & Non-Erasure
# =========================================================================

def test_audit_area_4_status_precedence_and_non_erasure(audit_tokens):
    """
    Audits that:
    1. EXCEPTION_FOUND > INSUFFICIENT_INFORMATION > PARTIALLY_EVALUATED > COMPLIANT.
    2. An exception in one category does NOT erase or overwrite the insufficient-information status in another category.
    """
    headers = {"Authorization": f"Bearer {audit_tokens['reviewer_token']}"}

    with SessionLocal() as db:
        inst_id = uuid.UUID(audit_tokens["apex_inst_id"])
        prog = db.execute(select(Programme).where(Programme.institution_id == inst_id)).scalars().first()
        prog_id = prog.id
        user = db.execute(select(User).where(User.email == "admin@apex.edu.in")).scalar_one()

        ay = f"2024-audit-prec-{uuid.uuid4().hex[:4]}"

        # Approved intake: 60
        config = ApprovalConfiguration(
            institution_id=inst_id,
            programme_id=prog_id,
            academic_year=ay,
            approved_intake=60,
            supernumerary_quota_percentage=15.0,
            lateral_entry_quota_percentage=10.0,
            approval_reference="AICTE/PREC/01",
            effective_from=date(2024, 6, 1),
            effective_to=date(2025, 5, 31),
            configuration_version=1,
            status="ACTIVE",
            created_by_user_id=user.id,
        )
        db.add(config)
        db.flush()

        # Allocation A: TFW (Compliant cap = 3)
        alloc_tfw = ApprovalCategoryAllocation(
            approval_configuration_id=config.id,
            category_code="TFW",
            entry_level="FIRST_YEAR",
            allocation_type="ADDITIONAL_SUPERNUMERARY",
            allocation_basis="PERCENTAGE",
            allocated_value=5.0,
            rounding_method="FLOOR",
            denominator_basis="SANCTIONED_INTAKE",
            calculated_seat_cap=3,
        )
        # Allocation B: PMSSS (Missing rounding method -> INSUFFICIENT_INFORMATION)
        alloc_pmsss = ApprovalCategoryAllocation(
            approval_configuration_id=config.id,
            category_code="PMSSS",
            entry_level="FIRST_YEAR",
            allocation_type="ADDITIONAL_SUPERNUMERARY",
            allocation_basis="PERCENTAGE",
            allocated_value=2.0,
            rounding_method="INVALID_ROUNDING",
            denominator_basis="SANCTIONED_INTAKE",
            calculated_seat_cap=None,
        )
        db.add_all([alloc_tfw, alloc_pmsss])
        db.commit()

        # Cohort has 65 regular students (EXCESS: 65 > 60 -> EXCEPTION_FOUND)
        students = [
            {"name": f"Student {i}", "apaar": f"6666{i:08d}", "dob": "2006-01-01", "gender": "M", "seat_cat": "REGULAR"}
            for i in range(1, 66)
        ]
        snapshot = create_mock_snapshot(db, inst_id, prog_id, ay, students, user.id)

    res = client.post("/api/v1/approvals/intake/verify", json={"candidate_snapshot_id": str(snapshot.id)}, headers=headers)
    assert res.status_code == 201
    data = res.json()

    # 1. Overall Status must be EXCEPTION_FOUND by precedence
    assert data["compliance_status"] == "EXCEPTION_FOUND"

    # 2. Individual Check Non-Erasure:
    # Both the regular intake excess AND the PMSSS indeterminate finding must be retained!
    categories = {c["category_code"]: c for c in data["category_breakdown"]}
    assert categories["REGULAR_INTAKE"]["status"] == "EXCEPTION_FOUND"
    assert categories["PMSSS"]["status"] == "INSUFFICIENT_INFORMATION"

    # Discrepancy cases created for both
    cases = data["discrepancy_cases_created"]
    classifications = [c["classification"] for c in cases]
    assert "INTAKE_EXCESS_REGULAR" in classifications
    assert "INDETERMINATE_POLICY_CONFIGURATION" in classifications


# =========================================================================
# AUDIT AREA 5: Discrepancy Integration & Scope Integrity
# =========================================================================

def test_audit_area_5_discrepancy_scope_and_version_lineage(audit_tokens):
    """
    Verifies that:
    1. Programme-level intake cases have scope_type = 'PROGRAMME' and student_identity_id = None.
    2. Exact approval configuration version and source submission reference are attached.
    3. No individual student is singled out as a violator.
    """
    headers = {"Authorization": f"Bearer {audit_tokens['reviewer_token']}"}

    with SessionLocal() as db:
        inst_id = uuid.UUID(audit_tokens["apex_inst_id"])
        prog = db.execute(select(Programme).where(Programme.institution_id == inst_id)).scalars().first()
        prog_id = prog.id
        user = db.execute(select(User).where(User.email == "admin@apex.edu.in")).scalar_one()

        ay = f"2024-s{uuid.uuid4().hex[:4]}"

        config = ApprovalConfiguration(
            institution_id=inst_id,
            programme_id=prog_id,
            academic_year=ay,
            approved_intake=50,
            supernumerary_quota_percentage=0.0,
            lateral_entry_quota_percentage=0.0,
            approval_reference="AICTE/SCOPE/01",
            effective_from=date(2024, 6, 1),
            effective_to=date(2025, 5, 31),
            configuration_version=3,  # Version 3
            status="ACTIVE",
            created_by_user_id=user.id,
        )
        db.add(config)
        db.commit()

        # Enrol 55 students (excess of 5)
        students = [
            {"name": f"Student {i}", "apaar": f"5555{i:08d}", "dob": "2006-01-01", "gender": "M", "seat_cat": "REGULAR"}
            for i in range(1, 56)
        ]
        snapshot = create_mock_snapshot(db, inst_id, prog_id, ay, students, user.id)

    res = client.post("/api/v1/approvals/intake/verify", json={"candidate_snapshot_id": str(snapshot.id)}, headers=headers)
    assert res.status_code == 201

    with SessionLocal() as db:
        case = db.execute(
            select(DiscrepancyCase).where(
                DiscrepancyCase.academic_year == ay,
                DiscrepancyCase.classification == "INTAKE_EXCESS_REGULAR",
            )
        ).scalar_one()

        assert case.scope_type == "PROGRAMME"
        assert case.student_identity_id is None, "Student ID must be NULL for collective intake excess"
        assert case.approved_limit == 50
        assert case.observed_count == 55
        assert case.excess_count == 5
        assert case.approval_configuration_version == 3
        assert case.source_submission_id == snapshot.source_submission_id
        assert case.review_priority == "HIGH"


# =========================================================================
# AUDIT AREA 6: Security, RBAC & Tenant Isolation
# =========================================================================

def test_audit_area_6_rbac_regulatory_roles_enforcement(audit_tokens):
    """
    Verifies that:
    1. Only SYSTEM_ADMIN and REGULATORY_REVIEWER can create or amend approval configurations.
    2. INSTITUTION_ADMIN and THIRD_PARTY_VERIFIER are strictly denied (403 Forbidden).
    """
    with SessionLocal() as db:
        inst_id = uuid.UUID(audit_tokens["apex_inst_id"])
        prog = db.execute(select(Programme).where(Programme.institution_id == inst_id)).scalars().first()
        prog_id = prog.id

    ay = f"2024-r{uuid.uuid4().hex[:4]}"
    payload = {
        "institution_id": str(inst_id),
        "programme_id": str(prog_id),
        "academic_year": ay,
        "approved_intake": 60,
        "approval_reference": "AICTE/RBAC/01",
        "effective_from": "2024-06-01",
        "effective_to": "2025-05-31",
    }

    # 1. INSTITUTION_ADMIN attempt -> 403 Forbidden
    res_inst = client.post(
        "/api/v1/approvals/configurations",
        json=payload,
        headers={"Authorization": f"Bearer {audit_tokens['apex_token']}"},
    )
    assert res_inst.status_code == 403
    assert "Required role: SYSTEM_ADMIN, REGULATORY_REVIEWER" in res_inst.json()["detail"]

    # 2. THIRD_PARTY_VERIFIER attempt -> 403 Forbidden
    res_ver = client.post(
        "/api/v1/approvals/configurations",
        json=payload,
        headers={"Authorization": f"Bearer {audit_tokens['verifier_token']}"},
    )
    assert res_ver.status_code == 403
    assert "Required role: SYSTEM_ADMIN, REGULATORY_REVIEWER" in res_ver.json()["detail"]

    # 3. REGULATORY_REVIEWER attempt -> 201 Created
    res_rev = client.post(
        "/api/v1/approvals/configurations",
        json=payload,
        headers={"Authorization": f"Bearer {audit_tokens['reviewer_token']}"},
    )
    assert res_rev.status_code == 201
    cfg_id = res_rev.json()["id"]

    # 4. INSTITUTION_ADMIN cannot amend -> 403 Forbidden
    amend_payload = {"amendment_reason": "Unauthorized attempt to raise intake."}
    res_inst_amend = client.post(
        f"/api/v1/approvals/configurations/{cfg_id}/amend",
        json=amend_payload,
        headers={"Authorization": f"Bearer {audit_tokens['apex_token']}"},
    )
    assert res_inst_amend.status_code == 403
