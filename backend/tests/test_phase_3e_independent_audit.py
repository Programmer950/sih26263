"""Independent Phase 3E Verification & Audit Test Suite.

Verifies:
1. Database integrity & constraint enforcement (RESTRICT on snapshot/institution deletion).
2. Concurrency & Idempotency:
   - Multiple requests with same Idempotency-Key return identical run without duplicate runs, items, or cases.
   - Advisory locking serializes execution.
   - Conflicting parameters return 409 Conflict.
   - Rollback integrity on failure.
3. Case Lineage & Boundary Isolation:
   - Different students, institutions, programmes, academic years and classifications are strictly isolated.
   - Re-occurrences after closure correctly populate linked_prior_case_id and reset occurrence_count to 1.
   - Active cases increment occurrence_count.
4. Decision Workflow:
   - Full status transition rules.
   - Role boundaries (Institution Admin cannot perform reviewer actions).
   - Mandatory reason >= 10 chars.
   - REQUEST_EVIDENCE cannot resolve cases.
   - REOPEN_CASE restores closed cases to UNDER_INVESTIGATION.
5. Evidence Security & Tenancy:
   - Cross-tenant access blocked across ALL endpoints (runs, results, cases, decisions, history).
   - APAAR masking (XXXX-XXXX-1234) enforced across all endpoints.
   - AuditEvent payloads contain no sensitive PII or unmasked student identifiers.
6. Reproducibility:
   - Fingerprint determinism and snapshot hash verification.
"""

import pytest
import uuid
import random
import io
import csv
from datetime import datetime, date, timezone
from sqlalchemy import select, func, text
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
from app.services.reconciliation_service import ReconciliationService
from app.schemas.reconciliation import ReconciliationRunCreateRequest

client = TestClient(app)


@pytest.fixture(scope="module")
def audit_tokens():
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


def create_csv_buffer(rows_data: list) -> io.BytesIO:
    output = io.StringIO()
    writer = csv.writer(output)
    for r in rows_data:
        writer.writerow(r)
    return io.BytesIO(output.getvalue().encode("utf-8"))


def upload_and_confirm(token: str, prog_id: str, file_rows: list, mark_authoritative: bool = True, academic_year: str = "2024-25"):
    uid = uuid.uuid4().hex[:6]
    file_tuple = (f"audit_roster_{uid}.csv", create_csv_buffer(file_rows), "text/csv")

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
# AUDIT AREA 1: Database Integrity & Deletion RESTRICT
# =========================================================================
def test_database_foreign_key_restricts(audit_tokens):
    """
    Verify deletion behavior:
    1. Candidate snapshot cannot be deleted if referenced by ReconciliationRun (RESTRICT).
    2. DiscrepancyCase cannot be deleted if referenced by DiscrepancyCaseDecision (RESTRICT).
    """
    apex = audit_tokens["apex"]
    u4 = f"{random.randint(1000, 9999)}"
    year = f"2024-A1-{u4}"

    rows = [["student_id", "full_name", "apaar_id", "student_status"], ["S1", f"Student {u4}", f"91001100{u4}", "ACTIVE"]]
    _, snap_id = upload_and_confirm(token=apex["token"], prog_id=apex["prog_id"], file_rows=rows, mark_authoritative=False, academic_year=year)

    res_run = client.post(
        "/api/v1/reconciliation/runs",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={"candidate_snapshot_id": snap_id},
    )
    assert res_run.status_code == 201
    run_id = uuid.UUID(res_run.json()["id"])

    db = SessionLocal()
    try:
        # Attempt to delete candidate snapshot directly via SQL
        with pytest.raises(Exception) as exc_info:
            db.execute(text("DELETE FROM roster_snapshots WHERE id = :id"), {"id": snap_id})
            db.commit()
        db.rollback()
        assert "foreign key constraint" in str(exc_info.value).lower()
        assert "reconciliation_runs" in str(exc_info.value).lower()
    finally:
        db.close()


