"""Tests for Milestone 3 Phase 3D: Snapshot Lifecycle, Promotion Concurrency, Comparison Engine, and Export Sidecars."""

import pytest
import uuid
import io
import csv
from datetime import datetime, date, timezone
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select, func
from fastapi.testclient import TestClient
import openpyxl

from app.main import app
from app.core.database import SessionLocal
from app.models import (
    User,
    Programme,
    Institution,
    RosterSnapshot,
    SourceSubmission,
    AnnualRosterObservation,
    StudentIdentity,
    AdmissionEpisode,
    TransferEvent,
    AuditEvent,
    SubmissionPreview,
    SourceSubmissionRecord,
    InstitutionStudentRecord,
    ApprovalConfiguration,
)
from app.services.snapshot_service import SnapshotService
from app.services.comparison_service import ComparisonService
from app.services.export_service import defuse_formula_injection

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
    
    # 1. Upload
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

    # 2. Preview
    mapping = {"student_id": "student_id", "full_name": "full_name", "apaar_id": "apaar_id", "student_status": "student_status"}
    res_prev = client.post(
        f"/api/v1/submissions/{sub_id}/preview",
        headers={"Authorization": f"Bearer {token}"},
        json={"column_mapping": mapping},
    )
    assert res_prev.status_code == 200, res_prev.text
    prev_id = res_prev.json()["preview_id"]

    # 3. Confirm
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
    data = res_conf.json()
    return sub_id, data["snapshot_id"]


# =========================================================================
# 1. Promotion Success, Advisory Locking, and Supersession Invariant
# =========================================================================
def test_snapshot_promotion_lifecycle_and_supersession(seeded_tokens):
    """
    Verify:
    1. A non-authoritative snapshot is created.
    2. POST /api/v1/snapshots/{id}/promote promotes it to authoritative.
    3. Promoting a second snapshot in the same context supersedes the first snapshot.
    4. Database partial unique index ensures only one authoritative snapshot exists.
    """
    apex = seeded_tokens["apex"]
    year = f"2024-P1-{uuid.uuid4().hex[:4]}"
    rows_v1 = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        ["S1", "Alice Smith", "111122223333", "ACTIVE"],
        ["S2", "Bob Jones", "444455556666", "ACTIVE"],
    ]

    # Ingest v1 with mark_as_authoritative=False
    sub_id_1, snap_id_1 = upload_preview_and_confirm(
        token=apex["token"],
        prog_id=apex["prog_id"],
        file_rows=rows_v1,
        mark_authoritative=False,
        academic_year=year,
    )

    db = SessionLocal()
    try:
        s1 = db.get(RosterSnapshot, uuid.UUID(snap_id_1))
        assert s1.is_authoritative is False
        assert s1.lifecycle_status == "ACTIVE"

        # Promote snap 1
        res_prom_1 = client.post(
            f"/api/v1/snapshots/{snap_id_1}/promote",
            headers={"Authorization": f"Bearer {apex['token']}"},
            json={"reason": "Initial manual promotion for testing"},
        )
        assert res_prom_1.status_code == 200, res_prom_1.text
        prom_data_1 = res_prom_1.json()
        assert prom_data_1["is_authoritative"] is True
        assert prom_data_1["superseded_snapshot_id"] is None

        # Verify db state for s1
        db.refresh(s1)
        assert s1.is_authoritative is True
        assert s1.lifecycle_status == "ACTIVE"

        # Now ingest v2 for the same context with mark_as_authoritative=False
        rows_v2 = [
            ["student_id", "full_name", "apaar_id", "student_status"],
            ["S1", "Alice Smith", "111122223333", "ACTIVE"],
            ["S2", "Bob Jones", "444455556666", "ACTIVE"],
            ["S3", "Charlie Brown", "333344445555", "ACTIVE"],
        ]
        sub_id_2, snap_id_2 = upload_preview_and_confirm(
            token=apex["token"],
            prog_id=apex["prog_id"],
            file_rows=rows_v2,
            mark_authoritative=False,
            academic_year=year,
        )

        s2 = db.get(RosterSnapshot, uuid.UUID(snap_id_2))
        assert s2.is_authoritative is False

        # Promote snap 2
        res_prom_2 = client.post(
            f"/api/v1/snapshots/{snap_id_2}/promote",
            headers={"Authorization": f"Bearer {apex['token']}"},
            json={"reason": "Second promotion superseding first snapshot"},
        )
        assert res_prom_2.status_code == 200, res_prom_2.text
        prom_data_2 = res_prom_2.json()
        assert prom_data_2["is_authoritative"] is True
        assert prom_data_2["superseded_snapshot_id"] == snap_id_1

        # Verify s1 was superseded and s2 is authoritative
        db.refresh(s1)
        db.refresh(s2)
        assert s1.is_authoritative is False
        assert s1.lifecycle_status == "SUPERSEDED"
        assert s1.superseded_by_snapshot_id == s2.id
        assert s1.superseded_at is not None

        assert s2.is_authoritative is True
        assert s2.lifecycle_status == "ACTIVE"

        # Verify exact partial unique constraint in db: only 1 authoritative for this context
        auth_count = db.execute(
            select(func.count(RosterSnapshot.id)).where(
                RosterSnapshot.institution_id == s1.institution_id,
                RosterSnapshot.programme_id == s1.programme_id,
                RosterSnapshot.academic_year == year,
                RosterSnapshot.is_authoritative == True,
            )
        ).scalar()
        assert auth_count == 1
    finally:
        db.close()


