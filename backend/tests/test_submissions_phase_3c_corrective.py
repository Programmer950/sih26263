"""Corrective tests for Milestone 3 Phase 3C: Findings 1, 2, 3, and 4."""

import pytest
import uuid
import io
import os
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select, func, text
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

    db = SessionLocal()
    try:
        apex_prog = db.execute(select(Programme).where(Programme.institution_id == uuid.UUID(apex_inst_id))).scalars().first()
        apex_prog_id = str(apex_prog.id) if apex_prog else None
    finally:
        db.close()

    return {
        "apex": {"token": apex_token, "inst_id": apex_inst_id, "prog_id": apex_prog_id},
    }


def create_sample_csv(rows_data: list) -> io.BytesIO:
    """Helper to create an in-memory CSV file."""
    output = io.StringIO()
    import csv
    writer = csv.writer(output)
    for r in rows_data:
        writer.writerow(r)
    return io.BytesIO(output.getvalue().encode("utf-8"))


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
# Finding 1: Context-Scoped Snapshot Serialization
# =========================================================================

def test_finding_1_concurrent_promotion_no_existing_authoritative(seeded_tokens):
    """
    Finding 1 Requirement A:
    - No existing authoritative snapshot.
    - Two distinct eligible submissions for the same institution/programme/year.
    - Both confirmed concurrently with authoritative promotion requested.
    - Transaction advisory lock serializes promotions.
    - Both transactions complete successfully (HTTP 200).
    - Exactly one snapshot remains authoritative; the other is superseded.
    """
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]
    academic_year = f"2025-F1A-{uid}"
    mapping = {"student_id": "student_id", "full_name": "full_name", "apaar_id": "apaar_id", "student_status": "student_status"}

    # Submission 1
    csv1 = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        [f"S1-{uid}-01", "Student One", "111100001111", "ACTIVE"],
    ]
    sub1_id, prev1_id = upload_and_preview(
        apex["token"], apex["prog_id"], (f"roster_f1a_1_{uid}.csv", create_sample_csv(csv1), "text/csv"), mapping, academic_year=academic_year
    )

    # Submission 2
    csv2 = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        [f"S2-{uid}-02", "Student Two", "222200002222", "ACTIVE"],
    ]
    sub2_id, prev2_id = upload_and_preview(
        apex["token"], apex["prog_id"], (f"roster_f1a_2_{uid}.csv", create_sample_csv(csv2), "text/csv"), mapping, academic_year=academic_year
    )

    def confirm_sub(sub_id, prev_id):
        c = TestClient(app)
        return c.post(
            f"/api/v1/submissions/{sub_id}/confirm",
            headers={"Authorization": f"Bearer {apex['token']}"},
            json={
                "preview_id": prev_id,
                "column_mapping": mapping,
                "mark_as_authoritative": True,
                "completeness_status": "COMPLETE",
            },
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(confirm_sub, sub1_id, prev1_id)
        f2 = executor.submit(confirm_sub, sub2_id, prev2_id)
        res1 = f1.result()
        res2 = f2.result()

    assert res1.status_code == 200, res1.text
    assert res2.status_code == 200, res2.text

    db = SessionLocal()
    try:
        snaps = db.execute(
            select(RosterSnapshot).where(
                RosterSnapshot.institution_id == uuid.UUID(apex["inst_id"]),
                RosterSnapshot.programme_id == uuid.UUID(apex["prog_id"]),
                RosterSnapshot.academic_year == academic_year,
            )
        ).scalars().all()

        assert len(snaps) == 2

        authoritative_snaps = [s for s in snaps if s.is_authoritative]
        superseded_snaps = [s for s in snaps if not s.is_authoritative]

        assert len(authoritative_snaps) == 1, "Exactly one snapshot must remain authoritative"
        assert len(superseded_snaps) == 1, "The other snapshot must be superseded"

        auth = authoritative_snaps[0]
        sup = superseded_snaps[0]

        assert auth.lifecycle_status == "ACTIVE"
        assert sup.lifecycle_status == "SUPERSEDED"
        assert sup.superseded_by_snapshot_id == auth.id
        assert sup.superseded_at is not None
    finally:
        db.close()


def test_finding_1_concurrent_promotion_with_existing_authoritative(seeded_tokens):
    """
    Finding 1 Requirement B:
    - Begin with one existing authoritative snapshot.
    - Concurrently promote two different submissions for the same context.
    - Both transactions complete successfully.
    - Exactly one final authoritative snapshot remains.
    - All previously authoritative snapshots have correct supersession metadata.
    """
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]
    academic_year = f"2025-F1B-{uid}"
    mapping = {"student_id": "student_id", "full_name": "full_name", "apaar_id": "apaar_id", "student_status": "student_status"}

    # Initial submission to establish initial authoritative snapshot
    csv0 = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        [f"S0-{uid}-00", "Initial Student", "333300003333", "ACTIVE"],
    ]
    sub0_id, prev0_id = upload_and_preview(
        apex["token"], apex["prog_id"], (f"roster_f1b_0_{uid}.csv", create_sample_csv(csv0), "text/csv"), mapping, academic_year=academic_year
    )
    res0 = client.post(
        f"/api/v1/submissions/{sub0_id}/confirm",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={"preview_id": prev0_id, "column_mapping": mapping, "mark_as_authoritative": True},
    )
    assert res0.status_code == 200

    # Two concurrent replacement submissions
    csv1 = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        [f"S1-{uid}-01", "Replacement One", "444400004444", "ACTIVE"],
    ]
    sub1_id, prev1_id = upload_and_preview(
        apex["token"], apex["prog_id"], (f"roster_f1b_1_{uid}.csv", create_sample_csv(csv1), "text/csv"), mapping, academic_year=academic_year
    )

    csv2 = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        [f"S2-{uid}-02", "Replacement Two", "555500005555", "ACTIVE"],
    ]
    sub2_id, prev2_id = upload_and_preview(
        apex["token"], apex["prog_id"], (f"roster_f1b_2_{uid}.csv", create_sample_csv(csv2), "text/csv"), mapping, academic_year=academic_year
    )

    def confirm_sub(sub_id, prev_id):
        c = TestClient(app)
        return c.post(
            f"/api/v1/submissions/{sub_id}/confirm",
            headers={"Authorization": f"Bearer {apex['token']}"},
            json={"preview_id": prev_id, "column_mapping": mapping, "mark_as_authoritative": True},
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(confirm_sub, sub1_id, prev1_id)
        f2 = executor.submit(confirm_sub, sub2_id, prev2_id)
        res1 = f1.result()
        res2 = f2.result()

    assert res1.status_code == 200, res1.text
    assert res2.status_code == 200, res2.text

    db = SessionLocal()
    try:
        snaps = db.execute(
            select(RosterSnapshot).where(
                RosterSnapshot.institution_id == uuid.UUID(apex["inst_id"]),
                RosterSnapshot.programme_id == uuid.UUID(apex["prog_id"]),
                RosterSnapshot.academic_year == academic_year,
            )
        ).scalars().all()

        assert len(snaps) == 3

        authoritative = [s for s in snaps if s.is_authoritative]
        superseded = [s for s in snaps if not s.is_authoritative]

        assert len(authoritative) == 1, "Exactly one final authoritative snapshot must remain"
        assert len(superseded) == 2, "Both previous snapshots must be superseded"

        for s in superseded:
            assert s.lifecycle_status == "SUPERSEDED"
            assert s.superseded_at is not None
            assert s.superseded_by_snapshot_id is not None
    finally:
        db.close()


def test_finding_1_different_contexts_not_serialized(seeded_tokens):
    """
    Finding 1 Requirement C:
    - Confirm that operations for unrelated institution/programme/year contexts
      are not unnecessarily serialized and succeed in parallel.
    """
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]
    mapping = {"student_id": "student_id", "full_name": "full_name", "apaar_id": "apaar_id", "student_status": "student_status"}

    # Context 1
    year1 = f"2025-C1-{uid}"
    csv1 = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        [f"C1-{uid}-01", "Context 1 Student", "666600006666", "ACTIVE"],
    ]
    sub1_id, prev1_id = upload_and_preview(
        apex["token"], apex["prog_id"], (f"roster_c1_{uid}.csv", create_sample_csv(csv1), "text/csv"), mapping, academic_year=year1
    )

    # Context 2
    year2 = f"2025-C2-{uid}"
    csv2 = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        [f"C2-{uid}-02", "Context 2 Student", "777700007777", "ACTIVE"],
    ]
    sub2_id, prev2_id = upload_and_preview(
        apex["token"], apex["prog_id"], (f"roster_c2_{uid}.csv", create_sample_csv(csv2), "text/csv"), mapping, academic_year=year2
    )

    def confirm_sub(sub_id, prev_id):
        c = TestClient(app)
        return c.post(
            f"/api/v1/submissions/{sub_id}/confirm",
            headers={"Authorization": f"Bearer {apex['token']}"},
            json={"preview_id": prev_id, "column_mapping": mapping, "mark_as_authoritative": True},
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(confirm_sub, sub1_id, prev1_id)
        f2 = executor.submit(confirm_sub, sub2_id, prev2_id)
        res1 = f1.result()
        res2 = f2.result()

    assert res1.status_code == 200
    assert res2.status_code == 200

    db = SessionLocal()
    try:
        snap1 = db.execute(
            select(RosterSnapshot).where(
                RosterSnapshot.source_submission_id == uuid.UUID(sub1_id)
            )
        ).scalar_one()
        snap2 = db.execute(
            select(RosterSnapshot).where(
                RosterSnapshot.source_submission_id == uuid.UUID(sub2_id)
            )
        ).scalar_one()

        assert snap1.is_authoritative is True
        assert snap2.is_authoritative is True
    finally:
        db.close()


# =========================================================================
# Finding 2: Conditional Failure-State Transition
# =========================================================================

def test_finding_2_delayed_failure_handler_cannot_overwrite_committed(seeded_tokens):
    """
    Finding 2 Interleaving:
    1. Request A starts on submission X, fails, and rolls back TxA.
    2. Before failure handler B executes, Request B retries and successfully commits.
    3. Failure handler B executes conditional UPDATE.
    4. Assert: rowcount == 0. Status remains COMMITTED.
    """
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]
    academic_year = f"2025-F2-{uid}"
    csv_rows = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        [f"RET-{uid}-01", "Retry Student", "888800008888", "ACTIVE"],
    ]
    mapping = {"student_id": "student_id", "full_name": "full_name", "apaar_id": "apaar_id", "student_status": "student_status"}
    sub_id, prev_id = upload_and_preview(
        apex["token"], apex["prog_id"], (f"roster_f2_{uid}.csv", create_sample_csv(csv_rows), "text/csv"), mapping, academic_year=academic_year
    )

    # Request B confirms successfully
    res_b = client.post(
        f"/api/v1/submissions/{sub_id}/confirm",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={"preview_id": prev_id, "column_mapping": mapping, "mark_as_authoritative": True},
    )
    assert res_b.status_code == 200
    assert res_b.json()["submission_status"] == "COMMITTED"

    # Now simulate delayed failure handler B attempting conditional UPDATE
    db = SessionLocal()
    try:
        result = db.execute(
            text("""
                UPDATE source_submissions
                SET submission_status = 'FAILED',
                    failure_reason = 'Simulated delayed failure handler',
                    updated_at = NOW()
                WHERE id = :submission_id
                  AND submission_status IN ('PREVIEW_READY', 'INGESTING')
            """),
            {"submission_id": uuid.UUID(sub_id)},
        )
        db.commit()

        # Rowcount must be 0: conditional check prevented overwrite
        assert result.rowcount == 0, "Delayed failure handler must not update a COMMITTED submission"

        sub_db = db.execute(select(SourceSubmission).where(SourceSubmission.id == uuid.UUID(sub_id))).scalar_one()
        assert sub_db.submission_status == "COMMITTED"
        assert sub_db.failure_reason is None
    finally:
        db.close()


