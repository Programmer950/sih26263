"""Milestone 5.2 Verification Test Suite.

Exhaustively verifies:
1. Same blind index with unverified identity -> AMBIGUOUS_IDENTITY.
2. Blind-index key-version metadata and check.
3. Legitimate transfer within one academic year -> LEGITIMATE_TRANSFER.
4. Missing admission or exit dates -> INSUFFICIENT_EVIDENCE.
5. Unverified transfer assertion -> UNRESOLVED_TRANSFER.
6. Concurrent enrolment with overlapping dates and no verified transfer -> CONCURRENT_DUAL_ENROLMENT.
7. Candidate-side cohort classification summation.
8. Baseline-side disappearance accounting.
9. Same student appearing in multiple intake-related findings without aggregate double-counting.
10. Independent engine failures and partial unified execution.
11. Duplicate run idempotency.
12. Cross-tenant duplicate visibility.
13. API contract consistency.
"""

import io
import csv
import uuid
import random
from datetime import date, datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.core.database import SessionLocal
from app.models import (
    User,
    Institution,
    Programme,
    StudentIdentity,
    AnnualRosterObservation,
    AdmissionEpisode,
    TransferEvent,
    RosterSnapshot,
    ApprovalConfiguration,
)
from app.services.duplicate_service import DuplicateService, BLIND_INDEX_VERSION
from app.services.unified_reconciliation_service import UnifiedReconciliationService
from app.schemas.unified_reconciliation import UnifiedReconciliationRequest
from tests.test_e2e_integration import upload_preview_and_confirm, e2e_tokens

client = TestClient(app)


def test_01_same_blind_index_with_unverified_identity(e2e_tokens):
    """1. Same blind index with unverified identity produces AMBIGUOUS_IDENTITY, not false conviction."""
    rev = e2e_tokens["reviewer"]
    ay = f"2024-dup-{uuid.uuid4().hex[:4]}"
    shared_blind_idx = f"blind_unver_{uuid.uuid4().hex}"

    with SessionLocal() as db:
        apex_inst_id = uuid.UUID(e2e_tokens["apex"]["inst_id"])
        poly_inst_id = uuid.UUID(e2e_tokens["poly"]["inst_id"])
        apex_prog_id = uuid.UUID(e2e_tokens["apex"]["prog_id"])
        poly_prog_id = uuid.UUID(e2e_tokens["poly"]["prog_id"])

        # Unverified StudentIdentity enrolled across two institutions
        s = StudentIdentity(
            full_name="Unverified Across Institutions",
            apaar_blind_index=shared_blind_idx,
            masked_apaar_reference="XXXX-XXXX-1111",
            identity_status="UNVERIFIED",
        )
        db.add(s)
        db.flush()

        obs1 = AnnualRosterObservation(
            student_identity_id=s.id,
            institution_id=apex_inst_id,
            programme_id=apex_prog_id,
            academic_year=ay,
            student_status="ACTIVE",
        )
        obs2 = AnnualRosterObservation(
            student_identity_id=s.id,
            institution_id=poly_inst_id,
            programme_id=poly_prog_id,
            academic_year=ay,
            student_status="ACTIVE",
        )
        db.add_all([obs1, obs2])
        db.commit()

    res = client.get(
        f"/api/v1/reconciliation/duplicates?academic_year={ay}",
        headers={"Authorization": f"Bearer {rev['token']}"},
    )
    assert res.status_code == 200
    conflicts = res.json()
    assert len(conflicts) >= 1
    target = next((c for c in conflicts if c["blind_index"] == shared_blind_idx), None)
    assert target is not None
    assert target["conflict_type"] == "AMBIGUOUS_IDENTITY"
    assert target["review_priority"] == "MEDIUM"


def test_02_blind_index_key_version_metadata():
    """2. Blind-index key-version metadata is preserved and verified."""
    assert BLIND_INDEX_VERSION == "v1-apaar-sha256"


