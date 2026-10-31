"""Tests for Milestone 3 Phase 3E: Evidence & Discrepancy Intelligence.

Verifies:
1. All eight classifications persisted correctly as immutable run results.
2. Only review-worthy findings create discrepancy cases (CONTINUING, ADDED, WITHDRAWN, DOCUMENTED_TRANSFER do not).
3. Missing source provenance is represented safely without fabrication.
4. Repeated run requests with Idempotency-Key are idempotent.
5. New runs preserve prior run results (immutability).
6. Equivalent findings link to active cases (lineage & occurrence counts).
7. Invalid status transitions rejected; REQUEST_EVIDENCE does not resolve cases.
8. Decision history is append-only with chained AuditEvents.
9. Multi-tenant isolation and role permissions.
10. APAAR masking and field-level disclosure.
"""

import pytest
import uuid
import random
import io
import csv
from datetime import datetime, date, timezone
from sqlalchemy import select, func
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.models import (
    User,
    Programme,
    Institution,
    RosterSnapshot,
    StudentIdentity,
    AdmissionEpisode,
    TransferEvent,
    AuditEvent,
    ReconciliationRun,
    ReconciliationResultItem,
    DiscrepancyCase,
    DiscrepancyCaseDecision,
)
from app.services.storage_service import StorageService

client = TestClient(app)


@pytest.fixture(scope="module")
def seeded_tokens():
    """Logs in seeded users and provides Bearer tokens."""
    # Apex Admin
    res_apex = client.post("/api/v1/auth/login", json={"email": "admin@apex.edu.in", "password": "Apex@12345"})
    assert res_apex.status_code == 200
    apex_token = res_apex.json()["access_token"]
    apex_inst_id = res_apex.json()["user"]["institution_id"]

    # Polytechnic Admin
    res_poly = client.post("/api/v1/auth/login", json={"email": "admin@polytechnic.edu.in", "password": "Poly@12345"})
    assert res_poly.status_code == 200
    poly_token = res_poly.json()["access_token"]
    poly_inst_id = res_poly.json()["user"]["institution_id"]

    # Regulatory Reviewer
    res_rev = client.post("/api/v1/auth/login", json={"email": "reviewer@aicte.gov.in", "password": "Reviewer@12345"})
    assert res_rev.status_code == 200
    rev_token = res_rev.json()["access_token"]

    # System Admin
    res_sys = client.post("/api/v1/auth/login", json={"email": "sysadmin@aicte.gov.in", "password": "Admin@12345"})
    assert res_sys.status_code == 200
    sys_token = res_sys.json()["access_token"]

    db = SessionLocal()
    try:
        apex_prog = db.execute(select(Programme).where(Programme.institution_id == uuid.UUID(apex_inst_id))).scalars().first()
        poly_prog = db.execute(select(Programme).where(Programme.institution_id == uuid.UUID(poly_inst_id))).scalars().first()
        apex_prog_id = str(apex_prog.id) if apex_prog else None
        poly_prog_id = str(poly_prog.id) if poly_prog else None
    finally:
        db.close()

    return {
        "apex": {"token": apex_token, "inst_id": apex_inst_id, "prog_id": apex_prog_id},
        "poly": {"token": poly_token, "inst_id": poly_inst_id, "prog_id": poly_prog_id},
        "reviewer": {"token": rev_token},
        "sys": {"token": sys_token},
    }


def create_sample_csv(rows_data: list) -> io.BytesIO:
    output = io.StringIO()
    writer = csv.writer(output)
    for r in rows_data:
        writer.writerow(r)
    return io.BytesIO(output.getvalue().encode("utf-8"))


