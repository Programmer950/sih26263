"""Tests for Milestone 3 Phase 3C: Transactional Ingestion & Concurrency-Safe Provenance."""

import pytest
import uuid
import io
import os
import openpyxl
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select, func
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.models import (
    StudentIdentity,
    InstitutionStudentRecord,
    AnnualRosterObservation,
    RosterSnapshot,
    SourceSubmission,
    SourceSubmissionRecord,
    SubmissionPreview,
    Programme,
    Institution,
)
from app.services.storage_service import StorageService
import app.services.ingestion_service as ingestion_module

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
        "reviewer": {"token": reviewer_token},
    }


def create_sample_csv(rows_data: list) -> io.BytesIO:
    """Helper to create an in-memory CSV file."""
    output = io.StringIO()
    import csv
    writer = csv.writer(output)
    for r in rows_data:
        writer.writerow(r)
    return io.BytesIO(output.getvalue().encode("utf-8"))


def create_sample_xlsx(rows_data: list) -> io.BytesIO:
    """Helper to create an in-memory XLSX file."""
    wb = openpyxl.Workbook()
    ws = wb.active
    for r in rows_data:
        ws.append(r)
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return stream


def upload_and_preview(token: str, prog_id: str, file_tuple: tuple, mapping: dict, academic_year: str = "2024-25"):
    """Helper to upload file and generate active preview."""
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

    res_prev = client.post(
        f"/api/v1/submissions/{sub_id}/preview",
        headers={"Authorization": f"Bearer {token}"},
        json={"column_mapping": mapping},
    )
    assert res_prev.status_code == 200, res_prev.text
    preview_id = res_prev.json()["preview_id"]

    return sub_id, preview_id


# =========================================================================
# Scenario 1: Successful CSV Ingestion
# =========================================================================
def test_scenario_1_successful_csv_ingestion(seeded_tokens):
    """
    Scenario 1:
    - Successful CSV ingestion converts validated preview into canonical repository records.
    - SourceSubmission status transitions to COMMITTED.
    - Creates SourceSubmissionRecords, StudentIdentities, InstitutionStudentRecords,
      AnnualRosterObservations, and an ACTIVE authoritative RosterSnapshot.
    """
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]
    csv_rows = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        [f"CSE-{uid}-01", "Aarav Sharma", "123456789012", "ACTIVE"],
        [f"CSE-{uid}-02", "Diya Patel", "987654321098", "ACTIVE"],
        [f"CSE-{uid}-03", "Rohan Mehta", "456789012345", "ACTIVE"],
    ]
    mapping = {"student_id": "student_id", "full_name": "full_name", "apaar_id": "apaar_id", "student_status": "student_status"}
    sub_id, prev_id = upload_and_preview(
        apex["token"], apex["prog_id"], (f"roster_{uid}.csv", create_sample_csv(csv_rows), "text/csv"), mapping, academic_year=f"2024-{uid[:4]}"
    )

    res_confirm = client.post(
        f"/api/v1/submissions/{sub_id}/confirm",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={
            "preview_id": prev_id,
            "column_mapping": mapping,
            "mark_as_authoritative": True,
            "completeness_status": "COMPLETE",
        },
    )
    assert res_confirm.status_code == 200, res_confirm.text
    data = res_confirm.json()
    assert data["submission_id"] == sub_id
    assert data["submission_status"] == "COMMITTED"
    assert data["total_records_processed"] == 3
    assert data["valid_records"] == 3
    assert data["snapshot_status"] == "ACTIVE"
    assert data["completeness_status"] == "COMPLETE"
    assert data["is_authoritative"] is True

    # Database Verification
    db = SessionLocal()
    try:
        sub = db.execute(select(SourceSubmission).where(SourceSubmission.id == uuid.UUID(sub_id))).scalar_one()
        assert sub.submission_status == "COMMITTED"
        assert sub.committed_at is not None

        records = db.execute(select(SourceSubmissionRecord).where(SourceSubmissionRecord.submission_id == sub.id)).scalars().all()
        assert len(records) == 3
        for r in records:
            assert r.validation_status == "VALID"
            assert r.resolved_student_identity_id is not None
            assert r.resolved_institution_student_record_id is not None

        obs = db.execute(select(AnnualRosterObservation).where(AnnualRosterObservation.source_submission_id == sub.id)).scalars().all()
        assert len(obs) == 3

        snap = db.execute(select(RosterSnapshot).where(RosterSnapshot.id == uuid.UUID(data["snapshot_id"]))).scalar_one()
        assert snap.is_authoritative is True
        assert snap.lifecycle_status == "ACTIVE"
        assert snap.declared_headcount == 3
        assert snap.observed_headcount == 3
    finally:
        db.close()