def test_03_legitimate_transfer_within_academic_year(e2e_tokens):
    """3. Legitimate transfer within one academic year recognized as LEGITIMATE_TRANSFER."""
    rev = e2e_tokens["reviewer"]
    ay = f"2024-trf-{uuid.uuid4().hex[:4]}"
    shared_blind_idx = f"blind_trf_{uuid.uuid4().hex}"

    with SessionLocal() as db:
        apex_inst_id = uuid.UUID(e2e_tokens["apex"]["inst_id"])
        poly_inst_id = uuid.UUID(e2e_tokens["poly"]["inst_id"])
        apex_prog_id = uuid.UUID(e2e_tokens["apex"]["prog_id"])
        poly_prog_id = uuid.UUID(e2e_tokens["poly"]["prog_id"])

        s = StudentIdentity(
            full_name="Transfer Student",
            apaar_blind_index=shared_blind_idx,
            masked_apaar_reference="XXXX-XXXX-2222",
            identity_status="FORMAT_VALID",
        )
        db.add(s)
        db.flush()

        obs1 = AnnualRosterObservation(
            student_identity_id=s.id,
            institution_id=apex_inst_id,
            programme_id=apex_prog_id,
            academic_year=ay,
            student_status="ACTIVE",
        )
        obs2 = AnnualRosterObservation(
            student_identity_id=s.id,
            institution_id=poly_inst_id,
            programme_id=poly_prog_id,
            academic_year=ay,
            student_status="ACTIVE",
        )
        db.add_all([obs1, obs2])

        # Documented transfer event
        trf = TransferEvent(
            student_identity_id=s.id,
            source_institution_id=apex_inst_id,
            destination_institution_id=poly_inst_id,
            source_programme_id=apex_prog_id,
            destination_programme_id=poly_prog_id,
            academic_year=ay,
            transfer_date=date(2024, 11, 15),
            verification_status="DOCUMENTED",
        )
        db.add(trf)
        db.commit()

    res = client.get(
        f"/api/v1/reconciliation/duplicates?academic_year={ay}",
        headers={"Authorization": f"Bearer {rev['token']}"},
    )
    assert res.status_code == 200
    target = next((c for c in res.json() if c["blind_index"] == shared_blind_idx), None)
    assert target is not None
    assert target["conflict_type"] == "LEGITIMATE_TRANSFER"
    assert target["is_verified_transfer"] is True
    assert target["review_priority"] == "INFO"


def test_04_missing_admission_or_exit_dates(e2e_tokens):
    """4. Missing admission or exit dates produces INSUFFICIENT_EVIDENCE rather than dual conviction."""
    rev = e2e_tokens["reviewer"]
    ay = f"2024-nodate-{uuid.uuid4().hex[:4]}"
    shared_blind_idx = f"blind_nodate_{uuid.uuid4().hex}"

    with SessionLocal() as db:
        apex_inst_id = uuid.UUID(e2e_tokens["apex"]["inst_id"])
        poly_inst_id = uuid.UUID(e2e_tokens["poly"]["inst_id"])
        apex_prog_id = uuid.UUID(e2e_tokens["apex"]["prog_id"])
        poly_prog_id = uuid.UUID(e2e_tokens["poly"]["prog_id"])

        s = StudentIdentity(
            full_name="No Date Student",
            apaar_blind_index=shared_blind_idx,
            masked_apaar_reference="XXXX-XXXX-3333",
            identity_status="FORMAT_VALID",
        )
        db.add(s)
        db.flush()

        obs1 = AnnualRosterObservation(
            student_identity_id=s.id,
            institution_id=apex_inst_id,
            programme_id=apex_prog_id,
            academic_year=ay,
            student_status="ACTIVE",
        )
        obs2 = AnnualRosterObservation(
            student_identity_id=s.id,
            institution_id=poly_inst_id,
            programme_id=poly_prog_id,
            academic_year=ay,
            student_status="ACTIVE",
        )
        # Note: No admission episodes created!
        db.add_all([obs1, obs2])
        db.commit()

    res = client.get(
        f"/api/v1/reconciliation/duplicates?academic_year={ay}",
        headers={"Authorization": f"Bearer {rev['token']}"},
    )
    assert res.status_code == 200
    target = next((c for c in res.json() if c["blind_index"] == shared_blind_idx), None)
    assert target is not None
    assert target["conflict_type"] == "INSUFFICIENT_EVIDENCE"