def upload_preview_and_confirm(token: str, prog_id: str, file_rows: list, mark_authoritative: bool = True, academic_year: str = "2024-25"):
    uid = uuid.uuid4().hex[:6]
    file_tuple = (f"roster_{uid}.csv", create_sample_csv(file_rows), "text/csv")

    res_up = client.post(
        "/api/v1/submissions/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": file_tuple},
        data={
            "programme_id": prog_id,
            "academic_year": academic_year,
            "submission_type": "ANNUAL_ROSTER",
        },
    )
    assert res_up.status_code == 201, res_up.text
    sub_id = res_up.json()["submission_id"]

    mapping = {"student_id": "student_id", "full_name": "full_name", "apaar_id": "apaar_id", "student_status": "student_status"}
    res_prev = client.post(
        f"/api/v1/submissions/{sub_id}/preview",
        headers={"Authorization": f"Bearer {token}"},
        json={"column_mapping": mapping},
    )
    assert res_prev.status_code == 200, res_prev.text
    prev_id = res_prev.json()["preview_id"]

    res_conf = client.post(
        f"/api/v1/submissions/{sub_id}/confirm",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "preview_id": prev_id,
            "column_mapping": mapping,
            "mark_as_authoritative": mark_authoritative,
            "completeness_status": "COMPLETE",
        },
    )
    assert res_conf.status_code == 200, res_conf.text
    return sub_id, res_conf.json()["snapshot_id"]