# =========================================================================
# Scenario 2: Successful XLSX Ingestion
# =========================================================================
def test_scenario_2_successful_xlsx_ingestion(seeded_tokens):
    """
    Scenario 2:
    - Successful XLSX ingestion creates complete canonical records and active snapshot.
    """
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]
    xlsx_rows = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        [f"ECE-{uid}-01", "Kavya Iyer", "333444555666", "ACTIVE"],
        [f"ECE-{uid}-02", "Aditya Nair", "777888999000", "ACTIVE"],
    ]
    mapping = {"student_id": "student_id", "full_name": "full_name", "apaar_id": "apaar_id", "student_status": "student_status"}
    sub_id, prev_id = upload_and_preview(
        apex["token"], apex["prog_id"], (f"roster_{uid}.xlsx", create_sample_xlsx(xlsx_rows), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"), mapping, academic_year=f"2024-{uid[:4]}"
    )

    res_confirm = client.post(
        f"/api/v1/submissions/{sub_id}/confirm",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={"preview_id": prev_id, "column_mapping": mapping, "mark_as_authoritative": True, "completeness_status": "COMPLETE"},
    )
    assert res_confirm.status_code == 200, res_confirm.text
    data = res_confirm.json()
    assert data["submission_status"] == "COMMITTED"
    assert data["total_records_processed"] == 2


# =========================================================================
# Scenario 3: Repeated Valid APAAR Resolves to Exact Same StudentIdentity
# =========================================================================
def test_scenario_3_repeated_apaar_resolves_to_same_identity(seeded_tokens):
    """
    Scenario 3:
    - Multiple records with the same valid APAAR resolve to the exact same StudentIdentity.
    - Zero duplicate identities created.
    """
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]
    shared_apaar = "111222333444"
    csv_rows = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        [f"SEC-A-{uid}", "Pooja Verma", shared_apaar, "ACTIVE"],
        [f"SEC-B-{uid}", "Pooja Verma Junior", shared_apaar, "ACTIVE"],
    ]
    mapping = {"student_id": "student_id", "full_name": "full_name", "apaar_id": "apaar_id", "student_status": "student_status"}
    sub_id, prev_id = upload_and_preview(
        apex["token"], apex["prog_id"], (f"roster_dup_apaar_{uid}.csv", create_sample_csv(csv_rows), "text/csv"), mapping, academic_year=f"2024-{uid[:4]}"
    )

    res = client.post(
        f"/api/v1/submissions/{sub_id}/confirm",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={"preview_id": prev_id, "column_mapping": mapping},
    )
    assert res.status_code == 200

    db = SessionLocal()
    try:
        records = db.execute(
            select(SourceSubmissionRecord).where(SourceSubmissionRecord.submission_id == uuid.UUID(sub_id))
        ).scalars().all()
        assert len(records) == 2
        # Both source records must point to the identical StudentIdentity id
        assert records[0].resolved_student_identity_id == records[1].resolved_student_identity_id

        obs = db.execute(
            select(AnnualRosterObservation).where(AnnualRosterObservation.source_submission_id == uuid.UUID(sub_id))
        ).scalars().all()
        assert len(obs) == 2
        assert obs[0].student_identity_id == obs[1].student_identity_id
    finally:
        db.close()


# =========================================================================
# Scenario 4: Missing APAAR Creates Provisional StudentIdentity
# =========================================================================
def test_scenario_4_missing_apaar_handling(seeded_tokens):
    """
    Scenario 4:
    - Record with missing APAAR creates provisional StudentIdentity with identity_status='MISSING_APAAR'.
    """
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]
    csv_rows = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        [f"NO-APAAR-{uid}", "Suresh Raina", "", "ACTIVE"],
    ]
    mapping = {"student_id": "student_id", "full_name": "full_name", "apaar_id": "apaar_id", "student_status": "student_status"}
    sub_id, prev_id = upload_and_preview(
        apex["token"], apex["prog_id"], (f"roster_no_apaar_{uid}.csv", create_sample_csv(csv_rows), "text/csv"), mapping, academic_year=f"2024-{uid[:4]}"
    )

    res = client.post(
        f"/api/v1/submissions/{sub_id}/confirm",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={"preview_id": prev_id, "column_mapping": mapping},
    )
    assert res.status_code == 200

    db = SessionLocal()
    try:
        rec = db.execute(
            select(SourceSubmissionRecord).where(SourceSubmissionRecord.submission_id == uuid.UUID(sub_id))
        ).scalar_one()
        identity = db.execute(
            select(StudentIdentity).where(StudentIdentity.id == rec.resolved_student_identity_id)
        ).scalar_one()

        assert identity.identity_status == "MISSING_APAAR"
        assert identity.encrypted_apaar_reference is None
        assert identity.apaar_blind_index is None
    finally:
        db.close()