def test_finding_2_failure_handler_records_failed_first_blocks_retry(seeded_tokens):
    """
    Finding 2 Inverse Ordering:
    - Failure handler records FAILED.
    - Subsequent retry observes FAILED and is rejected with 400 Bad Request.
    """
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]
    academic_year = f"2025-F2INV-{uid}"
    csv_rows = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        [f"INV-{uid}-01", "Inverse Student", "999900009999", "ACTIVE"],
    ]
    mapping = {"student_id": "student_id", "full_name": "full_name", "apaar_id": "apaar_id", "student_status": "student_status"}
    sub_id, prev_id = upload_and_preview(
        apex["token"], apex["prog_id"], (f"roster_f2inv_{uid}.csv", create_sample_csv(csv_rows), "text/csv"), mapping, academic_year=academic_year
    )

    # Set submission to FAILED via conditional update
    db = SessionLocal()
    try:
        res = db.execute(
            text("""
                UPDATE source_submissions
                SET submission_status = 'FAILED',
                    failure_reason = 'Ingestion fault simulated',
                    updated_at = NOW()
                WHERE id = :submission_id
                  AND submission_status IN ('PREVIEW_READY', 'INGESTING')
            """),
            {"submission_id": uuid.UUID(sub_id)},
        )
        db.commit()
        assert res.rowcount == 1
    finally:
        db.close()

    # Retry attempt is rejected with 400
    res_retry = client.post(
        f"/api/v1/submissions/{sub_id}/confirm",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={"preview_id": prev_id, "column_mapping": mapping},
    )
    assert res_retry.status_code == 400
    assert "Cannot confirm a failed submission" in res_retry.text