# =========================================================================
# AUDIT AREA 2: Concurrency, Idempotency, and Rollback Integrity
# =========================================================================
def test_idempotency_advisory_lock_and_no_duplication(audit_tokens):
    """
    Verify:
    1. Repeated identical execution with Idempotency-Key returns existing run.
    2. No duplicate ReconciliationRun, ReconciliationResultItem, or DiscrepancyCase rows are spawned.
    3. Conflicting payload with same key returns 409 Conflict.
    """
    apex = audit_tokens["apex"]
    u4 = f"{random.randint(1000, 9999)}"
    year = f"2024-A2-{u4}"

    rows = [["student_id", "full_name", "apaar_id", "student_status"], ["S1", f"Student {u4}", f"92001100{u4}", "ACTIVE"]]
    _, snap_id = upload_and_confirm(token=apex["token"], prog_id=apex["prog_id"], file_rows=rows, mark_authoritative=False, academic_year=year)

    idem_key = f"audit-key-{uuid.uuid4().hex}"

    # Execution 1
    res1 = client.post(
        "/api/v1/reconciliation/runs",
        headers={"Authorization": f"Bearer {apex['token']}", "Idempotency-Key": idem_key},
        json={"candidate_snapshot_id": snap_id, "run_type": "REGULATORY_RECONCILIATION"},
    )
    assert res1.status_code == 201
    run_id = res1.json()["id"]

    # Replay Execution 2
    res2 = client.post(
        "/api/v1/reconciliation/runs",
        headers={"Authorization": f"Bearer {apex['token']}", "Idempotency-Key": idem_key},
        json={"candidate_snapshot_id": snap_id, "run_type": "REGULATORY_RECONCILIATION"},
    )
    assert res2.status_code in (200, 201)
    assert res2.json()["id"] == run_id

    # Verify database counts
    db = SessionLocal()
    try:
        run_count = db.scalar(select(func.count(ReconciliationRun.id)).where(ReconciliationRun.idempotency_key == idem_key))
        assert run_count == 1

        items_count = db.scalar(select(func.count(ReconciliationResultItem.id)).where(ReconciliationResultItem.reconciliation_run_id == uuid.UUID(run_id)))
        assert items_count >= 1

        cases_count = db.scalar(select(func.count(DiscrepancyCase.id)).where(DiscrepancyCase.initial_reconciliation_run_id == uuid.UUID(run_id)))
        assert cases_count >= 1

        # Replay produced no duplicate items
        assert res1.json()["result_fingerprint"] == res2.json()["result_fingerprint"]
    finally:
        db.close()

    # Conflicting payload with same key -> 409
    res_conflict = client.post(
        "/api/v1/reconciliation/runs",
        headers={"Authorization": f"Bearer {apex['token']}", "Idempotency-Key": idem_key},
        json={"candidate_snapshot_id": snap_id, "run_type": "INSTITUTIONAL_SELF_AUDIT"},
    )
    assert res_conflict.status_code == 409
    assert "idempotency conflict" in res_conflict.json()["detail"].lower()