# =========================================================================
# Scenario 5: Invalid APAAR Format Creates Provisional StudentIdentity
# =========================================================================
def test_scenario_5_invalid_apaar_format_handling(seeded_tokens):
    """
    Scenario 5:
    - Record with invalid APAAR format creates provisional StudentIdentity with identity_status='INVALID_FORMAT'.
    """
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]
    csv_rows = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        [f"BAD-APAAR-{uid}", "Manish Pandey", "1234INVALID9", "ACTIVE"],
    ]
    mapping = {"student_id": "student_id", "full_name": "full_name", "apaar_id": "apaar_id", "student_status": "student_status"}
    sub_id, prev_id = upload_and_preview(
        apex["token"], apex["prog_id"], (f"roster_bad_apaar_{uid}.csv", create_sample_csv(csv_rows), "text/csv"), mapping, academic_year=f"2024-{uid[:4]}"
    )

    res = client.post(
        f"/api/v1/submissions/{sub_id}/confirm",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={"preview_id": prev_id, "column_mapping": mapping},
    )
    assert res.status_code == 200

    db = SessionLocal()
    try:
        rec = db.execute(
            select(SourceSubmissionRecord).where(SourceSubmissionRecord.submission_id == uuid.UUID(sub_id))
        ).scalar_one()
        identity = db.execute(
            select(StudentIdentity).where(StudentIdentity.id == rec.resolved_student_identity_id)
        ).scalar_one()

        assert identity.identity_status == "INVALID_FORMAT"
        assert identity.encrypted_apaar_reference is None
        assert identity.apaar_blind_index is None
    finally:
        db.close()


# =========================================================================
# Scenario 6: Weak Attribute Non-Merging
# =========================================================================
def test_scenario_6_weak_attribute_non_merging(seeded_tokens):
    """
    Scenario 6:
    - Identical name with different or missing APAAR creates separate StudentIdentities.
    - Weak attributes (names alone) never trigger identity merging.
    """
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]
    csv_rows = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        [f"NAME-MERGE-A-{uid}", "Rajesh Kumar", "112233445566", "ACTIVE"],
        [f"NAME-MERGE-B-{uid}", "Rajesh Kumar", "998877665544", "ACTIVE"],
        [f"NAME-MERGE-C-{uid}", "Rajesh Kumar", "", "ACTIVE"],
    ]
    mapping = {"student_id": "student_id", "full_name": "full_name", "apaar_id": "apaar_id", "student_status": "student_status"}
    sub_id, prev_id = upload_and_preview(
        apex["token"], apex["prog_id"], (f"roster_weak_attr_{uid}.csv", create_sample_csv(csv_rows), "text/csv"), mapping, academic_year=f"2024-{uid[:4]}"
    )

    res = client.post(
        f"/api/v1/submissions/{sub_id}/confirm",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={"preview_id": prev_id, "column_mapping": mapping},
    )
    assert res.status_code == 200

    db = SessionLocal()
    try:
        records = db.execute(
            select(SourceSubmissionRecord).where(SourceSubmissionRecord.submission_id == uuid.UUID(sub_id))
        ).scalars().all()
        assert len(records) == 3

        id_set = {r.resolved_student_identity_id for r in records}
        # All three must be distinct identities despite identical names!
        assert len(id_set) == 3
    finally:
        db.close()