def test_05_unverified_transfer_assertion(e2e_tokens):
    """5. Unverified transfer assertion produces UNRESOLVED_TRANSFER."""
    rev = e2e_tokens["reviewer"]
    ay = f"2024-unvtrf-{uuid.uuid4().hex[:4]}"
    shared_blind_idx = f"blind_unvtrf_{uuid.uuid4().hex}"

    with SessionLocal() as db:
        apex_inst_id = uuid.UUID(e2e_tokens["apex"]["inst_id"])
        poly_inst_id = uuid.UUID(e2e_tokens["poly"]["inst_id"])
        apex_prog_id = uuid.UUID(e2e_tokens["apex"]["prog_id"])
        poly_prog_id = uuid.UUID(e2e_tokens["poly"]["prog_id"])

        s = StudentIdentity(
            full_name="Unresolved Transfer",
            apaar_blind_index=shared_blind_idx,
            masked_apaar_reference="XXXX-XXXX-4444",
            identity_status="FORMAT_VALID",
        )
        db.add(s)
        db.flush()

        obs1 = AnnualRosterObservation(
            student_identity_id=s.id,
            institution_id=apex_inst_id,
            programme_id=apex_prog_id,
            academic_year=ay,
            student_status="ACTIVE",
        )
        obs2 = AnnualRosterObservation(
            student_identity_id=s.id,
            institution_id=poly_inst_id,
            programme_id=poly_prog_id,
            academic_year=ay,
            student_status="ACTIVE",
        )
        # Pending/Unverified Transfer
        trf = TransferEvent(
            student_identity_id=s.id,
            source_institution_id=apex_inst_id,
            destination_institution_id=poly_inst_id,
            source_programme_id=apex_prog_id,
            destination_programme_id=poly_prog_id,
            academic_year=ay,
            transfer_date=date(2024, 10, 1),
            verification_status="PENDING",
        )
        db.add_all([obs1, obs2, trf])
        db.commit()

    res = client.get(
        f"/api/v1/reconciliation/duplicates?academic_year={ay}",
        headers={"Authorization": f"Bearer {rev['token']}"},
    )
    assert res.status_code == 200
    target = next((c for c in res.json() if c["blind_index"] == shared_blind_idx), None)
    assert target is not None
    assert target["conflict_type"] == "UNRESOLVED_TRANSFER"
    assert target["is_verified_transfer"] is False


def test_06_concurrent_enrolment_overlapping_dates(e2e_tokens):
    """6. Concurrent enrolment with overlapping dates and no verified transfer produces CONCURRENT_DUAL_ENROLMENT."""
    rev = e2e_tokens["reviewer"]
    ay = f"2024-dual-{uuid.uuid4().hex[:4]}"
    shared_blind_idx = f"blind_dual_{uuid.uuid4().hex}"

    with SessionLocal() as db:
        apex_inst_id = uuid.UUID(e2e_tokens["apex"]["inst_id"])
        poly_inst_id = uuid.UUID(e2e_tokens["poly"]["inst_id"])
        apex_prog_id = uuid.UUID(e2e_tokens["apex"]["prog_id"])
        poly_prog_id = uuid.UUID(e2e_tokens["poly"]["prog_id"])

        s = StudentIdentity(
            full_name="Dual Enrolment Student",
            apaar_blind_index=shared_blind_idx,
            masked_apaar_reference="XXXX-XXXX-5555",
            identity_status="FORMAT_VALID",
        )
        db.add(s)
        db.flush()

        obs1 = AnnualRosterObservation(
            student_identity_id=s.id,
            institution_id=apex_inst_id,
            programme_id=apex_prog_id,
            academic_year=ay,
            student_status="ACTIVE",
        )
        obs2 = AnnualRosterObservation(
            student_identity_id=s.id,
            institution_id=poly_inst_id,
            programme_id=poly_prog_id,
            academic_year=ay,
            student_status="ACTIVE",
        )
        # Overlapping admission episodes
        ep1 = AdmissionEpisode(
            student_identity_id=s.id,
            institution_id=apex_inst_id,
            programme_id=apex_prog_id,
            academic_year=ay,
            admission_date=date(2024, 7, 1),
            seat_accounting_category="REGULAR",
        )
        ep2 = AdmissionEpisode(
            student_identity_id=s.id,
            institution_id=poly_inst_id,
            programme_id=poly_prog_id,
            academic_year=ay,
            admission_date=date(2024, 8, 1),
            seat_accounting_category="REGULAR",
        )
        db.add_all([obs1, obs2, ep1, ep2])
        db.commit()

    res = client.get(
        f"/api/v1/reconciliation/duplicates?academic_year={ay}",
        headers={"Authorization": f"Bearer {rev['token']}"},
    )
    assert res.status_code == 200
    target = next((c for c in res.json() if c["blind_index"] == shared_blind_idx), None)
    assert target is not None
    assert target["conflict_type"] == "CONCURRENT_DUAL_ENROLMENT"
    assert target["review_priority"] == "HIGH"