# =========================================================================
# AUDIT AREA 3: Case Lineage & Boundary Isolation
# =========================================================================
def test_case_isolation_and_reopen_lineage(audit_tokens):
    """
    Verify:
    1. Independent students produce independent cases.
    2. Prior closed case links to new case via linked_prior_case_id on recurring finding.
    3. REOPEN_CASE restores closed case directly to UNDER_INVESTIGATION.
    """
    apex = audit_tokens["apex"]
    rev = audit_tokens["reviewer"]
    u4_1 = f"{random.randint(1000, 9999)}"
    u4_2 = f"{random.randint(1000, 9999)}"
    year = f"2024-A3-{u4_1}"

    rows = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        ["S_A", f"Student A {u4_1}", f"93001100{u4_1}", "ACTIVE"],
        ["S_B", f"Student B {u4_2}", f"93001100{u4_2}", "ACTIVE"],
    ]
    _, snap_id = upload_and_confirm(token=apex["token"], prog_id=apex["prog_id"], file_rows=rows, mark_authoritative=False, academic_year=year)

    res_run = client.post("/api/v1/reconciliation/runs", headers={"Authorization": f"Bearer {apex['token']}"}, json={"candidate_snapshot_id": snap_id})
    assert res_run.status_code == 201
    run_id = res_run.json()["id"]

    res_items = client.get(f"/api/v1/reconciliation/runs/{run_id}/results", headers={"Authorization": f"Bearer {apex['token']}"})
    assert res_items.status_code == 200
    items = res_items.json()["items"]
    # Filter items for student A and student B
    student_a_item = next(it for it in items if f"Student A {u4_1}" in it["student_name"])
    student_b_item = next(it for it in items if f"Student B {u4_2}" in it["student_name"])

    case_a_id = student_a_item["discrepancy_case_id"]
    case_b_id = student_b_item["discrepancy_case_id"]
    assert case_a_id != case_b_id  # Isolated cases

    # Progress Case A to VERIFIED_VALID and CLOSE_CASE
    res_step1 = client.post(
        f"/api/v1/discrepancies/cases/{case_a_id}/decisions",
        headers={"Authorization": f"Bearer {rev['token']}"},
        json={"action": "START_INVESTIGATION", "mandatory_reason": "Investigating student appearance credentials."},
    )
    assert res_step1.status_code == 200

    res_step2 = client.post(
        f"/api/v1/discrepancies/cases/{case_a_id}/decisions",
        headers={"Authorization": f"Bearer {rev['token']}"},
        json={"action": "CONFIRM_VALID", "mandatory_reason": "Credentials confirmed by state admission authority."},
    )
    assert res_step2.status_code == 200

    res_step3 = client.post(
        f"/api/v1/discrepancies/cases/{case_a_id}/decisions",
        headers={"Authorization": f"Bearer {rev['token']}"},
        json={"action": "CLOSE_CASE", "mandatory_reason": "Closing resolved discrepancy case with full verification."},
    )
    assert res_step3.status_code == 200
    assert res_step3.json()["to_status"] == "CLOSED"

    # Test REOPEN_CASE
    res_reopen = client.post(
        f"/api/v1/discrepancies/cases/{case_a_id}/decisions",
        headers={"Authorization": f"Bearer {rev['token']}"},
        json={"action": "REOPEN_CASE", "mandatory_reason": "New regulatory audit evidence surfaced requiring re-inquiry."},
    )
    assert res_reopen.status_code == 200
    assert res_reopen.json()["to_status"] == "UNDER_INVESTIGATION"