# =========================================================================
# Scenario 7: Complete Provenance Verification
# =========================================================================
def test_scenario_7_complete_provenance(seeded_tokens):
    """
    Scenario 7:
    - Complete provenance verification: Observation links source_submission_id,
      source_record_id, institution_id, programme_id, academic_year, and source row number.
    """
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]
    academic_year = f"2024-{uid[:4]}"
    csv_rows = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        [f"PROV-{uid}-01", "Priya Sen", "222333444555", "ACTIVE"],
    ]
    mapping = {"student_id": "student_id", "full_name": "full_name", "apaar_id": "apaar_id", "student_status": "student_status"}
    sub_id, prev_id = upload_and_preview(
        apex["token"], apex["prog_id"], (f"roster_prov_{uid}.csv", create_sample_csv(csv_rows), "text/csv"), mapping, academic_year=academic_year
    )

    res = client.post(
        f"/api/v1/submissions/{sub_id}/confirm",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={"preview_id": prev_id, "column_mapping": mapping},
    )
    assert res.status_code == 200

    db = SessionLocal()
    try:
        obs = db.execute(
            select(AnnualRosterObservation).where(AnnualRosterObservation.source_submission_id == uuid.UUID(sub_id))
        ).scalar_one()

        rec = db.execute(
            select(SourceSubmissionRecord).where(SourceSubmissionRecord.id == obs.source_record_id)
        ).scalar_one()

        assert obs.source_submission_id == uuid.UUID(sub_id)
        assert obs.source_record_id == rec.id
        assert obs.institution_id == uuid.UUID(apex["inst_id"])
        assert obs.programme_id == uuid.UUID(apex["prog_id"])
        assert obs.academic_year == academic_year
        assert obs.observation_metadata["source_row"] == 1
        assert obs.observation_metadata["raw_identifier"] == f"PROV-{uid}-01"
    finally:
        db.close()


# =========================================================================
# Scenario 8: Atomic Rollback on Source Record Failure
# =========================================================================
def test_scenario_8_atomic_rollback_after_source_record_failure(seeded_tokens, monkeypatch):
    """
    Scenario 8:
    - Simulated failure during source record creation triggers atomic rollback.
    - Zero source submission records, observations, or snapshots created.
    """
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]
    csv_rows = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        [f"FAIL-REC-{uid}-01", "Fail Test 1", "333222111000", "ACTIVE"],
        [f"FAIL-REC-{uid}-02", "Fail Test 2", "444333222111", "ACTIVE"],
    ]
    mapping = {"student_id": "student_id", "full_name": "full_name", "apaar_id": "apaar_id", "student_status": "student_status"}
    sub_id, prev_id = upload_and_preview(
        apex["token"], apex["prog_id"], (f"roster_fail_rec_{uid}.csv", create_sample_csv(csv_rows), "text/csv"), mapping, academic_year=f"2024-{uid[:4]}"
    )

    # Monkeypatch SourceSubmissionRecord to fail on second instantiation
    original_init = SourceSubmissionRecord.__init__
    call_count = [0]

    def failing_init(self, *args, **kwargs):
        call_count[0] += 1
        if call_count[0] >= 2:
            raise RuntimeError("Simulated failure during SourceSubmissionRecord creation")
        original_init(self, *args, **kwargs)

    monkeypatch.setattr(SourceSubmissionRecord, "__init__", failing_init)

    res = client.post(
        f"/api/v1/submissions/{sub_id}/confirm",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={"preview_id": prev_id, "column_mapping": mapping},
    )
    assert res.status_code == 500
    assert "Simulated failure" in res.text

    db = SessionLocal()
    try:
        # Verify 0 records, 0 observations, 0 snapshots persisted
        rec_count = db.execute(
            select(func.count(SourceSubmissionRecord.id)).where(SourceSubmissionRecord.submission_id == uuid.UUID(sub_id))
        ).scalar()
        assert rec_count == 0

        obs_count = db.execute(
            select(func.count(AnnualRosterObservation.id)).where(AnnualRosterObservation.source_submission_id == uuid.UUID(sub_id))
        ).scalar()
        assert obs_count == 0

        snap_count = db.execute(
            select(func.count(RosterSnapshot.id)).where(RosterSnapshot.source_submission_id == uuid.UUID(sub_id))
        ).scalar()
        assert snap_count == 0
    finally:
        db.close()


# =========================================================================
# Scenario 9: Atomic Rollback on Identity Resolution Failure
# =========================================================================
def test_scenario_9_atomic_rollback_after_identity_resolution_failure(seeded_tokens, monkeypatch):
    """
    Scenario 9:
    - Simulated failure during identity resolution triggers atomic rollback.
    """
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]
    csv_rows = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        [f"FAIL-ID-{uid}", "Fail Identity", "555666777888", "ACTIVE"],
    ]
    mapping = {"student_id": "student_id", "full_name": "full_name", "apaar_id": "apaar_id", "student_status": "student_status"}
    sub_id, prev_id = upload_and_preview(
        apex["token"], apex["prog_id"], (f"roster_fail_id_{uid}.csv", create_sample_csv(csv_rows), "text/csv"), mapping, academic_year=f"2024-{uid[:4]}"
    )

    def failing_validate_apaar(apaar_str):
        raise RuntimeError("Simulated KMS cryptographic failure during identity resolution")

    monkeypatch.setattr(ingestion_module, "validate_apaar_format", failing_validate_apaar)

    res = client.post(
        f"/api/v1/submissions/{sub_id}/confirm",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={"preview_id": prev_id, "column_mapping": mapping},
    )
    assert res.status_code == 500
    assert "Simulated KMS" in res.text

    db = SessionLocal()
    try:
        rec_count = db.execute(
            select(func.count(SourceSubmissionRecord.id)).where(SourceSubmissionRecord.submission_id == uuid.UUID(sub_id))
        ).scalar()
        assert rec_count == 0
    finally:
        db.close()