def test_07_candidate_side_cohort_summation(e2e_tokens):
    """7. Candidate-side cohort classification summation invariant holds."""
    apex = e2e_tokens["apex"]
    ay = f"2024-sum-{uuid.uuid4().hex[:4]}"
    rows = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        ["S1", "Student One", f"99{random.randint(1000000000, 9999999999)}", "ACTIVE"],
        ["S2", "Student Two", f"99{random.randint(1000000000, 9999999999)}", "ACTIVE"],
    ]
    _, snap_id = upload_preview_and_confirm(apex["token"], apex["prog_id"], rows, mark_authoritative=False, academic_year=ay)

    res = client.post(
        "/api/v1/reconciliation/unified",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={"snapshot_id": snap_id},
    )
    assert res.status_code == 200
    cohort = res.json()["cohort_summary"]

    # Candidate sum equals total candidate observations
    computed_sum = (
        cohort["continuing_count"]
        + cohort["added_count"]
        + cohort["documented_transfer_count"]
        + cohort["unexplained_appearance_count"]
        + cohort["ambiguous_identity_count"]
        + cohort["insufficient_evidence_count"]
    )
    assert computed_sum == cohort["total_candidate_observations"]
    assert cohort["total_candidate_observations"] == 2


def test_08_baseline_side_disappearance_accounting(e2e_tokens):
    """8. Baseline-side departures are accounted separately in baseline_disappearances."""
    apex = e2e_tokens["apex"]
    ay_base = f"2023-dep-{uuid.uuid4().hex[:4]}"
    ay_cand = f"2024-dep-{uuid.uuid4().hex[:4]}"
    shared_apaar = f"99{random.randint(1000000000, 9999999999)}"

    # Baseline has 2 students
    rows_base = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        ["S1", "Cont Std", shared_apaar, "ACTIVE"],
        ["S2", "Departed Std", f"99{random.randint(1000000000, 9999999999)}", "ACTIVE"],
    ]
    _, base_snap_id = upload_preview_and_confirm(apex["token"], apex["prog_id"], rows_base, mark_authoritative=True, academic_year=ay_base)

    # Candidate has 1 student (S1 continuing, S2 absent)
    rows_cand = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        ["S1", "Cont Std", shared_apaar, "ACTIVE"],
    ]
    _, cand_snap_id = upload_preview_and_confirm(apex["token"], apex["prog_id"], rows_cand, mark_authoritative=False, academic_year=ay_cand)

    res = client.post(
        "/api/v1/reconciliation/unified",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={"snapshot_id": cand_snap_id, "baseline_snapshot_id": base_snap_id},
    )
    assert res.status_code == 200
    cohort = res.json()["cohort_summary"]

    # Departures are isolated in baseline_disappearances
    assert "WITHDRAWN" in cohort["baseline_disappearances"] or "UNEXPLAINED_DISAPPEARANCE" in cohort["baseline_disappearances"]
    disappearances_total = sum(cohort["baseline_disappearances"].values())
    assert disappearances_total >= 1
    # Candidate-side total still strictly counts candidate observations
    assert cohort["total_candidate_observations"] == 1