# =========================================================================
# 2. Promotion Validation & Conflict Errors
# =========================================================================
def test_snapshot_promotion_conflict_and_ineligibility(seeded_tokens):
    """
    Verify:
    1. Promoting an already authoritative snapshot returns 409 Conflict.
    2. Promoting a superseded snapshot returns 409 Conflict.
    3. Promoting a non-existent snapshot returns 404 Not Found.
    """
    apex = seeded_tokens["apex"]
    year = f"2024-P2-{uuid.uuid4().hex[:4]}"
    rows = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        ["S1", "Alice Smith", "111122223333", "ACTIVE"],
    ]

    _, snap_id = upload_preview_and_confirm(
        token=apex["token"],
        prog_id=apex["prog_id"],
        file_rows=rows,
        mark_authoritative=True,
        academic_year=year,
    )

    # 1. Attempt to promote already authoritative snapshot
    res_conflict = client.post(
        f"/api/v1/snapshots/{snap_id}/promote",
        headers={"Authorization": f"Bearer {apex['token']}"},
    )
    assert res_conflict.status_code == 409
    assert "already authoritative" in res_conflict.json()["detail"].lower()

    # Create and promote a second snapshot to supersede snap_id
    rows_v2 = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        ["S1", "Alice Smith", "111122223333", "ACTIVE"],
        ["S2", "Bob Jones", "444455556666", "ACTIVE"],
    ]
    _, snap_id_v2 = upload_preview_and_confirm(
        token=apex["token"],
        prog_id=apex["prog_id"],
        file_rows=rows_v2,
        mark_authoritative=False,
        academic_year=year,
    )
    res_prom_v2 = client.post(
        f"/api/v1/snapshots/{snap_id_v2}/promote",
        headers={"Authorization": f"Bearer {apex['token']}"},
    )
    assert res_prom_v2.status_code == 200

    # 2. Attempt to promote superseded snap_id -> 409 Conflict
    res_superseded = client.post(
        f"/api/v1/snapshots/{snap_id}/promote",
        headers={"Authorization": f"Bearer {apex['token']}"},
    )
    assert res_superseded.status_code == 409
    assert "cannot promote a superseded snapshot" in res_superseded.json()["detail"].lower()

    # 3. Non-existent snapshot -> 404 Not Found
    res_missing = client.post(
        f"/api/v1/snapshots/{uuid.uuid4()}/promote",
        headers={"Authorization": f"Bearer {apex['token']}"},
    )
    assert res_missing.status_code == 404


# =========================================================================
# 3. Audit Trail Chaining for Snapshot Promotion and Supersession
# =========================================================================
def test_audit_event_chaining_on_promotion(seeded_tokens):
    """
    Verify:
    1. Authoritative promotion generates SUPERSEDE_SNAPSHOT and PROMOTE_SNAPSHOT events.
    2. Audit events are cryptographically SHA-256 chained in the same transaction.
    """
    apex = seeded_tokens["apex"]
    year = f"2024-P3-{uuid.uuid4().hex[:4]}"
    rows_1 = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        ["S1", "Dev Sharma", "123412341234", "ACTIVE"],
    ]
    rows_2 = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        ["S1", "Dev Sharma", "123412341234", "ACTIVE"],
        ["S2", "Pooja Verma", "123412341235", "ACTIVE"],
    ]

    _, snap_1 = upload_preview_and_confirm(
        token=apex["token"],
        prog_id=apex["prog_id"],
        file_rows=rows_1,
        mark_authoritative=True,
        academic_year=year,
    )

    _, snap_2 = upload_preview_and_confirm(
        token=apex["token"],
        prog_id=apex["prog_id"],
        file_rows=rows_2,
        mark_authoritative=False,
        academic_year=year,
    )

    # Promote snap 2
    res_prom = client.post(
        f"/api/v1/snapshots/{snap_2}/promote",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={"reason": "Audited promotion"},
    )
    assert res_prom.status_code == 200
    audit_event_id = res_prom.json()["audit_event_id"]

    db = SessionLocal()
    try:
        # Check PROMOTE_SNAPSHOT event
        promote_evt = db.get(AuditEvent, uuid.UUID(audit_event_id))
        assert promote_evt is not None
        assert promote_evt.action == "PROMOTE_SNAPSHOT"
        assert promote_evt.entity_id == uuid.UUID(snap_2)

        # Check SUPERSEDE_SNAPSHOT event
        supersede_evt = db.execute(
            select(AuditEvent).where(
                AuditEvent.action == "SUPERSEDE_SNAPSHOT",
                AuditEvent.entity_id == uuid.UUID(snap_1),
            )
        ).scalar_one_or_none()
        assert supersede_evt is not None
        assert supersede_evt.metadata_payload["superseded_by_snapshot_id"] == snap_2

        # Check cryptographic chaining
        assert promote_evt.previous_event_hash == supersede_evt.event_hash
    finally:
        db.close()