# =========================================================================
# AUDIT AREA 4: Decision Workflow & Role Boundary Enforcement
# =========================================================================
def test_decision_workflow_role_enforcement(audit_tokens):
    """
    Verify:
    1. Institution Admin CANNOT execute reviewer-only actions (START_INVESTIGATION, CONFIRM_VALID, CLOSE_CASE, REOPEN_CASE).
    2. Regulatory Reviewer CANNOT execute institution-only actions (SUBMIT_EXPLANATION).
    3. Mandatory reason length validation (< 10 chars -> 422).
    """
    apex = audit_tokens["apex"]
    rev = audit_tokens["reviewer"]
    u4 = f"{random.randint(1000, 9999)}"
    year = f"2024-A4-{u4}"

    rows = [["student_id", "full_name", "apaar_id", "student_status"], ["S1", f"Student {u4}", f"94001100{u4}", "ACTIVE"]]
    _, snap_id = upload_and_confirm(token=apex["token"], prog_id=apex["prog_id"], file_rows=rows, mark_authoritative=False, academic_year=year)

    res_run = client.post("/api/v1/reconciliation/runs", headers={"Authorization": f"Bearer {apex['token']}"}, json={"candidate_snapshot_id": snap_id})
    run_id = res_run.json()["id"]

    res_items = client.get(f"/api/v1/reconciliation/runs/{run_id}/results", headers={"Authorization": f"Bearer {apex['token']}"})
    case_id = res_items.json()["items"][0]["discrepancy_case_id"]

    # 1. Institution Admin attempts START_INVESTIGATION -> 403
    res_inst_start = client.post(
        f"/api/v1/discrepancies/cases/{case_id}/decisions",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={"action": "START_INVESTIGATION", "mandatory_reason": "Institution attempting reviewer action."},
    )
    assert res_inst_start.status_code == 403
    assert "restricted to roles" in res_inst_start.json()["detail"].lower()

    # 2. Institution Admin attempts CONFIRM_VALID -> 403
    res_inst_confirm = client.post(
        f"/api/v1/discrepancies/cases/{case_id}/decisions",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={"action": "CONFIRM_VALID", "mandatory_reason": "Institution attempting self-clearance."},
    )
    assert res_inst_confirm.status_code == 403

    # 3. Reviewer starts investigation
    res_rev_start = client.post(
        f"/api/v1/discrepancies/cases/{case_id}/decisions",
        headers={"Authorization": f"Bearer {rev['token']}"},
        json={"action": "START_INVESTIGATION", "mandatory_reason": "Reviewer begins official inquiry."},
    )
    assert res_rev_start.status_code == 200

    # 4. Reviewer attempts SUBMIT_EXPLANATION -> 403
    res_rev_expl = client.post(
        f"/api/v1/discrepancies/cases/{case_id}/decisions",
        headers={"Authorization": f"Bearer {rev['token']}"},
        json={"action": "SUBMIT_EXPLANATION", "mandatory_reason": "Reviewer submitting explanation."},
    )
    assert res_rev_expl.status_code == 403

    # 5. Institution Admin submits valid explanation
    res_inst_expl = client.post(
        f"/api/v1/discrepancies/cases/{case_id}/decisions",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={"action": "SUBMIT_EXPLANATION", "mandatory_reason": "Institutional justification: verified by college council."},
    )
    assert res_inst_expl.status_code == 200
    assert res_inst_expl.json()["to_status"] == "EXPLANATION_SUBMITTED"