# =========================================================================
# Scenario 10: Atomic Rollback on Observation Failure
# =========================================================================
def test_scenario_10_atomic_rollback_after_observation_failure(seeded_tokens, monkeypatch):
    """
    Scenario 10:
    - Simulated failure during observation creation triggers atomic rollback.
    """
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]
    csv_rows = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        [f"FAIL-OBS-{uid}", "Fail Observation", "666777888999", "ACTIVE"],
    ]
    mapping = {"student_id": "student_id", "full_name": "full_name", "apaar_id": "apaar_id", "student_status": "student_status"}
    sub_id, prev_id = upload_and_preview(
        apex["token"], apex["prog_id"], (f"roster_fail_obs_{uid}.csv", create_sample_csv(csv_rows), "text/csv"), mapping, academic_year=f"2024-{uid[:4]}"
    )

    def failing_obs_init(self, *args, **kwargs):
        raise RuntimeError("Simulated foreign key or observation persistence fault")

    monkeypatch.setattr(AnnualRosterObservation, "__init__", failing_obs_init)

    res = client.post(
        f"/api/v1/submissions/{sub_id}/confirm",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={"preview_id": prev_id, "column_mapping": mapping},
    )
    assert res.status_code == 500

    db = SessionLocal()
    try:
        obs_count = db.execute(
            select(func.count(AnnualRosterObservation.id)).where(AnnualRosterObservation.source_submission_id == uuid.UUID(sub_id))
        ).scalar()
        assert obs_count == 0
    finally:
        db.close()


# =========================================================================
# Scenario 11: Failed Status Persistence After Rollback (Transaction B)
# =========================================================================
def test_scenario_11_failed_status_persistence_after_rollback(seeded_tokens, monkeypatch):
    """
    Scenario 11:
    - After rollback of Transaction A, Transaction B in an isolated session
      records submission_status='FAILED' and sanitized failure_reason in the database.
    - Raw uploaded file evidence is preserved in storage.
    """
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]
    csv_rows = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        [f"FAIL-TXB-{uid}", "TxB Test Student", "777666555444", "ACTIVE"],
    ]
    mapping = {"student_id": "student_id", "full_name": "full_name", "apaar_id": "apaar_id", "student_status": "student_status"}
    sub_id, prev_id = upload_and_preview(
        apex["token"], apex["prog_id"], (f"roster_fail_txb_{uid}.csv", create_sample_csv(csv_rows), "text/csv"), mapping, academic_year=f"2024-{uid[:4]}"
    )

    def failing_validate_row(*args, **kwargs):
        raise RuntimeError("Simulated validation engine crash inside Transaction A")

    monkeypatch.setattr("app.services.preview_service.PreviewService.validate_row", failing_validate_row)

    res = client.post(
        f"/api/v1/submissions/{sub_id}/confirm",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={"preview_id": prev_id, "column_mapping": mapping},
    )
    assert res.status_code == 500

    db = SessionLocal()
    try:
        sub = db.execute(select(SourceSubmission).where(SourceSubmission.id == uuid.UUID(sub_id))).scalar_one()
        assert sub.submission_status == "FAILED"
        assert sub.failure_reason is not None
        assert "Simulated validation engine crash" in sub.failure_reason

        # Verify raw storage file still exists
        resolved_path = StorageService.resolve_safe_path(sub.storage_key)
        assert os.path.exists(resolved_path)
    finally:
        db.close()