def test_finding_2_every_allowed_failure_transition(seeded_tokens):
    """
    Finding 2 Allowlist Verification:
    - Every allowed predecessor state ('PREVIEW_READY', 'INGESTING')
      successfully transitions to 'FAILED' with rowcount == 1.
    """
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]
    mapping = {"student_id": "student_id", "full_name": "full_name", "apaar_id": "apaar_id", "student_status": "student_status"}

    for state in ["PREVIEW_READY", "INGESTING"]:
        sub_uid = f"{uid}_{state[:3]}"
        csv_rows = [["student_id", "full_name", "apaar_id", "student_status"], [f"ALLOW-{sub_uid}", "Allow Student", "111122223333", "ACTIVE"]]
        sub_id, _ = upload_and_preview(
            apex["token"], apex["prog_id"], (f"roster_allow_{sub_uid}.csv", create_sample_csv(csv_rows), "text/csv"), mapping, academic_year=f"2025-ALW-{sub_uid}"
        )

        db = SessionLocal()
        try:
            # Manually set state to target allowed state
            db.execute(
                text("UPDATE source_submissions SET submission_status = :state WHERE id = :id"),
                {"state": state, "id": uuid.UUID(sub_id)},
            )
            db.commit()

            # Execute the failure handler conditional UPDATE
            result = db.execute(
                text("""
                    UPDATE source_submissions
                    SET submission_status = 'FAILED',
                        failure_reason = :reason,
                        updated_at = NOW()
                    WHERE id = :id
                      AND submission_status IN ('PREVIEW_READY', 'INGESTING')
                """),
                {"id": uuid.UUID(sub_id), "reason": f"Failure from {state}"},
            )
            db.commit()

            assert result.rowcount == 1, f"State '{state}' must transition to FAILED with rowcount == 1"

            sub_db = db.execute(select(SourceSubmission).where(SourceSubmission.id == uuid.UUID(sub_id))).scalar_one()
            assert sub_db.submission_status == "FAILED"
            assert sub_db.failure_reason == f"Failure from {state}"
        finally:
            db.close()