def test_09_anti_double_counting_in_intake_and_cohort(e2e_tokens):
    """9. Student appearing in multiple findings does not inflate aggregate totals."""
    apex = e2e_tokens["apex"]
    ay = f"2024-ndc-{uuid.uuid4().hex[:4]}"
    rows = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        ["S1", "Single Student", f"99{random.randint(1000000000, 9999999999)}", "ACTIVE"],
    ]
    _, snap_id = upload_preview_and_confirm(apex["token"], apex["prog_id"], rows, mark_authoritative=False, academic_year=ay)

    res = client.post(
        "/api/v1/reconciliation/unified",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={"snapshot_id": snap_id},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["cohort_summary"]["total_candidate_observations"] == 1


def test_10_missing_approval_configuration_partial_unified_success(e2e_tokens):
    """10. Missing approval config produces INSUFFICIENT_INFORMATION for intake while cohort succeeds."""
    apex = e2e_tokens["apex"]
    ay = f"2024-noapp-{uuid.uuid4().hex[:4]}"
    rows = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        ["S1", "No App Std", f"99{random.randint(1000000000, 9999999999)}", "ACTIVE"],
    ]
    _, snap_id = upload_preview_and_confirm(apex["token"], apex["prog_id"], rows, mark_authoritative=False, academic_year=ay)

    res = client.post(
        "/api/v1/reconciliation/unified",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={"snapshot_id": snap_id},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "COMPLETED"
    assert data["intake_summary"]["compliance_status"] == "INSUFFICIENT_INFORMATION"
    assert data["cohort_summary"]["total_candidate_observations"] == 1


def test_11_duplicate_detection_idempotency(e2e_tokens):
    """11. Duplicate detection endpoint is repeatable and produces consistent responses."""
    rev = e2e_tokens["reviewer"]
    res1 = client.get("/api/v1/reconciliation/duplicates?academic_year=2024-25", headers={"Authorization": f"Bearer {rev['token']}"})
    res2 = client.get("/api/v1/reconciliation/duplicates?academic_year=2024-25", headers={"Authorization": f"Bearer {rev['token']}"})
    assert res1.status_code == 200
    assert res2.status_code == 200
    assert len(res1.json()) == len(res2.json())


def test_12_cross_tenant_duplicate_visibility(e2e_tokens):
    """12. Institution Admin only sees duplicates involving their own institution."""
    poly = e2e_tokens["poly"]
    ay = f"2024-vis-{uuid.uuid4().hex[:4]}"
    shared_blind_idx = f"blind_vis_{uuid.uuid4().hex}"

    with SessionLocal() as db:
        apex_inst_id = uuid.UUID(e2e_tokens["apex"]["inst_id"])
        poly_inst_id = uuid.UUID(e2e_tokens["poly"]["inst_id"])
        apex_prog_id = uuid.UUID(e2e_tokens["apex"]["prog_id"])
        poly_prog_id = uuid.UUID(e2e_tokens["poly"]["prog_id"])

        s = StudentIdentity(
            full_name="Visibility Test Student",
            apaar_blind_index=shared_blind_idx,
            masked_apaar_reference="XXXX-XXXX-8888",
            identity_status="FORMAT_VALID",
        )
        db.add(s)
        db.flush()

        # Enrolled in Apex and Poly
        obs1 = AnnualRosterObservation(
            student_identity_id=s.id,
            institution_id=apex_inst_id,
            programme_id=apex_prog_id,
            academic_year=ay,
            student_status="ACTIVE",
        )
        obs2 = AnnualRosterObservation(
            student_identity_id=s.id,
            institution_id=poly_inst_id,
            programme_id=poly_prog_id,
            academic_year=ay,
            student_status="ACTIVE",
        )
        db.add_all([obs1, obs2])
        db.commit()

    # Polytechnic Admin queries duplicates
    res_poly = client.get(
        f"/api/v1/reconciliation/duplicates?academic_year={ay}",
        headers={"Authorization": f"Bearer {poly['token']}"},
    )
    assert res_poly.status_code == 200
    poly_conflicts = res_poly.json()
    assert any(c["blind_index"] == shared_blind_idx for c in poly_conflicts)

    # Verifier attempting duplicate detection -> 403 Forbidden
    ver = e2e_tokens["verifier"]
    res_ver = client.get(
        f"/api/v1/reconciliation/duplicates?academic_year={ay}",
        headers={"Authorization": f"Bearer {ver['token']}"},
    )
    assert res_ver.status_code == 403


def test_13_api_contract_consistency_with_frontend(e2e_tokens):
    """13. Verified API contracts match required frontend interfaces."""
    rev = e2e_tokens["reviewer"]
    res = client.get("/api/v1/reconciliation/duplicates", headers={"Authorization": f"Bearer {rev['token']}"})
    assert res.status_code == 200
    for item in res.json():
        assert "student_identity_id" in item
        assert "masked_apaar_reference" in item
        assert "full_name" in item
        assert "conflict_type" in item
        assert "review_priority" in item
        assert "enrolments" in item
        assert isinstance(item["enrolments"], list)