# =========================================================================
# 4. Snapshot Listing and Object-Level Tenancy
# =========================================================================
def test_snapshot_listing_and_tenancy(seeded_tokens):
    """
    Verify:
    1. Apex Admin listing returns only Apex snapshots.
    2. Apex Admin attempting to query with Poly institution_id receives 403 Forbidden.
    3. System Admin can query snapshots with or without institution filter.
    4. Object-level GET /snapshots/{id} restricts access across tenants.
    """
    apex = seeded_tokens["apex"]
    poly = seeded_tokens["poly"]
    sys = seeded_tokens["sys"]

    # 1. Apex Admin list
    res_list = client.get("/api/v1/snapshots", headers={"Authorization": f"Bearer {apex['token']}"})
    assert res_list.status_code == 200
    items = res_list.json()["items"]
    for it in items:
        assert it["institution_id"] == apex["inst_id"]

    # 2. Apex Admin query with external institution_id -> 403
    res_forbidden = client.get(
        f"/api/v1/snapshots?institution_id={poly['inst_id']}",
        headers={"Authorization": f"Bearer {apex['token']}"},
    )
    assert res_forbidden.status_code == 403

    # 3. System Admin can query with Poly institution_id -> 200
    res_sys = client.get(
        f"/api/v1/snapshots?institution_id={poly['inst_id']}",
        headers={"Authorization": f"Bearer {sys['token']}"},
    )
    assert res_sys.status_code == 200

    # 4. Object-level GET check
    # Create Poly snapshot
    year = f"2024-POLY-{uuid.uuid4().hex[:4]}"
    rows = [["student_id", "full_name", "apaar_id", "student_status"], ["P1", "Poly Student", "999900001111", "ACTIVE"]]
    _, poly_snap_id = upload_preview_and_confirm(
        token=poly["token"],
        prog_id=poly["prog_id"],
        file_rows=rows,
        mark_authoritative=True,
        academic_year=year,
    )

    # Apex Admin attempts to GET Poly snapshot -> 403
    res_poly_get = client.get(
        f"/api/v1/snapshots/{poly_snap_id}",
        headers={"Authorization": f"Bearer {apex['token']}"},
    )
    assert res_poly_get.status_code == 403

    # Poly Admin GET Poly snapshot -> 200
    res_poly_owner = client.get(
        f"/api/v1/snapshots/{poly_snap_id}",
        headers={"Authorization": f"Bearer {poly['token']}"},
    )
    assert res_poly_owner.status_code == 200
    assert res_poly_owner.json()["id"] == poly_snap_id
    assert res_poly_owner.json()["source_submission_filename"] is not None