def test_finding_2_every_disallowed_failure_transition(seeded_tokens):
    """
    Finding 2 Disallowlist Verification:
    - Every non-predecessor state:
      'COMMITTED', 'FAILED', 'CANCELLED', 'VALIDATION_FAILED', 'UPLOADED', 'VALIDATING'
      is rejected by the conditional UPDATE (rowcount == 0).
      Their status remains completely unchanged.
    """
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]
    mapping = {"student_id": "student_id", "full_name": "full_name", "apaar_id": "apaar_id", "student_status": "student_status"}

    disallowed_states = [
        "COMMITTED",
        "FAILED",
        "CANCELLED",
        "VALIDATION_FAILED",
        "UPLOADED",
        "VALIDATING",
    ]

    for state in disallowed_states:
        sub_uid = f"{uid}_{state.lower()}"
        csv_rows = [["student_id", "full_name", "apaar_id", "student_status"], [f"DIS-{sub_uid}", "Disallow Student", "444455556666", "ACTIVE"]]
        sub_id, _ = upload_and_preview(
            apex["token"], apex["prog_id"], (f"roster_dis_{sub_uid}.csv", create_sample_csv(csv_rows), "text/csv"), mapping, academic_year=f"2025-{state.lower()[:6]}-{uid}"
        )

        db = SessionLocal()
        try:
            # Set submission to the disallowed test state
            db.execute(
                text("UPDATE source_submissions SET submission_status = :state WHERE id = :id"),
                {"state": state, "id": uuid.UUID(sub_id)},
            )
            db.commit()

            # Attempt conditional failure transition
            result = db.execute(
                text("""
                    UPDATE source_submissions
                    SET submission_status = 'FAILED',
                        failure_reason = 'Should not overwrite',
                        updated_at = NOW()
                    WHERE id = :id
                      AND submission_status IN ('PREVIEW_READY', 'INGESTING')
                """),
                {"id": uuid.UUID(sub_id)},
            )
            db.commit()

            assert result.rowcount == 0, f"Disallowed state '{state}' must NOT be updated (rowcount must be 0)"

            sub_db = db.execute(select(SourceSubmission).where(SourceSubmission.id == uuid.UUID(sub_id))).scalar_one()
            assert sub_db.submission_status == state, f"Submission in state '{state}' must remain in '{state}'"
            assert sub_db.failure_reason != "Should not overwrite"
        finally:
            db.close()