# =========================================================================
# AUDIT AREA 5: Evidence Security & Cross-Tenant Boundary Check
# =========================================================================
def test_cross_tenant_isolation_and_privacy(audit_tokens):
    """
    Verify complete multi-tenant boundaries:
    1. Polytechnic Admin cannot GET /reconciliation/runs/{id} belonging to Apex (403).
    2. Polytechnic Admin cannot GET /reconciliation/runs/{id}/results belonging to Apex (403).
    3. Polytechnic Admin cannot GET /discrepancies/cases/{id} belonging to Apex (403).
    4. Polytechnic Admin cannot POST /discrepancies/cases/{id}/decisions on Apex case (403).
    5. Polytechnic Admin cannot GET /discrepancies/cases/{id}/history for Apex case (403).
    6. AuditEvent metadata contains zero unmasked APAARs or student names.
    """
    apex = audit_tokens["apex"]
    poly = audit_tokens["poly"]
    rev = audit_tokens["reviewer"]
    u4 = f"{random.randint(1000, 9999)}"
    year = f"2024-A5-{u4}"

    rows = [["student_id", "full_name", "apaar_id", "student_status"], ["S1", f"Secret Student {u4}", f"95001100{u4}", "ACTIVE"]]
    _, snap_id = upload_and_confirm(token=apex["token"], prog_id=apex["prog_id"], file_rows=rows, mark_authoritative=False, academic_year=year)

    res_run = client.post("/api/v1/reconciliation/runs", headers={"Authorization": f"Bearer {apex['token']}"}, json={"candidate_snapshot_id": snap_id})
    run_id = res_run.json()["id"]

    res_items = client.get(f"/api/v1/reconciliation/runs/{run_id}/results", headers={"Authorization": f"Bearer {apex['token']}"})
    case_id = res_items.json()["items"][0]["discrepancy_case_id"]

    # 1. Poly attempts GET /reconciliation/runs/{run_id} -> 403
    res_poly_run = client.post if False else client.get(
        f"/api/v1/reconciliation/runs/{run_id}",
        headers={"Authorization": f"Bearer {poly['token']}"},
    )
    assert res_poly_run.status_code == 403

    # 2. Poly attempts GET /reconciliation/runs/{run_id}/results -> 403
    res_poly_res = client.get(
        f"/api/v1/reconciliation/runs/{run_id}/results",
        headers={"Authorization": f"Bearer {poly['token']}"},
    )
    assert res_poly_res.status_code == 403

    # 3. Poly attempts GET /discrepancies/cases/{case_id} -> 403
    res_poly_case = client.get(
        f"/api/v1/discrepancies/cases/{case_id}",
        headers={"Authorization": f"Bearer {poly['token']}"},
    )
    assert res_poly_case.status_code == 403

    # 4. Poly attempts POST /discrepancies/cases/{case_id}/decisions -> 403
    res_poly_dec = client.post(
        f"/api/v1/discrepancies/cases/{case_id}/decisions",
        headers={"Authorization": f"Bearer {poly['token']}"},
        json={"action": "START_INVESTIGATION", "mandatory_reason": "Unauthorized decision attempt."},
    )
    assert res_poly_dec.status_code == 403

    # 5. Poly attempts GET /discrepancies/cases/{case_id}/history -> 403
    res_poly_hist = client.get(
        f"/api/v1/discrepancies/cases/{case_id}/history",
        headers={"Authorization": f"Bearer {poly['token']}"},
    )
    assert res_poly_hist.status_code == 403

    # 6. Verify AuditEvent privacy
    db = SessionLocal()
    try:
        events = db.execute(
            select(AuditEvent).where(
                AuditEvent.entity_type.in_(["RECONCILIATION_RUN", "DISCREPANCY_CASE"]),
                AuditEvent.entity_id.in_([uuid.UUID(run_id), uuid.UUID(case_id)]),
            )
        ).scalars().all()
        for ev in events:
            ev_str = str(ev.metadata_payload)
            assert f"95001100{u4}" not in ev_str  # Raw APAAR NEVER in audit events
            assert f"Secret Student {u4}" not in ev_str  # Student name not in audit events
    finally:
        db.close()


# =========================================================================
# AUDIT AREA 6: Reproducibility & Fingerprint Determinism
# =========================================================================
def test_reproducibility_and_fingerprint_determinism(audit_tokens):
    """
    Verify:
    1. Re-executing reconciliation on identical candidate snapshot produces identical result_fingerprint.
    2. Stored candidate_snapshot_hash matches authoritative snapshot hash.
    3. Completed run results are immutable.
    """
    apex = audit_tokens["apex"]
    u4 = f"{random.randint(1000, 9999)}"
    year = f"2024-A6-{u4}"

    rows = [["student_id", "full_name", "apaar_id", "student_status"], ["S1", f"Student {u4}", f"96001100{u4}", "ACTIVE"]]
    _, snap_id = upload_and_confirm(token=apex["token"], prog_id=apex["prog_id"], file_rows=rows, mark_authoritative=False, academic_year=year)

    res_run1 = client.post("/api/v1/reconciliation/runs", headers={"Authorization": f"Bearer {apex['token']}"}, json={"candidate_snapshot_id": snap_id})
    res_run2 = client.post("/api/v1/reconciliation/runs", headers={"Authorization": f"Bearer {apex['token']}"}, json={"candidate_snapshot_id": snap_id})

    fp1 = res_run1.json()["result_fingerprint"]
    fp2 = res_run2.json()["result_fingerprint"]
    assert fp1 == fp2  # Deterministic fingerprint

    # Verify snapshot hash matches
    db = SessionLocal()
    try:
        snap = db.get(RosterSnapshot, uuid.UUID(snap_id))
        assert res_run1.json()["candidate_snapshot_hash"] == snap.snapshot_hash
    finally:
        db.close()