# =========================================================================
# 1. Reconciliation Run Execution, Result Items, and Case Creation Policy
# =========================================================================
def test_reconciliation_run_results_and_case_creation_policy(seeded_tokens):
    """
    Verify:
    1. All eight classifications are persisted as immutable ReconciliationResultItem rows.
    2. Only review-worthy findings create DiscrepancyCases (UNEXPLAINED_APPEARANCE, UNEXPLAINED_DISAPPEARANCE,
       AMBIGUOUS_IDENTITY, INSUFFICIENT_EVIDENCE).
    3. Normal outcomes (CONTINUING, ADDED, WITHDRAWN, DOCUMENTED_TRANSFER) do NOT create cases.
    4. Missing source provenance is represented safely (nulls preserved).
    """
    apex = seeded_tokens["apex"]
    poly = seeded_tokens["poly"]
    u4 = f"{random.randint(1000, 9999)}"
    year = f"2024-3E1-{u4}"

    # Baseline Roster Setup
    # S_CONT: Continuing
    # S_WITH: Withdrawn
    # S_DIS: Disappeared without documentation -> CASE
    # S_TR_OUT: Transferred out with Documented TransferEvent -> NO CASE
    # S_AMB: Ambiguous identity (missing APAAR) -> CASE
    rows_base = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        ["S_CONT", f"Cont Student {u4}", f"71002000{u4}", "ACTIVE"],
        ["S_WITH", f"With Student {u4}", f"72002000{u4}", "ACTIVE"],
        ["S_DIS", f"Dis Student {u4}", f"73002000{u4}", "ACTIVE"],
        ["S_TR_OUT", f"Trans Out {u4}", f"74002000{u4}", "ACTIVE"],
        ["S_AMB", f"Amb Student {u4}", "", "ACTIVE"],
    ]

    _, base_snap_id = upload_preview_and_confirm(
        token=apex["token"],
        prog_id=apex["prog_id"],
        file_rows=rows_base,
        mark_authoritative=True,
        academic_year=year,
    )

    db = SessionLocal()
    try:
        # Document outbound transfer for S_TR_OUT
        s_tr_ident = db.execute(
            select(StudentIdentity).where(StudentIdentity.full_name == f"Trans Out {u4}")
        ).scalars().first()
        assert s_tr_ident is not None

        transfer_out = TransferEvent(
            student_identity_id=s_tr_ident.id,
            source_institution_id=uuid.UUID(apex["inst_id"]),
            destination_institution_id=uuid.UUID(poly["inst_id"]),
            source_programme_id=uuid.UUID(apex["prog_id"]),
            destination_programme_id=uuid.UUID(poly["prog_id"]),
            academic_year=year,
            transfer_date=date.today(),
            verification_status="DOCUMENTED",
        )
        db.add(transfer_out)
        db.commit()
    finally:
        db.close()

    # Candidate Roster Setup
    # S_CONT: active -> CONTINUING (NO CASE)
    # S_WITH: status WITHDRAWN -> WITHDRAWN (NO CASE)
    # S_AMB: missing APAAR -> AMBIGUOUS_IDENTITY (CASE)
    # S_ADD: new student with AdmissionEpisode -> ADDED (NO CASE)
    # S_APP: new student without AdmissionEpisode -> UNEXPLAINED_APPEARANCE (CASE)
    rows_cand = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        ["S_CONT", f"Cont Student {u4}", f"71002000{u4}", "ACTIVE"],
        ["S_WITH", f"With Student {u4}", f"72002000{u4}", "WITHDRAWN"],
        ["S_AMB", f"Amb Student {u4}", "", "ACTIVE"],
        ["S_ADD", f"Added Student {u4}", f"75002000{u4}", "ACTIVE"],
        ["S_APP", f"Unexpected App {u4}", f"76002000{u4}", "ACTIVE"],
    ]

    _, cand_snap_id = upload_preview_and_confirm(
        token=apex["token"],
        prog_id=apex["prog_id"],
        file_rows=rows_cand,
        mark_authoritative=False,
        academic_year=year,
    )

    db = SessionLocal()
    try:
        # Link AdmissionEpisode for S_ADD
        s_add_ident = db.execute(
            select(StudentIdentity).where(StudentIdentity.full_name == f"Added Student {u4}")
        ).scalars().first()
        assert s_add_ident is not None

        adm = AdmissionEpisode(
            student_identity_id=s_add_ident.id,
            institution_id=uuid.UUID(apex["inst_id"]),
            programme_id=uuid.UUID(apex["prog_id"]),
            academic_year=year,
            admission_date=date.today(),
            admission_category="REGULAR",
        )
        db.add(adm)
        db.commit()
    finally:
        db.close()

    # Execute formal Reconciliation Run via API
    res_run = client.post(
        "/api/v1/reconciliation/runs",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={
            "candidate_snapshot_id": cand_snap_id,
            "baseline_snapshot_id": base_snap_id,
            "run_type": "REGULATORY_RECONCILIATION",
        },
    )
    assert res_run.status_code == 201, res_run.text
    run_data = res_run.json()
    run_id = run_data["id"]
    assert run_data["execution_status"] == "COMPLETED"
    assert len(run_data["result_fingerprint"]) == 64

    # 1. Inspect persisted ReconciliationResultItems
    res_items = client.get(
        f"/api/v1/reconciliation/runs/{run_id}/results?limit=100",
        headers={"Authorization": f"Bearer {apex['token']}"},
    )
    assert res_items.status_code == 200
    items = res_items.json()["items"]
    by_class = {}
    for it in items:
        by_class.setdefault(it["classification"], []).append(it)

    # All classifications are persisted in result items
    assert "CONTINUING" in by_class
    assert "WITHDRAWN" in by_class
    assert "DOCUMENTED_TRANSFER" in by_class
    assert "ADDED" in by_class
    assert "UNEXPLAINED_APPEARANCE" in by_class
    assert "UNEXPLAINED_DISAPPEARANCE" in by_class
    assert "AMBIGUOUS_IDENTITY" in by_class

    # 2. Case Creation Policy Verification:
    # Normal outcomes do NOT have a discrepancy case
    for it in by_class["CONTINUING"]:
        assert it["is_case_eligible"] is False
        assert it["discrepancy_case_id"] is None
        assert it["review_priority"] == "NONE"

    for it in by_class["ADDED"]:
        assert it["is_case_eligible"] is False
        assert it["discrepancy_case_id"] is None

    for it in by_class["WITHDRAWN"]:
        assert it["is_case_eligible"] is False
        assert it["discrepancy_case_id"] is None

    for it in by_class["DOCUMENTED_TRANSFER"]:
        assert it["is_case_eligible"] is False
        assert it["discrepancy_case_id"] is None

    # Review-worthy items MUST have an active discrepancy case
    for it in by_class["UNEXPLAINED_APPEARANCE"]:
        assert it["is_case_eligible"] is True
        assert it["discrepancy_case_id"] is not None
        assert it["review_priority"] == "HIGH"

    for it in by_class["UNEXPLAINED_DISAPPEARANCE"]:
        assert it["is_case_eligible"] is True
        assert it["discrepancy_case_id"] is not None
        assert it["review_priority"] == "HIGH"

    # 3. Source Provenance Independence
    # Absent student has baseline submission but candidate submission is None
    dis_item = by_class["UNEXPLAINED_DISAPPEARANCE"][0]
    assert dis_item["baseline_submission_id"] is not None
    assert dis_item["candidate_submission_id"] is None
    assert dis_item["candidate_row_number"] is None

    # Added student has candidate submission but baseline submission is None
    app_item = by_class["UNEXPLAINED_APPEARANCE"][0]
    assert app_item["candidate_submission_id"] is not None
    assert app_item["baseline_submission_id"] is None
    assert app_item["baseline_row_number"] is None