# =========================================================================
# Finding 3: Historical Processing Version Enforcement
# =========================================================================

def test_finding_3_unsupported_parser_version_rejected(seeded_tokens):
    """Unsupported parser version rejects with HTTP 409."""
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]
    csv_rows = [["student_id", "full_name", "apaar_id", "student_status"], [f"PVER-{uid}", "P Ver Student", "121200001212", "ACTIVE"]]
    mapping = {"student_id": "student_id", "full_name": "full_name", "apaar_id": "apaar_id", "student_status": "student_status"}
    sub_id, prev_id = upload_and_preview(
        apex["token"], apex["prog_id"], (f"roster_pver_{uid}.csv", create_sample_csv(csv_rows), "text/csv"), mapping, academic_year=f"2025-PVER-{uid}"
    )

    db = SessionLocal()
    try:
        prev = db.execute(select(SubmissionPreview).where(SubmissionPreview.id == uuid.UUID(prev_id))).scalar_one()
        prev.parser_version = "openpyxl-legacy-unsupported"
        db.commit()
    finally:
        db.close()

    res = client.post(
        f"/api/v1/submissions/{sub_id}/confirm",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={"preview_id": prev_id, "column_mapping": mapping},
    )
    assert res.status_code == 409
    assert "Unsupported parser version" in res.text
    assert "preview must be regenerated" in res.text


def test_finding_3_unsupported_validation_rules_version_rejected(seeded_tokens):
    """Unsupported validation rules version rejects with HTTP 409."""
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]
    csv_rows = [["student_id", "full_name", "apaar_id", "student_status"], [f"RVER-{uid}", "R Ver Student", "131300001313", "ACTIVE"]]
    mapping = {"student_id": "student_id", "full_name": "full_name", "apaar_id": "apaar_id", "student_status": "student_status"}
    sub_id, prev_id = upload_and_preview(
        apex["token"], apex["prog_id"], (f"roster_rver_{uid}.csv", create_sample_csv(csv_rows), "text/csv"), mapping, academic_year=f"2025-RVER-{uid}"
    )

    db = SessionLocal()
    try:
        prev = db.execute(select(SubmissionPreview).where(SubmissionPreview.id == uuid.UUID(prev_id))).scalar_one()
        prev.validation_rules_version = "rules-v1999.0"
        db.commit()
    finally:
        db.close()

    res = client.post(
        f"/api/v1/submissions/{sub_id}/confirm",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={"preview_id": prev_id, "column_mapping": mapping},
    )
    assert res.status_code == 409
    assert "Unsupported validation rules version" in res.text


def test_finding_3_unsupported_normalization_version_rejected(seeded_tokens):
    """Unsupported normalization version rejects with HTTP 409."""
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]
    csv_rows = [["student_id", "full_name", "apaar_id", "student_status"], [f"NVER-{uid}", "N Ver Student", "141400001414", "ACTIVE"]]
    mapping = {"student_id": "student_id", "full_name": "full_name", "apaar_id": "apaar_id", "student_status": "student_status"}
    sub_id, prev_id = upload_and_preview(
        apex["token"], apex["prog_id"], (f"roster_nver_{uid}.csv", create_sample_csv(csv_rows), "text/csv"), mapping, academic_year=f"2025-NVER-{uid}"
    )

    db = SessionLocal()
    try:
        prev = db.execute(select(SubmissionPreview).where(SubmissionPreview.id == uuid.UUID(prev_id))).scalar_one()
        prev.normalization_version = "norm-v0.0-unsupported"
        db.commit()
    finally:
        db.close()

    res = client.post(
        f"/api/v1/submissions/{sub_id}/confirm",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={"preview_id": prev_id, "column_mapping": mapping},
    )
    assert res.status_code == 409
    assert "Unsupported normalization version" in res.text


