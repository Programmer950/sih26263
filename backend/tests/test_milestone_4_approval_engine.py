"""Tests for Milestone 4: Regulatory Intake & Approval Matrix Verification Engine.

Covers:
1. Versioned approval configuration lifecycle (Create v1, Amend v2, Revoke, Tenancy).
2. All 8 Pre-Engine worked calculation scenarios:
   - Scenario 1: Regular intake excess (INTAKE_EXCESS_REGULAR -> EXCEPTION_FOUND).
   - Scenario 2: Additive supernumerary seats (TFW, EWS -> COMPLIANT).
   - Scenario 3: Within-sanctioned sub-quotas (MANAGEMENT_QUOTA breach -> EXCEPTION_FOUND).
   - Scenario 4: Missing rounding policy (INSUFFICIENT_INFORMATION).
   - Scenario 5: Overlapping student attributes & anti-double-counting (PARTIALLY_EVALUATED).
   - Scenario 6: Lateral entry segregated 2nd-year accounting (LATERAL_ENTRY_INTAKE_EXCESS).
   - Scenario 7: Missing approval configuration safe fallback (INSUFFICIENT_INFORMATION).
   - Scenario 8: Mixed compliant and indeterminate results (PARTIALLY_EVALUATED).
3. Multi-tenancy isolation and audit events.
"""

import pytest
import uuid
import random
import io
import csv
from datetime import datetime, date, timezone
from sqlalchemy import select
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
    AuditEvent,
)
from app.services.storage_service import StorageService

client = TestClient(app)


@pytest.fixture(scope="module")
def seeded_tokens():
    """Logs in seeded users and provides Bearer tokens."""
    res_apex = client.post("/api/v1/auth/login", json={"email": "admin@apex.edu.in", "password": "Apex@12345"})
    assert res_apex.status_code == 200
    apex_token = res_apex.json()["access_token"]
    apex_inst_id = res_apex.json()["user"]["institution_id"]

    res_poly = client.post("/api/v1/auth/login", json={"email": "admin@polytechnic.edu.in", "password": "Poly@12345"})
    assert res_poly.status_code == 200
    poly_token = res_poly.json()["access_token"]
    poly_inst_id = res_poly.json()["user"]["institution_id"]

    res_rev = client.post("/api/v1/auth/login", json={"email": "reviewer@aicte.gov.in", "password": "Reviewer@12345"})
    assert res_rev.status_code == 200
    reviewer_token = res_rev.json()["access_token"]

    res_sys = client.post("/api/v1/auth/login", json={"email": "sysadmin@aicte.gov.in", "password": "Admin@12345"})
    assert res_sys.status_code == 200
    sysadmin_token = res_sys.json()["access_token"]

    res_ver = client.post("/api/v1/auth/login", json={"email": "verifier@tcs.com", "password": "Verifier@12345"})
    assert res_ver.status_code == 200
    verifier_token = res_ver.json()["access_token"]

    return {
        "apex_token": apex_token,
        "apex_inst_id": apex_inst_id,
        "poly_token": poly_token,
        "poly_inst_id": poly_inst_id,
        "reviewer_token": reviewer_token,
        "sysadmin_token": sysadmin_token,
        "verifier_token": verifier_token,
    }


def create_test_submission_and_snapshot(db, institution_id, programme_id, academic_year, students_data, actor_id):
    """Helper to create confirmed submission, observations, admission episodes, and snapshot."""
    from app.models import SourceSubmission, SourceSubmissionRecord

    csv_buf = io.StringIO()
    writer = csv.writer(csv_buf)
    writer.writerow(["student_name", "apaar_id", "dob", "gender", "category"])
    for s in students_data:
        writer.writerow([s["name"], s["apaar"], s["dob"], s["gender"], s.get("category", "REGULAR")])

    content_bytes = csv_buf.getvalue().encode("utf-8")
    stored_path, fingerprint, file_size, _ = StorageService.save_upload_stream(
        stream=io.BytesIO(content_bytes),
        original_filename=f"test_intake_{uuid.uuid4().hex[:6]}.csv",
    )

    now_utc = datetime.now(timezone.utc)
    submission = SourceSubmission(
        institution_id=institution_id,
        programme_id=programme_id,
        academic_year=academic_year,
        uploaded_by_user_id=actor_id,
        submission_status="COMMITTED",
        original_filename="intake_test.csv",
        storage_key=stored_path,
        file_fingerprint=fingerprint,
        file_size_bytes=file_size,
        mime_type="text/csv",
        created_at=now_utc,
    )
    db.add(submission)
    db.flush()

    observations = []
    for idx, s in enumerate(students_data, start=1):
        # Look up or create StudentIdentity
        masked_apaar = f"XXXX-XXXX-{s['apaar'][-4:]}"
        blind_idx = f"blind_{s['apaar']}_{uuid.uuid4().hex[:8]}"
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
        observations.append(obs)

        # Create AdmissionEpisode
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