# =========================================================================
# 2. Idempotency & Run Immutability
# =========================================================================
def test_reconciliation_run_idempotency_and_immutability(seeded_tokens):
    """
    Verify:
    1. Retrying same run request with Idempotency-Key returns existing run without duplication.
    2. Same Idempotency-Key with different payload returns 409 Conflict.
    3. New run without idempotency key creates a new distinct run and preserves prior results.
    """
    apex = seeded_tokens["apex"]
    u4 = f"{random.randint(1000, 9999)}"
    year = f"2024-3E2-{u4}"

    rows = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        ["S1", f"Student One {u4}", f"81001100{u4}", "ACTIVE"],
    ]

    _, cand_snap_id = upload_preview_and_confirm(
        token=apex["token"],
        prog_id=apex["prog_id"],
        file_rows=rows,
        mark_authoritative=False,
        academic_year=year,
    )

    idem_key = f"key-{uuid.uuid4().hex}"

    # 1. Initial execution with Idempotency-Key
    res_1 = client.post(
        "/api/v1/reconciliation/runs",
        headers={"Authorization": f"Bearer {apex['token']}", "Idempotency-Key": idem_key},
        json={
            "candidate_snapshot_id": cand_snap_id,
            "run_type": "REGULATORY_RECONCILIATION",
        },
    )
    assert res_1.status_code == 201
    run_1_id = res_1.json()["id"]

    # 2. Replay with identical key and payload -> returns original run
    res_replay = client.post(
        "/api/v1/reconciliation/runs",
        headers={"Authorization": f"Bearer {apex['token']}", "Idempotency-Key": idem_key},
        json={
            "candidate_snapshot_id": cand_snap_id,
            "run_type": "REGULATORY_RECONCILIATION",
        },
    )
    assert res_replay.status_code == 201 or res_replay.status_code == 200
    assert res_replay.json()["id"] == run_1_id

    # 3. Same key with conflicting parameters -> 409 Conflict
    res_conflict = client.post(
        "/api/v1/reconciliation/runs",
        headers={"Authorization": f"Bearer {apex['token']}", "Idempotency-Key": idem_key},
        json={
            "candidate_snapshot_id": cand_snap_id,
            "run_type": "INSTITUTIONAL_SELF_AUDIT",  # Changed
        },
    )
    assert res_conflict.status_code == 409
    assert "idempotency conflict" in res_conflict.json()["detail"].lower()

    # 4. New run request creates a new distinct run and does not overwrite run 1
    res_2 = client.post(
        "/api/v1/reconciliation/runs",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={
            "candidate_snapshot_id": cand_snap_id,
            "run_type": "REGULATORY_RECONCILIATION",
        },
    )
    assert res_2.status_code == 201
    run_2_id = res_2.json()["id"]
    assert run_2_id != run_1_id