# =========================================================================
# Scenario 12: Concurrent Confirmation Attempts on Same Submission
# =========================================================================
def test_scenario_12_concurrent_confirmation_of_one_submission(seeded_tokens):
    """
    Scenario 12:
    - Concurrent confirmation attempts on the same submission:
      Row locking guarantees exactly one succeeds (200 COMMITTED),
      and the second returns 409 Conflict.
    """
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]
    csv_rows = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        [f"CONC-SAME-{uid}-01", "Student One", "888999000111", "ACTIVE"],
        [f"CONC-SAME-{uid}-02", "Student Two", "888999000222", "ACTIVE"],
    ]
    mapping = {"student_id": "student_id", "full_name": "full_name", "apaar_id": "apaar_id", "student_status": "student_status"}
    sub_id, prev_id = upload_and_preview(
        apex["token"], apex["prog_id"], (f"roster_conc_same_{uid}.csv", create_sample_csv(csv_rows), "text/csv"), mapping, academic_year=f"2024-{uid[:4]}"
    )

    def do_confirm():
        c = TestClient(app)
        return c.post(
            f"/api/v1/submissions/{sub_id}/confirm",
            headers={"Authorization": f"Bearer {apex['token']}"},
            json={"preview_id": prev_id, "column_mapping": mapping},
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(do_confirm)
        f2 = executor.submit(do_confirm)
        res1 = f1.result()
        res2 = f2.result()

    statuses = sorted([res1.status_code, res2.status_code])
    assert statuses == [200, 409], f"Expected [200, 409], got {statuses}: {res1.text} | {res2.text}"

    db = SessionLocal()
    try:
        snap_count = db.execute(
            select(func.count(RosterSnapshot.id)).where(RosterSnapshot.source_submission_id == uuid.UUID(sub_id))
        ).scalar()
        assert snap_count == 1
    finally:
        db.close()


# =========================================================================
# Scenario 13: Concurrent Confirmation Across Separate Submissions Same APAAR
# =========================================================================
def test_scenario_13_concurrent_identity_resolution_same_apaar(seeded_tokens):
    """
    Scenario 13:
    - Two separate submissions containing the same APAAR confirmed concurrently:
      Both succeed (200) and resolve to the exact same canonical StudentIdentity
      without duplicate key / integrity error crashes.
    """
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]
    shared_apaar = "999111222333"

    # Submission A
    csv_rows_a = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        [f"CONC-APAAR-A-{uid}", "Shared Student", shared_apaar, "ACTIVE"],
    ]
    mapping = {"student_id": "student_id", "full_name": "full_name", "apaar_id": "apaar_id", "student_status": "student_status"}
    sub_id_a, prev_id_a = upload_and_preview(
        apex["token"], apex["prog_id"], (f"roster_conc_a_{uid}.csv", create_sample_csv(csv_rows_a), "text/csv"), mapping, academic_year=f"2024-A{uid[:3]}"
    )

    # Submission B (different academic year to avoid duplicate context conflict)
    csv_rows_b = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        [f"CONC-APAAR-B-{uid}", "Shared Student", shared_apaar, "ACTIVE"],
    ]
    sub_id_b, prev_id_b = upload_and_preview(
        apex["token"], apex["prog_id"], (f"roster_conc_b_{uid}.csv", create_sample_csv(csv_rows_b), "text/csv"), mapping, academic_year=f"2024-B{uid[:3]}"
    )

    def do_confirm_a():
        c = TestClient(app)
        return c.post(
            f"/api/v1/submissions/{sub_id_a}/confirm",
            headers={"Authorization": f"Bearer {apex['token']}"},
            json={"preview_id": prev_id_a, "column_mapping": mapping},
        )

    def do_confirm_b():
        c = TestClient(app)
        return c.post(
            f"/api/v1/submissions/{sub_id_b}/confirm",
            headers={"Authorization": f"Bearer {apex['token']}"},
            json={"preview_id": prev_id_b, "column_mapping": mapping},
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        fa = executor.submit(do_confirm_a)
        fb = executor.submit(do_confirm_b)
        res_a = fa.result()
        res_b = fb.result()

    assert res_a.status_code == 200, res_a.text
    assert res_b.status_code == 200, res_b.text

    db = SessionLocal()
    try:
        rec_a = db.execute(
            select(SourceSubmissionRecord).where(SourceSubmissionRecord.submission_id == uuid.UUID(sub_id_a))
        ).scalar_one()
        rec_b = db.execute(
            select(SourceSubmissionRecord).where(SourceSubmissionRecord.submission_id == uuid.UUID(sub_id_b))
        ).scalar_one()

        assert rec_a.resolved_student_identity_id == rec_b.resolved_student_identity_id
    finally:
        db.close()


# =========================================================================
# Scenario 14: Tenancy Isolation on Confirmation
# =========================================================================
def test_scenario_14_tenant_isolation_confirm(seeded_tokens):
    """
    Scenario 14:
    - Institution Admin cannot confirm an external institution's submission (403 Forbidden).
    """
    apex = seeded_tokens["apex"]
    poly = seeded_tokens["poly"]
    uid = uuid.uuid4().hex[:6]

    csv_rows = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        [f"TENANT-{uid}", "Tenant Student", "121212121212", "ACTIVE"],
    ]
    mapping = {"student_id": "student_id", "full_name": "full_name", "apaar_id": "apaar_id", "student_status": "student_status"}
    sub_id, prev_id = upload_and_preview(
        apex["token"], apex["prog_id"], (f"roster_tenant_{uid}.csv", create_sample_csv(csv_rows), "text/csv"), mapping, academic_year=f"2024-{uid[:4]}"
    )

    # Polytechnic Admin attempts to confirm Apex submission
    res = client.post(
        f"/api/v1/submissions/{sub_id}/confirm",
        headers={"Authorization": f"Bearer {poly['token']}"},
        json={"preview_id": prev_id, "column_mapping": mapping},
    )
    assert res.status_code == 403
    assert "Tenancy Violation" in res.text