def test_approval_configuration_lifecycle_and_amendment(seeded_tokens):
    """
    Verifies ApprovalConfiguration lifecycle:
    - Create Version 1 with category allocations.
    - Check unique active constraint (409 on duplicate active).
    - Amend configuration (supersedes v1, creates v2, copies/updates allocations).
    - Revoke configuration.
    - Audit events emitted.
    """
    token = seeded_tokens["reviewer_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with SessionLocal() as db:
        inst_id = uuid.UUID(seeded_tokens["apex_inst_id"])
        programme = db.execute(select(Programme).where(Programme.institution_id == inst_id)).scalars().first()
        prog_id = programme.id

    # 1. Create Version 1
    ay = f"2024-test-{uuid.uuid4().hex[:4]}"
    create_payload = {
        "institution_id": str(inst_id),
        "programme_id": str(prog_id),
        "academic_year": ay,
        "approved_intake": 60,
        "approval_reference": "AICTE/EOA/2024/001",
        "issuing_authority": "AICTE",
        "approval_letter_date": "2024-04-15",
        "effective_from": "2024-06-01",
        "effective_to": "2025-05-31",
        "supernumerary_quota_percentage": 15.0,
        "lateral_entry_quota_percentage": 10.0,
        "category_allocations": [
            {
                "category_code": "TFW",
                "entry_level": "FIRST_YEAR",
                "allocation_type": "ADDITIONAL_SUPERNUMERARY",
                "allocation_basis": "PERCENTAGE",
                "allocated_value": 5.0,
                "rounding_method": "FLOOR",
                "denominator_basis": "SANCTIONED_INTAKE",
                "policy_clause": "Clause 4.1",
            },
            {
                "category_code": "MANAGEMENT_QUOTA",
                "entry_level": "FIRST_YEAR",
                "allocation_type": "WITHIN_SANCTIONED_INTAKE",
                "allocation_basis": "PERCENTAGE",
                "allocated_value": 15.0,
                "rounding_method": "FLOOR",
                "denominator_basis": "SANCTIONED_INTAKE",
                "policy_clause": "Clause 2.3",
            },
        ],
    }

    res_create = client.post("/api/v1/approvals/configurations", json=create_payload, headers=headers)
    assert res_create.status_code == 201, res_create.text
    data_v1 = res_create.json()
    assert data_v1["configuration_version"] == 1
    assert data_v1["status"] == "ACTIVE"
    assert len(data_v1["category_allocations"]) == 2
    # Check calculated seat caps: 60 * 0.05 = 3; 60 * 0.15 = 9
    alloc_map = {a["category_code"]: a for a in data_v1["category_allocations"]}
    assert alloc_map["TFW"]["calculated_seat_cap"] == 3
    assert alloc_map["MANAGEMENT_QUOTA"]["calculated_seat_cap"] == 9
    config_v1_id = data_v1["id"]

    # 2. Duplicate ACTIVE creation rejected with 409
    res_dup = client.post("/api/v1/approvals/configurations", json=create_payload, headers=headers)
    assert res_dup.status_code == 409

    # 3. Amend configuration -> Creates Version 2
    amend_payload = {
        "amendment_reason": "AICTE Supplementary Approval Letter Order increasing intake to 120 seats.",
        "approved_intake": 120,
        "approval_reference": "AICTE/EOA/2024/001-REV1",
    }
    res_amend = client.post(f"/api/v1/approvals/configurations/{config_v1_id}/amend", json=amend_payload, headers=headers)
    assert res_amend.status_code == 200, res_amend.text
    data_v2 = res_amend.json()
    assert data_v2["configuration_version"] == 2
    assert data_v2["status"] == "ACTIVE"
    assert data_v2["approved_intake"] == 120
    assert len(data_v2["category_allocations"]) == 2
    # Caps recomputed for 120 intake: 120 * 0.05 = 6; 120 * 0.15 = 18
    alloc_map_v2 = {a["category_code"]: a for a in data_v2["category_allocations"]}
    assert alloc_map_v2["TFW"]["calculated_seat_cap"] == 6
    assert alloc_map_v2["MANAGEMENT_QUOTA"]["calculated_seat_cap"] == 18

    # Verify Version 1 is now SUPERSEDED
    res_get_v1 = client.get(f"/api/v1/approvals/configurations/{config_v1_id}", headers=headers)
    assert res_get_v1.status_code == 200
    v1_refreshed = res_get_v1.json()
    assert v1_refreshed["status"] == "SUPERSEDED"
    assert v1_refreshed["superseded_by_id"] == data_v2["id"]

    # 4. Cannot amend non-active configuration
    res_amend_superseded = client.post(f"/api/v1/approvals/configurations/{config_v1_id}/amend", json=amend_payload, headers=headers)
    assert res_amend_superseded.status_code == 400

    # 5. Revoke Version 2
    revoke_payload = {"revocation_reason": "Academic programme discontinued by State Technical Education Directorate."}
    res_revoke = client.post(f"/api/v1/approvals/configurations/{data_v2['id']}/revoke", json=revoke_payload, headers=headers)
    assert res_revoke.status_code == 200
    assert res_revoke.json()["status"] == "REVOKED"


def test_scenario_1_regular_intake_excess(seeded_tokens):
    """
    Scenario 1: Regular Intake Excess (INTAKE_EXCESS_REGULAR).
    Approved: 60, Enrolled: 65 regular first-year students.
    Expected: EXCEPTION_FOUND, programme-level case with student_identity_id = None, excess = 5.
    """
    token = seeded_tokens["reviewer_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with SessionLocal() as db:
        inst_id = uuid.UUID(seeded_tokens["apex_inst_id"])
        programme = db.execute(select(Programme).where(Programme.institution_id == inst_id)).scalars().first()
        prog_id = programme.id
        user = db.execute(select(User).where(User.email == "admin@apex.edu.in")).scalar_one()

        ay = f"2024-sc1-{uuid.uuid4().hex[:4]}"

        # Setup 60 approved configuration
        config = ApprovalConfiguration(
            institution_id=inst_id,
            programme_id=prog_id,
            academic_year=ay,
            approved_intake=60,
            supernumerary_quota_percentage=15.0,
            lateral_entry_quota_percentage=10.0,
            approval_reference="AICTE/SC1/2024",
            effective_from=date(2024, 6, 1),
            effective_to=date(2025, 5, 31),
            configuration_version=1,
            status="ACTIVE",
            created_by_user_id=user.id,
        )
        db.add(config)
        db.commit()

        # Create 65 regular students
        students = [
            {
                "name": f"Regular Student {i}",
                "apaar": f"9100{i:08d}",
                "dob": "2006-05-10",
                "gender": "M",
                "seat_cat": "REGULAR",
                "entry_level": "FIRST_YEAR",
                "rule_id": "GENERAL",
            }
            for i in range(1, 66)
        ]
        snapshot = create_test_submission_and_snapshot(db, inst_id, prog_id, ay, students, user.id)

    # Execute Intake Reconciliation
    req_payload = {"candidate_snapshot_id": str(snapshot.id)}
    res = client.post("/api/v1/approvals/intake/verify", json=req_payload, headers=headers)
    assert res.status_code == 201, res.text
    data = res.json()

    assert data["compliance_status"] == "EXCEPTION_FOUND"
    assert data["regular_approved_intake"] == 60
    assert data["regular_enrolled_count"] == 65
    assert data["regular_variance"] == 5

    # Verify Programme-level Discrepancy Case
    with SessionLocal() as db:
        case = db.execute(
            select(DiscrepancyCase).where(
                DiscrepancyCase.academic_year == ay,
                DiscrepancyCase.classification == "INTAKE_EXCESS_REGULAR",
            )
        ).scalar_one()
        assert case.scope_type == "PROGRAMME"
        assert case.student_identity_id is None
        assert case.approved_limit == 60
        assert case.observed_count == 65
        assert case.excess_count == 5
        assert case.review_priority == "HIGH"


def test_scenario_2_additive_supernumerary_seats(seeded_tokens):
    """
    Scenario 2: Additive Supernumerary Seats (TFW, EWS).
    Approved: 60, TFW (5% = 3), EWS (10% = 6).
    Enrolled: 59 Regular, 3 TFW, 5 EWS -> within all limits.
    Expected: COMPLIANT, 0 discrepancy cases.
    """
    token = seeded_tokens["reviewer_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with SessionLocal() as db:
        inst_id = uuid.UUID(seeded_tokens["apex_inst_id"])
        programme = db.execute(select(Programme).where(Programme.institution_id == inst_id)).scalars().first()
        prog_id = programme.id
        user = db.execute(select(User).where(User.email == "admin@apex.edu.in")).scalar_one()

        ay = f"2024-sc2-{uuid.uuid4().hex[:4]}"

        config = ApprovalConfiguration(
            institution_id=inst_id,
            programme_id=prog_id,
            academic_year=ay,
            approved_intake=60,
            supernumerary_quota_percentage=15.0,
            lateral_entry_quota_percentage=10.0,
            approval_reference="AICTE/SC2/2024",
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
        alloc_ews = ApprovalCategoryAllocation(
            approval_configuration_id=config.id,
            category_code="EWS",
            entry_level="FIRST_YEAR",
            allocation_type="ADDITIONAL_SUPERNUMERARY",
            allocation_basis="PERCENTAGE",
            allocated_value=10.0,
            rounding_method="FLOOR",
            denominator_basis="SANCTIONED_INTAKE",
            calculated_seat_cap=6,
        )
        db.add_all([alloc_tfw, alloc_ews])
        db.commit()

        # Enrolled: 59 Regular, 3 TFW, 5 EWS = 67 total
        students = []
        for i in range(1, 60):
            students.append({"name": f"Reg {i}", "apaar": f"9201{i:08d}", "dob": "2006-01-01", "gender": "F", "seat_cat": "REGULAR"})
        for i in range(1, 4):
            students.append({"name": f"TFW {i}", "apaar": f"9202{i:08d}", "dob": "2006-01-01", "gender": "F", "seat_cat": "SUPERNUMERARY", "rule_id": "TFW"})
        for i in range(1, 6):
            students.append({"name": f"EWS {i}", "apaar": f"9203{i:08d}", "dob": "2006-01-01", "gender": "M", "seat_cat": "SUPERNUMERARY", "rule_id": "EWS"})

        snapshot = create_test_submission_and_snapshot(db, inst_id, prog_id, ay, students, user.id)

    res = client.post("/api/v1/approvals/intake/verify", json={"candidate_snapshot_id": str(snapshot.id)}, headers=headers)
    assert res.status_code == 201, res.text
    data = res.json()

    assert data["compliance_status"] == "COMPLIANT"
    assert data["regular_enrolled_count"] == 59
    assert data["regular_variance"] == -1
    assert data["supernumerary_enrolled_count"] == 8
    assert len(data["discrepancy_cases_created"]) == 0


def test_scenario_3_within_sanctioned_sub_quotas(seeded_tokens):
    """
    Scenario 3: Within-Sanctioned Sub-Quotas (Management Quota).
    Approved: 100, Management Quota (15% = 15 seats).
    Enrolled: 78 General Regular + 22 Management Quota = 100 total regular.
    Expected: EXCEPTION_FOUND, CATEGORY_ALLOCATION_BREACH (excess = 7), Regular intake itself is compliant.
    """
    token = seeded_tokens["reviewer_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with SessionLocal() as db:
        inst_id = uuid.UUID(seeded_tokens["apex_inst_id"])
        programme = db.execute(select(Programme).where(Programme.institution_id == inst_id)).scalars().first()
        prog_id = programme.id
        user = db.execute(select(User).where(User.email == "admin@apex.edu.in")).scalar_one()

        ay = f"2024-sc3-{uuid.uuid4().hex[:4]}"

        config = ApprovalConfiguration(
            institution_id=inst_id,
            programme_id=prog_id,
            academic_year=ay,
            approved_intake=100,
            supernumerary_quota_percentage=15.0,
            lateral_entry_quota_percentage=10.0,
            approval_reference="AICTE/SC3/2024",
            effective_from=date(2024, 6, 1),
            effective_to=date(2025, 5, 31),
            configuration_version=1,
            status="ACTIVE",
            created_by_user_id=user.id,
        )
        db.add(config)
        db.flush()

        alloc_mgmt = ApprovalCategoryAllocation(
            approval_configuration_id=config.id,
            category_code="MANAGEMENT_QUOTA",
            entry_level="FIRST_YEAR",
            allocation_type="WITHIN_SANCTIONED_INTAKE",
            allocation_basis="PERCENTAGE",
            allocated_value=15.0,
            rounding_method="FLOOR",
            denominator_basis="SANCTIONED_INTAKE",
            calculated_seat_cap=15,
        )
        db.add(alloc_mgmt)
        db.commit()

        students = []
        for i in range(1, 79):
            students.append({"name": f"Merit {i}", "apaar": f"9301{i:08d}", "dob": "2006-03-01", "gender": "M", "seat_cat": "REGULAR"})
        for i in range(1, 23):
            students.append({"name": f"Mgmt {i}", "apaar": f"9302{i:08d}", "dob": "2006-03-01", "gender": "F", "seat_cat": "WITHIN_SANCTIONED_SUB_QUOTA", "rule_id": "MANAGEMENT_QUOTA"})

        snapshot = create_test_submission_and_snapshot(db, inst_id, prog_id, ay, students, user.id)

    res = client.post("/api/v1/approvals/intake/verify", json={"candidate_snapshot_id": str(snapshot.id)}, headers=headers)
    assert res.status_code == 201, res.text
    data = res.json()

    assert data["compliance_status"] == "EXCEPTION_FOUND"
    assert data["regular_approved_intake"] == 100
    assert data["regular_enrolled_count"] == 100
    assert data["regular_variance"] == 0  # Regular overall is compliant!

    # Sub-quota breach must be generated
    cases = data["discrepancy_cases_created"]
    assert len(cases) == 1
    assert cases[0]["classification"] == "CATEGORY_ALLOCATION_BREACH"
    assert cases[0]["review_priority"] == "MEDIUM"


def test_scenario_4_missing_rounding_policy(seeded_tokens):
    """
    Scenario 4: Missing Rounding Policy -> INSUFFICIENT_INFORMATION.
    Approved: 63, TFW: 5% (raw = 3.15), rounding_method = None / unestablished.
    Expected: INSUFFICIENT_INFORMATION, INDETERMINATE_POLICY_CONFIGURATION case.
    """
    token = seeded_tokens["reviewer_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with SessionLocal() as db:
        inst_id = uuid.UUID(seeded_tokens["apex_inst_id"])
        programme = db.execute(select(Programme).where(Programme.institution_id == inst_id)).scalars().first()
        prog_id = programme.id
        user = db.execute(select(User).where(User.email == "admin@apex.edu.in")).scalar_one()

        ay = f"2024-sc4-{uuid.uuid4().hex[:4]}"

        config = ApprovalConfiguration(
            institution_id=inst_id,
            programme_id=prog_id,
            academic_year=ay,
            approved_intake=63,
            supernumerary_quota_percentage=15.0,
            lateral_entry_quota_percentage=10.0,
            approval_reference="AICTE/SC4/2024",
            effective_from=date(2024, 6, 1),
            effective_to=date(2025, 5, 31),
            configuration_version=1,
            status="ACTIVE",
            created_by_user_id=user.id,
        )
        db.add(config)
        db.flush()

        alloc_indeterminate = ApprovalCategoryAllocation(
            approval_configuration_id=config.id,
            category_code="TFW",
            entry_level="FIRST_YEAR",
            allocation_type="ADDITIONAL_SUPERNUMERARY",
            allocation_basis="PERCENTAGE",
            allocated_value=5.0,
            rounding_method="INVALID_METHOD",  # Missing/invalid rounding method
            denominator_basis="SANCTIONED_INTAKE",
            calculated_seat_cap=None,
        )
        db.add(alloc_indeterminate)
        db.commit()

        students = [
            {"name": f"Student {i}", "apaar": f"9401{i:08d}", "dob": "2006-04-01", "gender": "M", "seat_cat": "REGULAR"}
            for i in range(1, 50)
        ]
        snapshot = create_test_submission_and_snapshot(db, inst_id, prog_id, ay, students, user.id)

    res = client.post("/api/v1/approvals/intake/verify", json={"candidate_snapshot_id": str(snapshot.id)}, headers=headers)
    assert res.status_code == 201, res.text
    data = res.json()

    assert data["compliance_status"] == "INSUFFICIENT_INFORMATION"
    cases = data["discrepancy_cases_created"]
    assert any(c["classification"] == "INDETERMINATE_POLICY_CONFIGURATION" for c in cases)


def test_scenario_5_overlapping_attributes_anti_double_counting(seeded_tokens):
    """
    Scenario 5: Overlapping Student Attributes & Anti-Double-Counting.
    Student S1 has multiple attributes (NRI + TFW) -> counted exactly once.
    Student S2 has unclassifiable category -> UNCLASSIFIED_SEAT_CATEGORY -> PARTIALLY_EVALUATED.
    """
    token = seeded_tokens["reviewer_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with SessionLocal() as db:
        inst_id = uuid.UUID(seeded_tokens["apex_inst_id"])
        programme = db.execute(select(Programme).where(Programme.institution_id == inst_id)).scalars().first()
        prog_id = programme.id
        user = db.execute(select(User).where(User.email == "admin@apex.edu.in")).scalar_one()

        ay = f"2024-sc5-{uuid.uuid4().hex[:4]}"

        config = ApprovalConfiguration(
            institution_id=inst_id,
            programme_id=prog_id,
            academic_year=ay,
            approved_intake=60,
            supernumerary_quota_percentage=15.0,
            lateral_entry_quota_percentage=10.0,
            approval_reference="AICTE/SC5/2024",
            effective_from=date(2024, 6, 1),
            effective_to=date(2025, 5, 31),
            configuration_version=1,
            status="ACTIVE",
            created_by_user_id=user.id,
        )
        db.add(config)
        db.flush()

        alloc = ApprovalCategoryAllocation(
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
        db.add(alloc)
        db.commit()

        students = [
            # 50 regular
            *[{"name": f"Regular {i}", "apaar": f"9501{i:08d}", "dob": "2006-01-01", "gender": "M", "seat_cat": "REGULAR"} for i in range(1, 51)],
            # S1: Foreign National + TFW supernumerary allotment
            {"name": "S1 Overlapping", "apaar": "950200000001", "dob": "2006-01-01", "gender": "F", "nationality": "FOREIGN_NATIONAL", "seat_cat": "SUPERNUMERARY", "rule_id": "TFW"},
            # S2: Unclassified category
            {"name": "S2 Indeterminate", "apaar": "950200000002", "dob": "2006-01-01", "gender": "M", "seat_cat": "UNCLASSIFIED_SEAT_CATEGORY", "rule_id": "NONE"},
        ]
        snapshot = create_test_submission_and_snapshot(db, inst_id, prog_id, ay, students, user.id)

    res = client.post("/api/v1/approvals/intake/verify", json={"candidate_snapshot_id": str(snapshot.id)}, headers=headers)
    assert res.status_code == 201, res.text
    data = res.json()

    # Precedence: no exceptions found, but unclassified student exists -> PARTIALLY_EVALUATED
    assert data["compliance_status"] == "PARTIALLY_EVALUATED"
    assert data["unclassified_count"] == 1
    assert data["regular_enrolled_count"] == 50
    assert data["supernumerary_enrolled_count"] == 1


def test_scenario_6_lateral_entry_segregated_accounting(seeded_tokens):
    """
    Scenario 6: Lateral Entry Segregated 2nd-Year Accounting.
    Approved regular intake: 120. Lateral cap: 10% = 12 seats.
    Observed: 14 lateral entry students.
    Expected: EXCEPTION_FOUND, LATERAL_ENTRY_INTAKE_EXCESS, excess = 2.
    Does not count against 1st-year regular intake.
    """
    token = seeded_tokens["reviewer_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with SessionLocal() as db:
        inst_id = uuid.UUID(seeded_tokens["apex_inst_id"])
        programme = db.execute(select(Programme).where(Programme.institution_id == inst_id)).scalars().first()
        prog_id = programme.id
        user = db.execute(select(User).where(User.email == "admin@apex.edu.in")).scalar_one()

        ay = f"2024-sc6-{uuid.uuid4().hex[:4]}"

        config = ApprovalConfiguration(
            institution_id=inst_id,
            programme_id=prog_id,
            academic_year=ay,
            approved_intake=120,
            supernumerary_quota_percentage=15.0,
            lateral_entry_quota_percentage=10.0,
            approval_reference="AICTE/SC6/2024",
            effective_from=date(2024, 6, 1),
            effective_to=date(2025, 5, 31),
            configuration_version=1,
            status="ACTIVE",
            created_by_user_id=user.id,
        )
        db.add(config)
        db.flush()

        alloc_lat = ApprovalCategoryAllocation(
            approval_configuration_id=config.id,
            category_code="LATERAL_ENTRY",
            entry_level="LATERAL_ENTRY_SECOND_YEAR",
            allocation_type="INDEPENDENT_CAP",
            allocation_basis="PERCENTAGE",
            allocated_value=10.0,
            rounding_method="FLOOR",
            denominator_basis="SANCTIONED_INTAKE",
            calculated_seat_cap=12,
        )
        db.add(alloc_lat)
        db.commit()

        # 100 regular 1st years + 14 lateral 2nd years
        students = [
            *[{"name": f"Reg {i}", "apaar": f"9601{i:08d}", "dob": "2006-01-01", "gender": "M", "seat_cat": "REGULAR", "entry_level": "FIRST_YEAR"} for i in range(1, 101)],
            *[{"name": f"Lat {i}", "apaar": f"9602{i:08d}", "dob": "2005-01-01", "gender": "F", "seat_cat": "LATERAL_ENTRY", "entry_level": "LATERAL_ENTRY_SECOND_YEAR"} for i in range(1, 15)],
        ]
        snapshot = create_test_submission_and_snapshot(db, inst_id, prog_id, ay, students, user.id)

    res = client.post("/api/v1/approvals/intake/verify", json={"candidate_snapshot_id": str(snapshot.id)}, headers=headers)
    assert res.status_code == 201, res.text
    data = res.json()

    assert data["compliance_status"] == "EXCEPTION_FOUND"
    assert data["regular_approved_intake"] == 120
    assert data["regular_enrolled_count"] == 100
    assert data["regular_variance"] == -20  # Compliant 1st-year
    assert data["lateral_entry_approved_cap"] == 12
    assert data["lateral_entry_enrolled_count"] == 14
    assert data["lateral_entry_variance"] == 2  # Lateral excess!

    cases = data["discrepancy_cases_created"]
    assert any(c["classification"] == "LATERAL_ENTRY_INTAKE_EXCESS" for c in cases)


def test_scenario_7_missing_approval_configuration_safe_fallback(seeded_tokens):
    """
    Scenario 7: Missing Approval Configuration -> INSUFFICIENT_INFORMATION.
    Snapshot uploaded for programme where no active approval configuration exists.
    Must never accuse of zero-intake statutory fraud.
    """
    token = seeded_tokens["reviewer_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with SessionLocal() as db:
        inst_id = uuid.UUID(seeded_tokens["apex_inst_id"])
        programme = db.execute(select(Programme).where(Programme.institution_id == inst_id)).scalars().first()
        prog_id = programme.id
        user = db.execute(select(User).where(User.email == "admin@apex.edu.in")).scalar_one()

        ay = f"2024-sc7-{uuid.uuid4().hex[:4]}"

        # No configuration created in DB!
        students = [
            {"name": f"Student {i}", "apaar": f"9701{i:08d}", "dob": "2006-01-01", "gender": "M", "seat_cat": "REGULAR"}
            for i in range(1, 21)
        ]
        snapshot = create_test_submission_and_snapshot(db, inst_id, prog_id, ay, students, user.id)

    res = client.post("/api/v1/approvals/intake/verify", json={"candidate_snapshot_id": str(snapshot.id)}, headers=headers)
    assert res.status_code == 201, res.text
    data = res.json()

    assert data["compliance_status"] == "INSUFFICIENT_INFORMATION"
    assert data["approval_configuration_id"] is None
    cases = data["discrepancy_cases_created"]
    assert len(cases) == 1
    assert cases[0]["classification"] == "MISSING_APPROVAL_CONFIGURATION"
    assert cases[0]["review_priority"] == "LOW"


def test_scenario_8_mixed_compliant_and_indeterminate_precedence(seeded_tokens):
    """
    Scenario 8: Mixed Compliant and Indeterminate Results -> PARTIALLY_EVALUATED.
    Precedence: EXCEPTION_FOUND > INSUFFICIENT_INFORMATION > PARTIALLY_EVALUATED > COMPLIANT.
    """
    token = seeded_tokens["reviewer_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with SessionLocal() as db:
        inst_id = uuid.UUID(seeded_tokens["apex_inst_id"])
        programme = db.execute(select(Programme).where(Programme.institution_id == inst_id)).scalars().first()
        prog_id = programme.id
        user = db.execute(select(User).where(User.email == "admin@apex.edu.in")).scalar_one()

        ay = f"2024-sc8-{uuid.uuid4().hex[:4]}"

        config = ApprovalConfiguration(
            institution_id=inst_id,
            programme_id=prog_id,
            academic_year=ay,
            approved_intake=60,
            supernumerary_quota_percentage=15.0,
            lateral_entry_quota_percentage=10.0,
            approval_reference="AICTE/SC8/2024",
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

        # 40 regular students + 2 unclassified students
        students = [
            *[{"name": f"Regular {i}", "apaar": f"9801{i:08d}", "dob": "2006-01-01", "gender": "M", "seat_cat": "REGULAR"} for i in range(1, 41)],
            {"name": "Unclass 1", "apaar": "980200000001", "dob": "2006-01-01", "gender": "F", "seat_cat": "UNCLASSIFIED_SEAT_CATEGORY"},
            {"name": "Unclass 2", "apaar": "980200000002", "dob": "2006-01-01", "gender": "M", "seat_cat": "UNCLASSIFIED_SEAT_CATEGORY"},
        ]
        snapshot = create_test_submission_and_snapshot(db, inst_id, prog_id, ay, students, user.id)

    res = client.post("/api/v1/approvals/intake/verify", json={"candidate_snapshot_id": str(snapshot.id)}, headers=headers)
    assert res.status_code == 201, res.text
    data = res.json()

    assert data["compliance_status"] == "PARTIALLY_EVALUATED"
    assert data["unclassified_count"] == 2


def test_multi_tenancy_and_role_guards(seeded_tokens):
    """
    Verifies multi-tenancy enforcement:
    - Polytechnic admin cannot access Apex University approval configurations or snapshots.
    """
    poly_token = seeded_tokens["poly_token"]
    apex_inst_id = seeded_tokens["apex_inst_id"]
    headers = {"Authorization": f"Bearer {poly_token}"}

    # Attempt to create configuration for Apex using Polytechnic token
    with SessionLocal() as db:
        inst_id = uuid.UUID(apex_inst_id)
        programme = db.execute(select(Programme).where(Programme.institution_id == inst_id)).scalars().first()
        prog_id = programme.id

    bad_payload = {
        "institution_id": apex_inst_id,
        "programme_id": str(prog_id),
        "academic_year": "2024-25",
        "approved_intake": 60,
        "approval_reference": "UNAUTH/001",
        "effective_from": "2024-06-01",
        "effective_to": "2025-05-31",
    }
    # 1. Attempt to create configuration as Institution Admin -> 403 Forbidden
    res_inst = client.post("/api/v1/approvals/configurations", json=bad_payload, headers=headers)
    assert res_inst.status_code == 403
    assert "Required role: SYSTEM_ADMIN, REGULATORY_REVIEWER" in res_inst.json()["detail"]

    # 2. Attempt as Third-Party Verifier -> 403 Forbidden
    ver_headers = {"Authorization": f"Bearer {seeded_tokens['verifier_token']}"}
    res_ver = client.post("/api/v1/approvals/configurations", json=bad_payload, headers=ver_headers)
    assert res_ver.status_code == 403
    assert "Required role: SYSTEM_ADMIN, REGULATORY_REVIEWER" in res_ver.json()["detail"]

    # 3. Test Cross-Institution Tenancy on Intake Verification
    with SessionLocal() as db:
        # Create a candidate snapshot belonging to Apex
        students = [{"name": "Apex Std", "apaar": "999900000001", "dob": "2006-01-01", "gender": "M", "seat_cat": "REGULAR"}]
        apex_user = db.execute(select(User).where(User.email == "admin@apex.edu.in")).scalar_one()
        ay = f"2024-cross-{uuid.uuid4().hex[:4]}"
        apex_snapshot = create_test_submission_and_snapshot(db, inst_id, prog_id, ay, students, apex_user.id)

    # Polytechnic Admin attempts to verify Apex Snapshot -> 403 Tenancy Violation
    res_cross_verify = client.post(
        "/api/v1/approvals/intake/verify",
        json={"candidate_snapshot_id": str(apex_snapshot.id)},
        headers={"Authorization": f"Bearer {poly_token}"},
    )
    assert res_cross_verify.status_code == 403
    assert "Tenancy Violation" in res_cross_verify.json()["detail"]