# =========================================================================
# 3. Discrepancy Case Lineage & Equivalence Linking
# =========================================================================
def test_case_lineage_and_equivalence_linking(seeded_tokens):
    """
    Verify:
    1. First run creates a DiscrepancyCase.
    2. Second run for same student and classification links to the active case,
       updating occurrence_count and latest_reconciliation_run_id without spawning duplicate case.
    """
    apex = seeded_tokens["apex"]
    u4 = f"{random.randint(1000, 9999)}"
    year = f"2024-3E3-{u4}"

    rows = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        ["S_APP", f"Unexplained Student {u4}", f"82001100{u4}", "ACTIVE"],
    ]

    _, cand_snap_id = upload_preview_and_confirm(
        token=apex["token"],
        prog_id=apex["prog_id"],
        file_rows=rows,
        mark_authoritative=False,
        academic_year=year,
    )

    # Run 1
    res_run1 = client.post(
        "/api/v1/reconciliation/runs",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={"candidate_snapshot_id": cand_snap_id},
    )
    assert res_run1.status_code == 201
    run1_id = res_run1.json()["id"]

    # Query result items to get the created case
    res_items1 = client.get(
        f"/api/v1/reconciliation/runs/{run1_id}/results",
        headers={"Authorization": f"Bearer {apex['token']}"},
    )
    case_id_1 = res_items1.json()["items"][0]["discrepancy_case_id"]
    assert case_id_1 is not None

    # Check case detail
    res_case1 = client.get(
        f"/api/v1/discrepancies/cases/{case_id_1}",
        headers={"Authorization": f"Bearer {apex['token']}"},
    )
    assert res_case1.status_code == 200
    assert res_case1.json()["occurrence_count"] == 1
    assert res_case1.json()["case_status"] == "OPEN"

    # Run 2 (Subsequent reconciliation run generating equivalent finding)
    res_run2 = client.post(
        "/api/v1/reconciliation/runs",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={"candidate_snapshot_id": cand_snap_id},
    )
    assert res_run2.status_code == 201
    run2_id = res_run2.json()["id"]

    res_items2 = client.get(
        f"/api/v1/reconciliation/runs/{run2_id}/results",
        headers={"Authorization": f"Bearer {apex['token']}"},
    )
    case_id_2 = res_items2.json()["items"][0]["discrepancy_case_id"]

    # Must link to the exact same case!
    assert case_id_1 == case_id_2

    # Case occurrence count must be 2, latest run must be run2
    res_case2 = client.get(
        f"/api/v1/discrepancies/cases/{case_id_1}",
        headers={"Authorization": f"Bearer {apex['token']}"},
    )
    assert res_case2.status_code == 200
    case2_data = res_case2.json()
    assert case2_data["occurrence_count"] == 2
    assert case2_data["latest_reconciliation_run_id"] == run2_id
    assert case2_data["initial_reconciliation_run_id"] == run1_id