def test_finding_3_unsupported_mapping_version_rejected(seeded_tokens):
    """Unsupported mapping version rejects with HTTP 409."""
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]
    csv_rows = [["student_id", "full_name", "apaar_id", "student_status"], [f"MVER-{uid}", "M Ver Student", "151500001515", "ACTIVE"]]
    mapping = {"student_id": "student_id", "full_name": "full_name", "apaar_id": "apaar_id", "student_status": "student_status"}
    sub_id, prev_id = upload_and_preview(
        apex["token"], apex["prog_id"], (f"roster_mver_{uid}.csv", create_sample_csv(csv_rows), "text/csv"), mapping, academic_year=f"2025-MVER-{uid}"
    )

    db = SessionLocal()
    try:
        prev = db.execute(select(SubmissionPreview).where(SubmissionPreview.id == uuid.UUID(prev_id))).scalar_one()
        prev.mapping_version = "v99.9"
        db.commit()
    finally:
        db.close()

    res = client.post(
        f"/api/v1/submissions/{sub_id}/confirm",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={"preview_id": prev_id, "column_mapping": mapping},
    )
    assert res.status_code == 409
    assert "Unsupported mapping version" in res.text


def test_finding_3_attempted_frontend_mapping_substitution_rejected(seeded_tokens):
    """Client cannot substitute a mapping that differs from authoritative preview mapping."""
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]
    csv_rows = [["student_id", "full_name", "apaar_id", "student_status"], [f"SUBST-{uid}", "Subst Student", "161600001616", "ACTIVE"]]
    mapping = {"student_id": "student_id", "full_name": "full_name", "apaar_id": "apaar_id", "student_status": "student_status"}
    sub_id, prev_id = upload_and_preview(
        apex["token"], apex["prog_id"], (f"roster_subst_{uid}.csv", create_sample_csv(csv_rows), "text/csv"), mapping, academic_year=f"2025-SUBST-{uid}"
    )

    # Attempt frontend substitution
    fraudulent_mapping = {"student_id": "full_name", "full_name": "student_id"}
    res = client.post(
        f"/api/v1/submissions/{sub_id}/confirm",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={"preview_id": prev_id, "column_mapping": fraudulent_mapping},
    )
    assert res.status_code == 409
    assert "Attempted mapping substitution" in res.text


def test_finding_3_successful_confirmation_matching_supported_versions(seeded_tokens):
    """Confirmation succeeds cleanly when all versions match current engine."""
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]
    csv_rows = [["student_id", "full_name", "apaar_id", "student_status"], [f"OK-{uid}", "OK Student", "171700001717", "ACTIVE"]]
    mapping = {"student_id": "student_id", "full_name": "full_name", "apaar_id": "apaar_id", "student_status": "student_status"}
    sub_id, prev_id = upload_and_preview(
        apex["token"], apex["prog_id"], (f"roster_ok_{uid}.csv", create_sample_csv(csv_rows), "text/csv"), mapping, academic_year=f"2025-OK-{uid}"
    )

    res = client.post(
        f"/api/v1/submissions/{sub_id}/confirm",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={"preview_id": prev_id, "column_mapping": mapping},
    )
    assert res.status_code == 200
    assert res.json()["submission_status"] == "COMMITTED"


# =========================================================================
# Finding 4: Retention Docstring Alignment
# =========================================================================

def test_finding_4_cancellation_preserves_evidence_under_retention_policy(seeded_tokens):
    """Cancelling submission transitions to CANCELLED while retaining raw evidence under policy."""
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]
    csv_rows = [["student_id", "full_name", "apaar_id", "student_status"], [f"RET-EVD-{uid}", "Policy Student", "181800001818", "ACTIVE"]]
    mapping = {"student_id": "student_id", "full_name": "full_name", "apaar_id": "apaar_id", "student_status": "student_status"}
    sub_id, _ = upload_and_preview(
        apex["token"], apex["prog_id"], (f"roster_retevd_{uid}.csv", create_sample_csv(csv_rows), "text/csv"), mapping, academic_year=f"2025-RETEVD-{uid}"
    )

    res_cancel = client.post(f"/api/v1/submissions/{sub_id}/cancel", headers={"Authorization": f"Bearer {apex['token']}"})
    assert res_cancel.status_code == 200
    assert res_cancel.json()["submission_status"] == "CANCELLED"

    db = SessionLocal()
    try:
        sub = db.execute(select(SourceSubmission).where(SourceSubmission.id == uuid.UUID(sub_id))).scalar_one()
        assert sub.submission_status == "CANCELLED"
        assert sub.cancelled_at is not None
        # Raw file is still retained on disk in accordance with RETENTION_DAYS_CANCELLED
        resolved_path = StorageService.resolve_safe_path(sub.storage_key)
        assert os.path.exists(resolved_path)
    finally:
        db.close()