# =========================================================================
# Scenario 15: Cancelled Submission Cannot Be Confirmed
# =========================================================================
def test_scenario_15_cancelled_submission_rejection(seeded_tokens):
    """
    Scenario 15:
    - Confirming a CANCELLED submission returns 400 Bad Request.
    """
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]
    csv_rows = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        [f"CANCEL-{uid}", "Cancel Student", "232323232323", "ACTIVE"],
    ]
    mapping = {"student_id": "student_id", "full_name": "full_name", "apaar_id": "apaar_id", "student_status": "student_status"}
    sub_id, prev_id = upload_and_preview(
        apex["token"], apex["prog_id"], (f"roster_cancel_{uid}.csv", create_sample_csv(csv_rows), "text/csv"), mapping, academic_year=f"2024-{uid[:4]}"
    )

    # Cancel submission
    res_cancel = client.post(f"/api/v1/submissions/{sub_id}/cancel", headers={"Authorization": f"Bearer {apex['token']}"})
    assert res_cancel.status_code == 200

    # Attempt to confirm
    res_confirm = client.post(
        f"/api/v1/submissions/{sub_id}/confirm",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={"preview_id": prev_id, "column_mapping": mapping},
    )
    assert res_confirm.status_code == 400
    assert "Cannot confirm a cancelled submission" in res_confirm.text


# =========================================================================
# Scenario 16: Stale Preview Rejection
# =========================================================================
def test_scenario_16_stale_preview_rejection(seeded_tokens):
    """
    Scenario 16:
    - Confirming with an inactive/stale preview returns 409 Conflict.
    """
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]
    csv_rows = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        [f"STALE-{uid}", "Stale Student", "343434343434", "ACTIVE"],
    ]
    mapping1 = {"student_id": "student_id", "full_name": "full_name", "apaar_id": "apaar_id", "student_status": "student_status"}
    sub_id, prev_id_1 = upload_and_preview(
        apex["token"], apex["prog_id"], (f"roster_stale_{uid}.csv", create_sample_csv(csv_rows), "text/csv"), mapping1, academic_year=f"2024-{uid[:4]}"
    )

    # Generate a second preview (deactivates preview 1)
    mapping2 = {"student_id": "student_id", "full_name": "full_name"}
    res_prev2 = client.post(
        f"/api/v1/submissions/{sub_id}/preview",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={"column_mapping": mapping2},
    )
    assert res_prev2.status_code == 200

    # Attempt to confirm with preview 1
    res_confirm = client.post(
        f"/api/v1/submissions/{sub_id}/confirm",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={"preview_id": prev_id_1, "column_mapping": mapping1},
    )
    assert res_confirm.status_code == 409
    assert "Stale preview" in res_confirm.text


# =========================================================================
# Scenario 17: Mapping Hash Mismatch Rejection
# =========================================================================
def test_scenario_17_mapping_hash_mismatch_rejection(seeded_tokens):
    """
    Scenario 17:
    - Calling confirm with a modified column mapping without generating a new preview
      returns 409 Conflict (mapping hash mismatch).
    """
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]
    csv_rows = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        [f"HASH-MISMATCH-{uid}", "Hash Student", "454545454545", "ACTIVE"],
    ]
    mapping = {"student_id": "student_id", "full_name": "full_name", "apaar_id": "apaar_id", "student_status": "student_status"}
    sub_id, prev_id = upload_and_preview(
        apex["token"], apex["prog_id"], (f"roster_hash_{uid}.csv", create_sample_csv(csv_rows), "text/csv"), mapping, academic_year=f"2024-{uid[:4]}"
    )

    # Attempt to confirm with a different mapping without generating a preview for it
    modified_mapping = {"student_id": "full_name", "full_name": "student_id"}
    res_confirm = client.post(
        f"/api/v1/submissions/{sub_id}/confirm",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={"preview_id": prev_id, "column_mapping": modified_mapping},
    )
    assert res_confirm.status_code == 409
    assert "Stale or mismatched preview version" in res_confirm.text