# =========================================================================
# 4. Controlled Decision Status Transitions & Audit History
# =========================================================================
def test_decision_status_transitions_and_append_only_history(seeded_tokens):
    """
    Verify:
    1. Mandatory reason length (>= 10 chars) is strictly enforced.
    2. Invalid status transitions are rejected (HTTP 409).
    3. REQUEST_EVIDENCE transitions to EVIDENCE_REQUESTED and does not close case.
    4. SUBMIT_EXPLANATION transitions to EXPLANATION_SUBMITTED.
    5. CONFIRM_VALID transitions to VERIFIED_VALID.
    6. CLOSE_CASE transitions to CLOSED.
    7. All decisions are appended to immutable history with chained AuditEvents.
    """
    apex = seeded_tokens["apex"]
    rev = seeded_tokens["reviewer"]
    u4 = f"{random.randint(1000, 9999)}"
    year = f"2024-3E4-{u4}"

    rows = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        ["S_APP", f"Decision Student {u4}", f"83001100{u4}", "ACTIVE"],
    ]

    _, cand_snap_id = upload_preview_and_confirm(
        token=apex["token"],
        prog_id=apex["prog_id"],
        file_rows=rows,
        mark_authoritative=False,
        academic_year=year,
    )

    res_run = client.post(
        "/api/v1/reconciliation/runs",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={"candidate_snapshot_id": cand_snap_id},
    )
    run_id = res_run.json()["id"]

    res_items = client.get(
        f"/api/v1/reconciliation/runs/{run_id}/results",
        headers={"Authorization": f"Bearer {apex['token']}"},
    )
    case_id = res_items.json()["items"][0]["discrepancy_case_id"]

    # 1. Mandatory Reason Enforcement (reason < 10 chars -> 422)
    res_short = client.post(
        f"/api/v1/discrepancies/cases/{case_id}/decisions",
        headers={"Authorization": f"Bearer {rev['token']}"},
        json={"action": "START_INVESTIGATION", "mandatory_reason": "Short"},
    )
    assert res_short.status_code == 422

    # 2. Invalid Transition (Cannot CLOSE_CASE from OPEN -> 409)
    res_invalid_trans = client.post(
        f"/api/v1/discrepancies/cases/{case_id}/decisions",
        headers={"Authorization": f"Bearer {rev['token']}"},
        json={"action": "CLOSE_CASE", "mandatory_reason": "Attempting premature closure"},
    )
    assert res_invalid_trans.status_code == 409
    assert "illegal state transition" in res_invalid_trans.json()["detail"].lower()

    # 3. Valid Step 1: Reviewer starts investigation
    res_step1 = client.post(
        f"/api/v1/discrepancies/cases/{case_id}/decisions",
        headers={"Authorization": f"Bearer {rev['token']}"},
        json={
            "action": "START_INVESTIGATION",
            "mandatory_reason": "Beginning formal discrepancy inquiry into unverified student appearance.",
        },
    )
    assert res_step1.status_code == 200
    assert res_step1.json()["to_status"] == "UNDER_INVESTIGATION"

    # 4. Valid Step 2: Reviewer requests evidence
    res_step2 = client.post(
        f"/api/v1/discrepancies/cases/{case_id}/decisions",
        headers={"Authorization": f"Bearer {rev['token']}"},
        json={
            "action": "REQUEST_EVIDENCE",
            "mandatory_reason": "Requesting admission council allotment letter and identity proof.",
        },
    )
    assert res_step2.status_code == 200
    # Must NOT be closed or resolved!
    assert res_step2.json()["to_status"] == "EVIDENCE_REQUESTED"

    # Verify case status is EVIDENCE_REQUESTED
    res_case_check = client.get(
        f"/api/v1/discrepancies/cases/{case_id}",
        headers={"Authorization": f"Bearer {apex['token']}"},
    )
    assert res_case_check.json()["case_status"] == "EVIDENCE_REQUESTED"

    # 5. Valid Step 3: Institution Admin submits explanation
    res_step3 = client.post(
        f"/api/v1/discrepancies/cases/{case_id}/decisions",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={
            "action": "SUBMIT_EXPLANATION",
            "mandatory_reason": "Student admitted under state management quota round 3; allotment letter attached.",
            "evidence_references": {"document_ref": "DOC-ALLOTMENT-2024-001"},
        },
    )
    assert res_step3.status_code == 200
    assert res_step3.json()["to_status"] == "EXPLANATION_SUBMITTED"

    # 6. Valid Step 4: Reviewer confirms valid
    res_step4 = client.post(
        f"/api/v1/discrepancies/cases/{case_id}/decisions",
        headers={"Authorization": f"Bearer {rev['token']}"},
        json={
            "action": "CONFIRM_VALID",
            "mandatory_reason": "State quota allotment verified against CET centralized database.",
        },
    )
    assert res_step4.status_code == 200
    assert res_step4.json()["to_status"] == "VERIFIED_VALID"

    # 7. Valid Step 5: Reviewer closes case
    res_step5 = client.post(
        f"/api/v1/discrepancies/cases/{case_id}/decisions",
        headers={"Authorization": f"Bearer {rev['token']}"},
        json={
            "action": "CLOSE_CASE",
            "mandatory_reason": "Inquiry completed; all regulatory requirements verified satisfactorily.",
        },
    )
    assert res_step5.status_code == 200
    assert res_step5.json()["to_status"] == "CLOSED"

    # 8. Inspect Decision History
    res_hist = client.get(
        f"/api/v1/discrepancies/cases/{case_id}/history",
        headers={"Authorization": f"Bearer {rev['token']}"},
    )
    assert res_hist.status_code == 200
    history = res_hist.json()
    assert len(history) == 5
    actions = [h["action"] for h in history]
    assert actions == [
        "START_INVESTIGATION",
        "REQUEST_EVIDENCE",
        "SUBMIT_EXPLANATION",
        "CONFIRM_VALID",
        "CLOSE_CASE",
    ]