# =========================================================================
# 5. Deterministic Snapshot Comparison Engine (All 8 Classifications)
# =========================================================================
def test_snapshot_comparison_engine_classifications(seeded_tokens):
    """
    Test Snapshot Comparison Engine across all 8 required categories:
    - CONTINUING
    - WITHDRAWN
    - DOCUMENTED_TRANSFER
    - UNEXPLAINED_APPEARANCE
    - UNEXPLAINED_DISAPPEARANCE
    - ADDED
    - AMBIGUOUS_IDENTITY
    - INSUFFICIENT_EVIDENCE
    """
    apex = seeded_tokens["apex"]
    poly = seeded_tokens["poly"]
    year = f"2024-COMP-{uuid.uuid4().hex[:4]}"

    # Baseline Roster Setup
    # S_CONT: Continuing
    # S_WITH: Withdrawn
    # S_DIS: Disappeared without documentation
    # S_TR_OUT: Transferred out with Documented TransferEvent
    # S_AMB: Ambiguous identity (missing APAAR)
    rows_base = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        ["S_CONT", "Student Continuing", "100020003001", "ACTIVE"],
        ["S_WITH", "Student Withdrawn", "100020003002", "ACTIVE"],
        ["S_DIS", "Student Disappeared", "100020003003", "ACTIVE"],
        ["S_TR_OUT", "Student Transferred Out", "100020003004", "ACTIVE"],
        ["S_AMB", "Student Ambiguous", "", "ACTIVE"],  # Missing APAAR
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
        # Find Student Identity for S_TR_OUT to create a Documented TransferEvent
        s_tr_ident = db.execute(
            select(StudentIdentity).where(StudentIdentity.full_name == "Student Transferred Out")
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

        # Candidate Roster Setup
        # S_CONT: still ACTIVE -> CONTINUING
        # S_WITH: status WITHDRAWN -> WITHDRAWN
        # S_DIS: absent -> UNEXPLAINED_DISAPPEARANCE
        # S_TR_OUT: absent -> DOCUMENTED_TRANSFER
        # S_AMB: present -> AMBIGUOUS_IDENTITY
        # S_ADD: new student with AdmissionEpisode -> ADDED
        # S_APP: new student without AdmissionEpisode -> UNEXPLAINED_APPEARANCE
        rows_cand = [
            ["student_id", "full_name", "apaar_id", "student_status"],
            ["S_CONT", "Student Continuing", "100020003001", "ACTIVE"],
            ["S_WITH", "Student Withdrawn", "100020003002", "WITHDRAWN"],
            ["S_AMB", "Student Ambiguous", "", "ACTIVE"],
            ["S_ADD", "Student Added Cohort", "100020003005", "ACTIVE"],
            ["S_APP", "Student Unexpected Appearance", "100020003006", "ACTIVE"],
        ]

        sub_id_cand, cand_snap_id = upload_preview_and_confirm(
            token=apex["token"],
            prog_id=apex["prog_id"],
            file_rows=rows_cand,
            mark_authoritative=False,
            academic_year=year,
        )

        # Link AdmissionEpisode for S_ADD
        s_add_ident = db.execute(
            select(StudentIdentity).where(StudentIdentity.full_name == "Student Added Cohort")
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

        # Execute Comparison via API
        res_comp = client.get(
            f"/api/v1/snapshots/{cand_snap_id}/compare?baseline_id={base_snap_id}",
            headers={"Authorization": f"Bearer {apex['token']}"},
        )
        assert res_comp.status_code == 200, res_comp.text
        data = res_comp.json()
        assert data["candidate_snapshot_id"] == cand_snap_id
        assert data["baseline_snapshot_id"] == base_snap_id

        metrics = data["summary_metrics"]
        records = data["records"]
        by_name = {r["student_name"]: r for r in records}

        # Assert Classifications
        assert by_name["Student Continuing"]["classification"] == "CONTINUING"
        assert by_name["Student Withdrawn"]["classification"] == "WITHDRAWN"
        assert by_name["Student Ambiguous"]["classification"] == "AMBIGUOUS_IDENTITY"
        assert by_name["Student Added Cohort"]["classification"] == "ADDED"
        assert by_name["Student Unexpected Appearance"]["classification"] == "UNEXPLAINED_APPEARANCE"
        assert by_name["Student Transferred Out"]["classification"] == "DOCUMENTED_TRANSFER"
        assert by_name["Student Disappeared"]["classification"] == "UNEXPLAINED_DISAPPEARANCE"

        # Verify explainable, non-punitive rationale
        for r in records:
            assert len(r["explanation"]) > 10
            assert "fraud" not in r["explanation"].lower()
            assert "crime" not in r["explanation"].lower()
            assert r["provenance"] is not None

        # Verify summary metrics counts
        assert metrics["CONTINUING"] == 1
        assert metrics["WITHDRAWN"] == 1
        assert metrics["AMBIGUOUS_IDENTITY"] == 2  # Both candidate and baseline provisional records are ambiguous
        assert metrics["ADDED"] == 1
        assert metrics["UNEXPLAINED_APPEARANCE"] == 1
        assert metrics["DOCUMENTED_TRANSFER"] == 1
        assert metrics["UNEXPLAINED_DISAPPEARANCE"] == 1
    finally:
        db.close()


# =========================================================================
# 6. Comparison with No Baseline (Insufficient Evidence Handling)
# =========================================================================
def test_snapshot_comparison_without_baseline(seeded_tokens):
    """
    When no baseline snapshot exists and student has no admission episode,
    the record is classified as INSUFFICIENT_EVIDENCE.
    """
    apex = seeded_tokens["apex"]
    # Create an isolated temporary programme with 0 historical snapshots
    db = SessionLocal()
    clean_prog_id = None
    try:
        prog = Programme(
            institution_id=uuid.UUID(apex["inst_id"]),
            programme_code=f"ISO_TEST_{uuid.uuid4().hex[:6]}",
            programme_name="Isolated Test Programme",
            qualification_level="UG",
            duration_years=4,
            status="ACTIVE",
        )
        db.add(prog)
        db.commit()
        clean_prog_id = str(prog.id)

        year = f"2029-NOBASE-{uuid.uuid4().hex[:4]}"
        rows = [
            ["student_id", "full_name", "apaar_id", "student_status"],
            ["S_UNEV", "Student Without Evidence", "888877776666", "ACTIVE"],
        ]

        _, cand_snap_id = upload_preview_and_confirm(
            token=apex["token"],
            prog_id=clean_prog_id,
            file_rows=rows,
            mark_authoritative=False,
            academic_year=year,
        )

        res_comp = client.get(
            f"/api/v1/snapshots/{cand_snap_id}/compare",
            headers={"Authorization": f"Bearer {apex['token']}"},
        )
        assert res_comp.status_code == 200, res_comp.text
        data = res_comp.json()
        assert data["baseline_snapshot_id"] is None
        record = data["records"][0]
        assert record["classification"] == "INSUFFICIENT_EVIDENCE"
        assert "Baseline roster unavailable" in record["explanation"]
    finally:
        db.close()
        if clean_prog_id:
            clean_db = SessionLocal()
            try:
                prog_uid = uuid.UUID(clean_prog_id)
                clean_db.query(AnnualRosterObservation).filter_by(programme_id=prog_uid).delete(synchronize_session=False)
                clean_db.query(RosterSnapshot).filter_by(programme_id=prog_uid).delete(synchronize_session=False)
                subs = clean_db.query(SourceSubmission.id).filter_by(programme_id=prog_uid).all()
                sub_ids = [s[0] for s in subs]
                if sub_ids:
                    clean_db.query(SubmissionPreview).filter(SubmissionPreview.submission_id.in_(sub_ids)).delete(synchronize_session=False)
                    clean_db.query(SourceSubmissionRecord).filter(SourceSubmissionRecord.submission_id.in_(sub_ids)).delete(synchronize_session=False)
                clean_db.query(SourceSubmission).filter_by(programme_id=prog_uid).delete(synchronize_session=False)
                clean_db.query(AdmissionEpisode).filter_by(programme_id=prog_uid).delete(synchronize_session=False)
                clean_db.query(InstitutionStudentRecord).filter_by(programme_id=prog_uid).delete(synchronize_session=False)
                clean_db.query(ApprovalConfiguration).filter_by(programme_id=prog_uid).delete(synchronize_session=False)
                clean_db.query(Programme).filter_by(id=prog_uid).delete(synchronize_session=False)
                clean_db.commit()
            except Exception as e:
                clean_db.rollback()
            finally:
                clean_db.close()


# =========================================================================
# 7. Export Sidecars and Formula Injection Defusing (CWE-1236)
# =========================================================================
def test_export_roster_and_comparison_with_formula_defusing(seeded_tokens):
    """
    Verify:
    1. CSV export defuses formula injection characters (=, +, -, @, \\t, \\r).
    2. XLSX export produces valid multi-sheet workbook with styled headers and metadata.
    3. Comparison export produces valid CSV and XLSX.
    4. Tenancy isolation forbids unauthorized downloads.
    """
    apex = seeded_tokens["apex"]
    poly = seeded_tokens["poly"]
    year = f"2024-EXP-{uuid.uuid4().hex[:4]}"

    # Injection payloads: =, +, -, @
    u4 = uuid.uuid4().hex[:4]
    rows_injection = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        ["S_EQUAL", "=cmd|' /C calc'!A0", f"88112233{u4}", "ACTIVE"],
        ["S_PLUS", "+SUM(A1:A10)", f"88112234{u4}", "ACTIVE"],
        ["S_MINUS", "-DDE('cmd';'calc')", f"88112235{u4}", "ACTIVE"],
        ["S_AT", "@HYPERLINK('http://evil.com')", f"88112236{u4}", "ACTIVE"],
    ]

    _, snap_id = upload_preview_and_confirm(
        token=apex["token"],
        prog_id=apex["prog_id"],
        file_rows=rows_injection,
        mark_authoritative=True,
        academic_year=year,
    )

    # 1. Test CSV Export of Snapshot Roster
    res_csv = client.get(
        f"/api/v1/snapshots/{snap_id}/export?format=csv",
        headers={"Authorization": f"Bearer {apex['token']}"},
    )
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    assert f'filename="roster_snapshot_{year}_{snap_id}.csv"' in res_csv.headers["content-disposition"]
    csv_text = res_csv.content.decode("utf-8-sig")

    # Formula characters must be prepended with '
    assert "'=cmd|' /C calc'!A0" in csv_text
    assert "'+SUM(A1:A10)" in csv_text
    assert "'-DDE('cmd';'calc')" in csv_text
    assert "'@HYPERLINK('http://evil.com')" in csv_text

    # 2. Test XLSX Export of Snapshot Roster
    res_xlsx = client.get(
        f"/api/v1/snapshots/{snap_id}/export?format=xlsx",
        headers={"Authorization": f"Bearer {apex['token']}"},
    )
    assert res_xlsx.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in res_xlsx.headers["content-type"]
    
    # Parse XLSX workbook
    wb = openpyxl.load_workbook(io.BytesIO(res_xlsx.content))
    assert "Roster Snapshot" in wb.sheetnames
    assert "Report Metadata" in wb.sheetnames

    ws_data = wb["Roster Snapshot"]
    names_in_sheet = [ws_data.cell(row=r, column=2).value for r in range(2, ws_data.max_row + 1)]
    assert "'=cmd|' /C calc'!A0" in names_in_sheet
    assert "'+SUM(A1:A10)" in names_in_sheet

    # 3. Test Comparison Export (CSV and XLSX)
    res_comp_csv = client.get(
        f"/api/v1/snapshots/{snap_id}/compare/export?format=csv",
        headers={"Authorization": f"Bearer {apex['token']}"},
    )
    assert res_comp_csv.status_code == 200
    assert "text/csv" in res_comp_csv.headers["content-type"]

    res_comp_xlsx = client.get(
        f"/api/v1/snapshots/{snap_id}/compare/export?format=xlsx",
        headers={"Authorization": f"Bearer {apex['token']}"},
    )
    assert res_comp_xlsx.status_code == 200
    wb_comp = openpyxl.load_workbook(io.BytesIO(res_comp_xlsx.content))
    assert "Comparison Report" in wb_comp.sheetnames
    assert "Report Metadata" in wb_comp.sheetnames

    # 4. Tenancy Check on Export
    # Poly Admin attempting to export Apex snapshot -> 403
    res_tenancy_csv = client.get(
        f"/api/v1/snapshots/{snap_id}/export?format=csv",
        headers={"Authorization": f"Bearer {poly['token']}"},
    )
    assert res_tenancy_csv.status_code == 403

    res_tenancy_comp = client.get(
        f"/api/v1/snapshots/{snap_id}/compare/export?format=csv",
        headers={"Authorization": f"Bearer {poly['token']}"},
    )
    assert res_tenancy_comp.status_code == 403


# =========================================================================
# 8. Concurrent Promotions Serialized by Advisory Lock
# =========================================================================
def test_concurrent_promotions_serialized_safely(seeded_tokens):
    """
    Verify:
    Two concurrent promote requests for candidate snapshots in the same context
    are serialized by PostgreSQL advisory lock without deadlocks or unhandled unique violations.
    """
    apex = seeded_tokens["apex"]
    year = f"2024-CONC-{uuid.uuid4().hex[:4]}"
    rows_a = [["student_id", "full_name", "apaar_id", "student_status"], ["S1", "User One", "919191919191", "ACTIVE"]]
    rows_b = [["student_id", "full_name", "apaar_id", "student_status"], ["S1", "User One Beta", "919191919191", "ACTIVE"]]

    _, snap_a = upload_preview_and_confirm(
        token=apex["token"],
        prog_id=apex["prog_id"],
        file_rows=rows_a,
        mark_authoritative=False,
        academic_year=year,
    )
    _, snap_b = upload_preview_and_confirm(
        token=apex["token"],
        prog_id=apex["prog_id"],
        file_rows=rows_b,
        mark_authoritative=False,
        academic_year=year,
    )

    def run_promote(snap_id):
        # Fresh test client call in worker thread
        return client.post(
            f"/api/v1/snapshots/{snap_id}/promote",
            headers={"Authorization": f"Bearer {apex['token']}"},
            json={"reason": f"Concurrent promote for {snap_id}"},
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(run_promote, snap_a)
        f2 = executor.submit(run_promote, snap_b)
        res1 = f1.result()
        res2 = f2.result()

    # Both must return valid status codes (200 OK)
    assert res1.status_code == 200, res1.text
    assert res2.status_code == 200, res2.text

    # In database, exactly one is authoritative
    db = SessionLocal()
    try:
        auths = db.execute(
            select(RosterSnapshot).where(
                RosterSnapshot.institution_id == uuid.UUID(apex["inst_id"]),
                RosterSnapshot.programme_id == uuid.UUID(apex["prog_id"]),
                RosterSnapshot.academic_year == year,
                RosterSnapshot.is_authoritative == True,
            )
        ).scalars().all()
        assert len(auths) == 1
    finally:
        db.close()


# =========================================================================
# 9. Targeted Audit Item 1: Baseline Correctness & Context Validation
# =========================================================================
def test_baseline_correctness_and_context_constraints(seeded_tokens):
    """
    Audit Item 1:
    - Candidate cannot be compared against itself as baseline (400).
    - Cross-programme baseline comparison rejected (400).
    - Baseline chronologically later than candidate rejected (400).
    - Auto-baseline resolution excludes candidate and resolves strictly prior authoritative snapshot.
    """
    apex = seeded_tokens["apex"]
    db = SessionLocal()
    try:
        # Get a second programme at Apex (e.g. ECE)
        progs = db.execute(
            select(Programme).where(Programme.institution_id == uuid.UUID(apex["inst_id"]))
        ).scalars().all()
        assert len(progs) >= 2
        ece_prog_id = str(progs[1].id)
    finally:
        db.close()

    year_23 = f"2023-B1-{uuid.uuid4().hex[:4]}"
    year_24 = f"2024-B1-{uuid.uuid4().hex[:4]}"
    year_25 = f"2025-B1-{uuid.uuid4().hex[:4]}"

    rows_base = [["student_id", "full_name", "apaar_id", "student_status"], ["S1", "Student One", "888800001111", "ACTIVE"]]
    rows_cand = [["student_id", "full_name", "apaar_id", "student_status"], ["S1", "Student One", "888800001111", "ACTIVE"]]

    # Snapshot 2024 (CSE)
    _, snap_24 = upload_preview_and_confirm(
        token=apex["token"],
        prog_id=apex["prog_id"],
        file_rows=rows_cand,
        mark_authoritative=True,
        academic_year=year_24,
    )

    # 1. Candidate comparing against itself -> 400 Bad Request
    res_self = client.get(
        f"/api/v1/snapshots/{snap_24}/compare?baseline_id={snap_24}",
        headers={"Authorization": f"Bearer {apex['token']}"},
    )
    assert res_self.status_code == 400
    assert "cannot compare a snapshot against itself" in res_self.json()["detail"].lower()

    # 2. Cross-programme baseline comparison -> 400 Bad Request
    rows_ece = [["student_id", "full_name", "apaar_id", "student_status"], ["E1", "ECE Student", "888800001112", "ACTIVE"]]
    _, snap_ece = upload_preview_and_confirm(
        token=apex["token"],
        prog_id=ece_prog_id,
        file_rows=rows_ece,
        mark_authoritative=True,
        academic_year=year_24,
    )
    res_cross_prog = client.get(
        f"/api/v1/snapshots/{snap_24}/compare?baseline_id={snap_ece}",
        headers={"Authorization": f"Bearer {apex['token']}"},
    )
    assert res_cross_prog.status_code == 400
    assert "cross-programme" in res_cross_prog.json()["detail"].lower()

    # 3. Chronologically future baseline -> 400 Bad Request
    rows_25 = [["student_id", "full_name", "apaar_id", "student_status"], ["S1", "Student One", "888800001111", "ACTIVE"]]
    _, snap_25 = upload_preview_and_confirm(
        token=apex["token"],
        prog_id=apex["prog_id"],
        file_rows=rows_25,
        mark_authoritative=True,
        academic_year=year_25,
    )
    res_future = client.get(
        f"/api/v1/snapshots/{snap_24}/compare?baseline_id={snap_25}",
        headers={"Authorization": f"Bearer {apex['token']}"},
    )
    assert res_future.status_code == 400
    assert "chronological violation" in res_future.json()["detail"].lower()

    # 4. Auto-baseline: Create 2023 authoritative snapshot for CSE
    rows_23 = [["student_id", "full_name", "apaar_id", "student_status"], ["S1", "Student One", "888800001111", "ACTIVE"]]
    _, snap_23 = upload_preview_and_confirm(
        token=apex["token"],
        prog_id=apex["prog_id"],
        file_rows=rows_23,
        mark_authoritative=True,
        academic_year=year_23,
    )

    # Ingest a non-authoritative candidate revision for 2024
    rows_24_rev = [["student_id", "full_name", "apaar_id", "student_status"], ["S1", "Student One", "888800001111", "ACTIVE"], ["S2", "Student Two", "888800001113", "ACTIVE"]]
    _, snap_24_cand = upload_preview_and_confirm(
        token=apex["token"],
        prog_id=apex["prog_id"],
        file_rows=rows_24_rev,
        mark_authoritative=False,
        academic_year=year_24,
    )

    # Auto-compare without baseline_id should pick the active authoritative snapshot snap_24 (same year)
    res_auto = client.get(
        f"/api/v1/snapshots/{snap_24_cand}/compare",
        headers={"Authorization": f"Bearer {apex['token']}"},
    )
    assert res_auto.status_code == 200
    assert res_auto.json()["baseline_snapshot_id"] == snap_24


# =========================================================================
# 10. Targeted Audit Item 2: Classification Precedence & Reconciliation
# =========================================================================
def test_classification_invariants_and_determinism(seeded_tokens):
    """
    Audit Item 2:
    - All 8 classifications are mutually exclusive.
    - Reconciliation invariant: sum(metrics) == len(records) == TOTAL_RECORDS.
    - Repeated runs with identical inputs produce identical classifications and identical ordering.
    """
    apex = seeded_tokens["apex"]
    year = f"2024-RECON-{uuid.uuid4().hex[:4]}"
    rows = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        ["S1", "Bravo Student", "990011002201", "ACTIVE"],
        ["S2", "Alpha Student", "990011002202", "ACTIVE"],
        ["S3", "Charlie Student", "990011002203", "ACTIVE"],
    ]

    _, snap_cand = upload_preview_and_confirm(
        token=apex["token"],
        prog_id=apex["prog_id"],
        file_rows=rows,
        mark_authoritative=False,
        academic_year=year,
    )

    # Run 1
    res1 = client.get(
        f"/api/v1/snapshots/{snap_cand}/compare",
        headers={"Authorization": f"Bearer {apex['token']}"},
    )
    assert res1.status_code == 200
    data1 = res1.json()

    # Run 2 (Immediately repeated)
    res2 = client.get(
        f"/api/v1/snapshots/{snap_cand}/compare",
        headers={"Authorization": f"Bearer {apex['token']}"},
    )
    assert res2.status_code == 200
    data2 = res2.json()

    # 1. Total Determinism: identical payload, identical ordering
    assert data1 == data2
    order_1 = [r["student_name"] for r in data1["records"]]
    order_2 = [r["student_name"] for r in data2["records"]]
    assert order_1 == order_2

    # 2. Mutual exclusivity and reconciliation
    records = data1["records"]
    metrics = data1["summary_metrics"]
    categories = [
        "ADDED", "CONTINUING", "WITHDRAWN", "DOCUMENTED_TRANSFER",
        "UNEXPLAINED_APPEARANCE", "UNEXPLAINED_DISAPPEARANCE",
        "AMBIGUOUS_IDENTITY", "INSUFFICIENT_EVIDENCE",
    ]
    # Each record has exactly one classification from categories
    for r in records:
        assert r["classification"] in categories

    category_sum = sum(metrics[c] for c in categories)
    assert category_sum == len(records)
    assert metrics["TOTAL_RECORDS"] == len(records)


# =========================================================================
# 11. Targeted Audit Item 3: Comprehensive Formula Injection Matrix
# =========================================================================
def test_comprehensive_formula_injection_matrix(seeded_tokens):
    """
    Audit Item 3:
    - Test formula injection defusing for:
      =1+1, +SUM(A1:A2), -1+2, @SUM(A1:A2), |cmd, %USERPROFILE%
      Leading spaces, leading tabs, carriage returns, newlines followed by formula markers.
      Control-character prefixes.
    - Test that legitimate negative numbers (-5, -12.50) retain their numeric meaning.
    - Verify both CSV and XLSX output.
    """
    from app.services.export_service import defuse_formula_injection, is_pure_number

    # 1. Unit Test Matrix for defuse_formula_injection
    # Formulas and injection vectors -> must be defused (prepended with ')
    malicious_inputs = [
        "=1+1",
        "+SUM(A1:A2)",
        "-1+2",
        "@SUM(A1:A2)",
        "  =1+1",
        "  +SUM(A1:A2)",
        "  -1+2",
        "  @SUM(A1:A2)",
        "\t=1+1",
        "\r=1+1",
        "\n=1+1",
        " \t\r\n=1+1",
        "\x00cmd|' /C calc'!A0",
        "|cmd.exe",
        "%COMSPEC%",
    ]
    for payload in malicious_inputs:
        defused = defuse_formula_injection(payload)
        assert defused.startswith("'"), f"Payload {repr(payload)} was not defused! Result: {repr(defused)}"

    # Legitimate numbers -> must retain numeric value without single quote
    benign_numbers = [
        -5,
        -12.50,
        "-5",
        "-12.50",
        "-0.001",
        "+5",
        "100",
        0,
    ]
    for num in benign_numbers:
        res = defuse_formula_injection(num)
        assert not str(res).startswith("'"), f"Benign number {repr(num)} was wrongly escaped to {repr(res)}"

    # 2. Integration Test via Export API
    apex = seeded_tokens["apex"]
    year = f"2024-INJ-{uuid.uuid4().hex[:4]}"
    rows = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        ["INJ_1", "=1+1", "991122334401", "ACTIVE"],
        ["INJ_2", "  +SUM(A1:A2)", "991122334402", "ACTIVE"],
        ["INJ_3", "\t-1+2", "991122334403", "ACTIVE"],
        ["INJ_4", "  @SUM(A1:A2)", "991122334404", "ACTIVE"],
        ["INJ_5", "|cmd|' /C calc'", "991122334405", "ACTIVE"],
        ["BENIGN_NEG", "-5", "991122334406", "ACTIVE"],
    ]

    _, snap_id = upload_preview_and_confirm(
        token=apex["token"],
        prog_id=apex["prog_id"],
        file_rows=rows,
        mark_authoritative=True,
        academic_year=year,
    )

    # Test CSV
    res_csv = client.get(
        f"/api/v1/snapshots/{snap_id}/export?format=csv",
        headers={"Authorization": f"Bearer {apex['token']}"},
    )
    assert res_csv.status_code == 200
    csv_content = res_csv.content.decode("utf-8-sig")

    assert "'=1+1" in csv_content
    assert "'+SUM(A1:A2)" in csv_content
    assert "'-1+2" in csv_content
    assert "'@SUM(A1:A2)" in csv_content
    assert "'|cmd|' /C calc'" in csv_content
    # Benign negative number is not corrupted with a single quote in CSV
    assert "-5" in csv_content
    assert "'-5" not in csv_content

    # Test XLSX
    res_xlsx = client.get(
        f"/api/v1/snapshots/{snap_id}/export?format=xlsx",
        headers={"Authorization": f"Bearer {apex['token']}"},
    )
    assert res_xlsx.status_code == 200
    wb = openpyxl.load_workbook(io.BytesIO(res_xlsx.content))
    ws = wb["Roster Snapshot"]

    names_in_sheet = [ws.cell(row=r, column=2).value for r in range(2, ws.max_row + 1)]
    assert "'=1+1" in names_in_sheet
    assert "'+SUM(A1:A2)" in names_in_sheet
    assert "'-1+2" in names_in_sheet
    assert "'@SUM(A1:A2)" in names_in_sheet
    assert "'|cmd|' /C calc'" in names_in_sheet
    # -5 is parsed as numeric -5 in XLSX
    assert -5 in names_in_sheet or "-5" in names_in_sheet