# =========================================================================
# Scenario 18: File Fingerprint Mismatch Rejection
# =========================================================================
def test_scenario_18_file_fingerprint_mismatch_rejection(seeded_tokens):
    """
    Scenario 18:
    - If preview file fingerprint does not match submission file fingerprint,
      confirm is rejected with 409 Conflict.
    """
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]
    csv_rows = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        [f"FP-MISMATCH-{uid}", "FP Student", "565656565656", "ACTIVE"],
    ]
    mapping = {"student_id": "student_id", "full_name": "full_name", "apaar_id": "apaar_id", "student_status": "student_status"}
    sub_id, prev_id = upload_and_preview(
        apex["token"], apex["prog_id"], (f"roster_fp_{uid}.csv", create_sample_csv(csv_rows), "text/csv"), mapping, academic_year=f"2024-{uid[:4]}"
    )

    # Tamper with preview file_fingerprint in database
    db = SessionLocal()
    try:
        prev = db.execute(select(SubmissionPreview).where(SubmissionPreview.id == uuid.UUID(prev_id))).scalar_one()
        prev.file_fingerprint = "0" * 64
        db.commit()
    finally:
        db.close()

    res_confirm = client.post(
        f"/api/v1/submissions/{sub_id}/confirm",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={"preview_id": prev_id, "column_mapping": mapping},
    )
    assert res_confirm.status_code == 409
    assert "Integrity violation" in res_confirm.text


# =========================================================================
# Scenario 19: Duplicate Confirmation After Commit Rejection
# =========================================================================
def test_scenario_19_duplicate_confirmation_after_commit(seeded_tokens):
    """
    Scenario 19:
    - Calling confirm on an already COMMITTED submission returns 409 Conflict.
    """
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]
    csv_rows = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        [f"DUP-CONFIRM-{uid}", "Dup Confirm Student", "676767676767", "ACTIVE"],
    ]
    mapping = {"student_id": "student_id", "full_name": "full_name", "apaar_id": "apaar_id", "student_status": "student_status"}
    sub_id, prev_id = upload_and_preview(
        apex["token"], apex["prog_id"], (f"roster_dup_confirm_{uid}.csv", create_sample_csv(csv_rows), "text/csv"), mapping, academic_year=f"2024-{uid[:4]}"
    )

    # First confirm succeeds
    res1 = client.post(
        f"/api/v1/submissions/{sub_id}/confirm",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={"preview_id": prev_id, "column_mapping": mapping},
    )
    assert res1.status_code == 200

    # Second confirm returns 409
    res2 = client.post(
        f"/api/v1/submissions/{sub_id}/confirm",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={"preview_id": prev_id, "column_mapping": mapping},
    )
    assert res2.status_code == 409
    assert "Submission has already been committed" in res2.text


# =========================================================================
# Scenario 20: Formula Evidence Preservation
# =========================================================================
def test_scenario_20_formula_evidence_preservation(seeded_tokens):
    """
    Scenario 20:
    - Ingested XLSX records retain verbatim formula strings (e.g., =SUM(10,20))
      in source_submission_records.raw_payload without mutation or apostrophe prefixing.
    """
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]
    formula_str = "=SUM(10,20)"
    xlsx_rows = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        [formula_str, "Formula Student", "787878787878", "ACTIVE"],
    ]
    mapping = {"student_id": "student_id", "full_name": "full_name", "apaar_id": "apaar_id", "student_status": "student_status"}
    sub_id, prev_id = upload_and_preview(
        apex["token"], apex["prog_id"], (f"roster_formula_{uid}.xlsx", create_sample_xlsx(xlsx_rows), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"), mapping, academic_year=f"2024-{uid[:4]}"
    )

    res = client.post(
        f"/api/v1/submissions/{sub_id}/confirm",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={"preview_id": prev_id, "column_mapping": mapping},
    )
    assert res.status_code == 200

    db = SessionLocal()
    try:
        rec = db.execute(
            select(SourceSubmissionRecord).where(SourceSubmissionRecord.submission_id == uuid.UUID(sub_id))
        ).scalar_one()

        # Formula string preserved exactly verbatim in raw_payload without mutation
        assert rec.raw_payload["student_id"] == formula_str
        assert not rec.raw_payload["student_id"].startswith("'")
        assert "student_id" in rec.formula_metadata
        assert rec.formula_metadata["student_id"]["formula"] == formula_str
    finally:
        db.close()