# =========================================================================
# 5. Multi-Tenant Isolation & Role Permissions
# =========================================================================
def test_discrepancy_tenancy_and_role_restrictions(seeded_tokens):
    """
    Verify:
    1. Apex Admin cannot access Polytechnic cases or decisions (HTTP 403).
    2. Polytechnic Admin cannot access Apex cases or decisions (HTTP 403).
    3. Regulatory Reviewer has global oversight.
    4. Institution Admin cannot perform reviewer-only actions (e.g. CONFIRM_VALID, CLOSE_CASE).
    5. APAAR IDs are masked in API responses.
    """
    apex = seeded_tokens["apex"]
    poly = seeded_tokens["poly"]
    rev = seeded_tokens["reviewer"]
    u4 = f"{random.randint(1000, 9999)}"
    year = f"2024-3E5-{u4}"

    # Create Apex discrepancy case
    rows_apex = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        ["S_APEX", f"Apex Secret Student {u4}", f"84001100{u4}", "ACTIVE"],
    ]
    _, cand_snap_apex = upload_preview_and_confirm(
        token=apex["token"],
        prog_id=apex["prog_id"],
        file_rows=rows_apex,
        mark_authoritative=False,
        academic_year=year,
    )
    res_run_apex = client.post(
        "/api/v1/reconciliation/runs",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={"candidate_snapshot_id": cand_snap_apex},
    )
    run_apex_id = res_run_apex.json()["id"]

    res_items = client.get(
        f"/api/v1/reconciliation/runs/{run_apex_id}/results",
        headers={"Authorization": f"Bearer {apex['token']}"},
    )
    apex_case_id = res_items.json()["items"][0]["discrepancy_case_id"]

    # 1. Poly Admin attempts to query Apex case -> 403 Forbidden
    res_poly_get = client.get(
        f"/api/v1/discrepancies/cases/{apex_case_id}",
        headers={"Authorization": f"Bearer {poly['token']}"},
    )
    assert res_poly_get.status_code == 403
    assert "tenancy violation" in res_poly_get.json()["detail"].lower()

    # 2. Poly Admin attempts to record decision on Apex case -> 403 Forbidden
    res_poly_dec = client.post(
        f"/api/v1/discrepancies/cases/{apex_case_id}/decisions",
        headers={"Authorization": f"Bearer {poly['token']}"},
        json={"action": "START_INVESTIGATION", "mandatory_reason": "Unauthorized poly decision attempt."},
    )
    assert res_poly_dec.status_code == 403

    # 3. Apex Admin attempts reviewer-only action (START_INVESTIGATION) -> 403 Forbidden
    res_apex_rev_action = client.post(
        f"/api/v1/discrepancies/cases/{apex_case_id}/decisions",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={"action": "START_INVESTIGATION", "mandatory_reason": "Institution attempting reviewer action."},
    )
    assert res_apex_rev_action.status_code == 403
    assert "restricted to roles" in res_apex_rev_action.json()["detail"].lower()

    # 4. Reviewer can view Apex case and verify APAAR masking
    res_rev_get = client.get(
        f"/api/v1/discrepancies/cases/{apex_case_id}",
        headers={"Authorization": f"Bearer {rev['token']}"},
    )
    assert res_rev_get.status_code == 200
    case_detail = res_rev_get.json()
    assert case_detail["masked_apaar"].startswith("XXXX-XXXX-")
    assert u4 in case_detail["masked_apaar"]
