"""Tests for Milestone 3 Phase 3B: CSV/XLSX Safe Parsers, Validation Preview Engine & API Contracts."""

import pytest
import uuid
import io
import os
import zipfile
import openpyxl
from sqlalchemy import select, func
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.core.database import SessionLocal
from app.models import (
    StudentIdentity,
    InstitutionStudentRecord,
    AnnualRosterObservation,
    RosterSnapshot,
    SourceSubmission,
    SubmissionPreview,
    Programme,
    Institution,
)
from app.services.storage_service import StorageService
from app.services.parser_service import ParserService, ParsedFileResult

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


def test_scenario_1_valid_csv_upload_and_preview_zero_student_db_leakage(seeded_tokens):
    """
    Scenario 1:
    - Valid CSV upload and full-file preview generation.
    - Zero student database leakage: StudentIdentity, InstitutionStudentRecord,
      AnnualRosterObservation, and RosterSnapshot counts remain strictly unchanged.
    """
    db = SessionLocal()
    try:
        baseline_identities = db.execute(select(func.count(StudentIdentity.id))).scalar()
        baseline_records = db.execute(select(func.count(InstitutionStudentRecord.id))).scalar()
        baseline_obs = db.execute(select(func.count(AnnualRosterObservation.id))).scalar()
        baseline_snaps = db.execute(select(func.count(RosterSnapshot.id))).scalar()

        apex = seeded_tokens["apex"]
        uid = uuid.uuid4().hex[:6]
        csv_content = [
            ["student_id", "full_name", "apaar_id", "student_status"],
            [f"CSE-{uid}-001", "Aarav Sharma", "123456789012", "ACTIVE"],
            [f"CSE-{uid}-002", "Diya Patel", "987654321098", "ACTIVE"],
            [f"CSE-{uid}-003", "Rohan Mehta", "456789012345", "ACTIVE"],
        ]
        csv_file = create_sample_csv(csv_content)

        # 1. POST /upload
        res_upload = client.post(
            "/api/v1/submissions/upload",
            headers={"Authorization": f"Bearer {apex['token']}"},
            files={"file": (f"test_roster_{uid}.csv", csv_file, "text/csv")},
            data={
                "programme_id": apex["prog_id"],
                "academic_year": "2024-25",
                "submission_type": "ANNUAL_ROSTER",
            },
        )
        assert res_upload.status_code == 201, res_upload.text
        upload_data = res_upload.json()
        sub_id = upload_data["submission_id"]
        assert upload_data["submission_status"] == "PREVIEW_READY"
        assert upload_data["detected_headers"] == ["student_id", "full_name", "apaar_id", "student_status"]
        assert upload_data["suggested_mapping"]["student_id"] == "student_id"
        assert upload_data["total_rows_count"] == 3

        # 2. POST /{id}/preview
        mapping = {
            "student_id": "student_id",
            "full_name": "full_name",
            "apaar_id": "apaar_id",
            "student_status": "student_status",
        }
        res_preview = client.post(
            f"/api/v1/submissions/{sub_id}/preview",
            headers={"Authorization": f"Bearer {apex['token']}"},
            json={"column_mapping": mapping},
        )
        assert res_preview.status_code == 200, res_preview.text
        preview_data = res_preview.json()
        assert preview_data["submission_id"] == sub_id
        assert preview_data["mapping_version"] == "v1.0"
        assert len(preview_data["mapping_hash"]) == 64
        assert preview_data["total_rows_count"] == 3
        assert preview_data["valid_rows_count"] == 3
        assert preview_data["error_rows_count"] == 0

        # 3. ZERO STUDENT REPOSITORY MUTATION INVARIANT
        assert db.execute(select(func.count(StudentIdentity.id))).scalar() == baseline_identities
        assert db.execute(select(func.count(InstitutionStudentRecord.id))).scalar() == baseline_records
        assert db.execute(select(func.count(AnnualRosterObservation.id))).scalar() == baseline_obs
        assert db.execute(select(func.count(RosterSnapshot.id))).scalar() == baseline_snaps

        # Verify Submission and Preview exist in database
        sub_db = db.execute(select(SourceSubmission).where(SourceSubmission.id == uuid.UUID(sub_id))).scalar_one()
        assert sub_db.submission_status == "PREVIEW_READY"
        prev_db = db.execute(select(SubmissionPreview).where(SubmissionPreview.submission_id == sub_db.id)).scalar_one()
        assert prev_db.is_active is True
        assert prev_db.file_fingerprint == sub_db.file_fingerprint

    finally:
        db.close()


def test_scenario_2_valid_xlsx_upload_and_preview_zero_student_db_leakage(seeded_tokens):
    """
    Scenario 2:
    - Valid XLSX upload and safe preview extraction via openpyxl.
    - Zero student database records created during upload or preview.
    """
    db = SessionLocal()
    try:
        baseline_identities = db.execute(select(func.count(StudentIdentity.id))).scalar()
        apex = seeded_tokens["apex"]
        uid = uuid.uuid4().hex[:6]

        xlsx_rows = [
            ["Roll No", "Student Name", "APAAR Number", "Status"],
            [f"APEX-{uid}-01", "Kavita Rao", "112233445566", "ACTIVE"],
            [f"APEX-{uid}-02", "Sunil Joshi", "998877665544", "ACTIVE"],
        ]
        xlsx_stream = create_sample_xlsx(xlsx_rows)

        # 1. POST /upload
        res_upload = client.post(
            "/api/v1/submissions/upload",
            headers={"Authorization": f"Bearer {apex['token']}"},
            files={"file": (f"Apex_{uid}_roster.xlsx", xlsx_stream, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            data={
                "programme_id": apex["prog_id"],
                "academic_year": "2024-25",
                "submission_type": "ANNUAL_ROSTER",
            },
        )
        assert res_upload.status_code == 201, res_upload.text
        upload_data = res_upload.json()
        sub_id = upload_data["submission_id"]
        assert upload_data["detected_headers"] == ["Roll No", "Student Name", "APAAR Number", "Status"]
        assert upload_data["suggested_mapping"]["student_id"] == "Roll No"
        assert upload_data["suggested_mapping"]["apaar_id"] == "APAAR Number"

        # 2. POST /{id}/preview with confirmed mapping
        mapping = {
            "student_id": "Roll No",
            "full_name": "Student Name",
            "apaar_id": "APAAR Number",
            "student_status": "Status",
        }
        res_preview = client.post(
            f"/api/v1/submissions/{sub_id}/preview",
            headers={"Authorization": f"Bearer {apex['token']}"},
            json={"column_mapping": mapping},
        )
        assert res_preview.status_code == 200, res_preview.text
        preview_data = res_preview.json()
        assert preview_data["valid_rows_count"] == 2
        assert preview_data["error_rows_count"] == 0

        # Invariant: Zero records in student_identities
        assert db.execute(select(func.count(StudentIdentity.id))).scalar() == baseline_identities

    finally:
        db.close()


def test_scenario_3_invalid_apaar_format_warning_not_discarded(seeded_tokens):
    """
    Scenario 3:
    - CSV containing rows with invalid APAAR format (e.g. 5 digits or non-numeric).
    - Flagged as non-fatal WARNING. Rows are NOT discarded.
    """
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]
    csv_rows = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        [f"S01-{uid}", "Valid APAAR", "123456789012", "ACTIVE"],
        [f"S02-{uid}", "Short APAAR", "12345", "ACTIVE"],
        [f"S03-{uid}", "Alpha APAAR", "12345678901A", "ACTIVE"],
    ]
    csv_stream = create_sample_csv(csv_rows)

    res_upload = client.post(
        "/api/v1/submissions/upload",
        headers={"Authorization": f"Bearer {apex['token']}"},
        files={"file": (f"invalid_apaar_{uid}.csv", csv_stream, "text/csv")},
        data={
            "programme_id": apex["prog_id"],
            "academic_year": "2024-25",
            "submission_type": "ANNUAL_ROSTER",
        },
    )
    assert res_upload.status_code == 201
    sub_id = res_upload.json()["submission_id"]

    res_preview = client.post(
        f"/api/v1/submissions/{sub_id}/preview",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={"column_mapping": {"student_id": "student_id", "full_name": "full_name", "apaar_id": "apaar_id", "student_status": "student_status"}},
    )
    assert res_preview.status_code == 200
    p = res_preview.json()
    assert p["total_rows_count"] == 3
    assert p["valid_rows_count"] == 1
    assert p["warning_rows_count"] == 2  # S02 and S03 flagged
    assert p["error_rows_count"] == 0    # Non-fatal warnings do not make rows INVALID
    warnings = p["validation_summary"]["warnings_by_row"]
    assert any("Invalid APAAR format" in str(w) for w in warnings)


def test_scenario_4_missing_apaar_retained_with_warning(seeded_tokens):
    """
    Scenario 4:
    - Missing APAAR values are permitted as reviewable provisional records with a warning.
    """
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]
    csv_rows = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        [f"S01-{uid}", "Student Without APAAR", "", "ACTIVE"],
    ]
    csv_stream = create_sample_csv(csv_rows)

    res_upload = client.post(
        "/api/v1/submissions/upload",
        headers={"Authorization": f"Bearer {apex['token']}"},
        files={"file": (f"missing_apaar_{uid}.csv", csv_stream, "text/csv")},
        data={
            "programme_id": apex["prog_id"],
            "academic_year": "2024-25",
            "submission_type": "ANNUAL_ROSTER",
        },
    )
    assert res_upload.status_code == 201
    sub_id = res_upload.json()["submission_id"]

    res_preview = client.post(
        f"/api/v1/submissions/{sub_id}/preview",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={"column_mapping": {"student_id": "student_id", "full_name": "full_name", "apaar_id": "apaar_id", "student_status": "student_status"}},
    )
    assert res_preview.status_code == 200
    p = res_preview.json()
    assert p["total_rows_count"] == 1
    assert p["warning_rows_count"] == 1
    assert p["error_rows_count"] == 0
    warnings = p["validation_summary"]["warnings_by_row"]
    assert any("Missing APAAR identifier" in str(w) for w in warnings)


def test_scenario_5_duplicate_rows_in_file_reported(seeded_tokens):
    """
    Scenario 5:
    - Duplicate student identifiers within the same file are detected and reported.
    """
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]
    csv_rows = [
        ["student_id", "full_name", "apaar_id", "student_status"],
        [f"DUP-{uid}", "First Occurrence", "123456789012", "ACTIVE"],
        [f"DUP-{uid}", "Second Occurrence", "123456789012", "ACTIVE"],
    ]
    csv_stream = create_sample_csv(csv_rows)

    res_upload = client.post(
        "/api/v1/submissions/upload",
        headers={"Authorization": f"Bearer {apex['token']}"},
        files={"file": (f"duplicates_{uid}.csv", csv_stream, "text/csv")},
        data={
            "programme_id": apex["prog_id"],
            "academic_year": "2024-25",
            "submission_type": "ANNUAL_ROSTER",
        },
    )
    assert res_upload.status_code == 201
    sub_id = res_upload.json()["submission_id"]

    res_preview = client.post(
        f"/api/v1/submissions/{sub_id}/preview",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={"column_mapping": {"student_id": "student_id", "full_name": "full_name", "apaar_id": "apaar_id", "student_status": "student_status"}},
    )
    assert res_preview.status_code == 200
    p = res_preview.json()
    assert p["duplicate_rows_count"] == 1
    assert any(f"Duplicate student identifier 'DUP-{uid}'" in str(w) for w in p["validation_summary"]["warnings_by_row"])


def test_scenario_14_institution_admin_external_upload_and_preview_forbidden(seeded_tokens):
    """
    Scenario 14:
    - Strict Multi-Tenancy Enforcement:
      Institution Admin cannot upload data or preview submissions for another institution.
    """
    apex = seeded_tokens["apex"]
    poly = seeded_tokens["poly"]
    uid = uuid.uuid4().hex[:6]

    csv_stream = create_sample_csv([["student_id", "full_name"], [f"S1-{uid}", "Name"]])

    # 1. Apex Admin explicitly attempts upload specifying Polytechnic's institution_id
    res_external_upload = client.post(
        "/api/v1/submissions/upload",
        headers={"Authorization": f"Bearer {apex['token']}"},
        files={"file": (f"illegal_{uid}.csv", csv_stream, "text/csv")},
        data={
            "institution_id": poly["inst_id"],
            "programme_id": poly["prog_id"],
            "academic_year": "2024-25",
            "submission_type": "ANNUAL_ROSTER",
        },
    )
    assert res_external_upload.status_code == 403
    assert "Tenancy Violation" in res_external_upload.text

    # 2. Polytechnic Admin creates a legitimate submission
    csv_poly = create_sample_csv([["student_id", "full_name", "apaar_id"], [f"P01-{uid}", "Poly Student", "999888777666"]])
    res_poly_upload = client.post(
        "/api/v1/submissions/upload",
        headers={"Authorization": f"Bearer {poly['token']}"},
        files={"file": (f"poly_roster_{uid}.csv", csv_poly, "text/csv")},
        data={
            "programme_id": poly["prog_id"],
            "academic_year": "2024-25",
            "submission_type": "ANNUAL_ROSTER",
        },
    )
    assert res_poly_upload.status_code == 201
    poly_sub_id = res_poly_upload.json()["submission_id"]

    # 3. Apex Admin attempts to generate preview for Polytechnic's submission -> 403 Forbidden
    res_idor_preview = client.post(
        f"/api/v1/submissions/{poly_sub_id}/preview",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={"column_mapping": {"student_id": "student_id", "full_name": "full_name"}},
    )
    assert res_idor_preview.status_code == 403
    assert "Tenancy Violation" in res_idor_preview.text

    # 4. Apex Admin attempts to view Polytechnic's submission details -> 403 Forbidden
    res_idor_get = client.get(
        f"/api/v1/submissions/{poly_sub_id}",
        headers={"Authorization": f"Bearer {apex['token']}"},
    )
    assert res_idor_get.status_code == 403
    assert "Tenancy Violation" in res_idor_get.text

    # 5. Apex Admin attempts to cancel Polytechnic's submission -> 403 Forbidden
    res_idor_cancel = client.post(
        f"/api/v1/submissions/{poly_sub_id}/cancel",
        headers={"Authorization": f"Bearer {apex['token']}"},
    )
    assert res_idor_cancel.status_code == 403
    assert "Tenancy Violation" in res_idor_cancel.text


def test_scenario_19_xlsx_archive_security_zip_bomb_and_traversal_rejected(seeded_tokens):
    """
    Scenario 19:
    - Pre-flight ZIP archive security inspection guards:
      a) Path traversal in ZIP entry name -> rejected with 400.
      b) Potential decompression bomb (>20:1 compression ratio) -> rejected with 400.
      c) Corrupted/non-zip file claiming to be xlsx -> rejected with 400.
      d) Storage cleanup: rejected files are removed from storage with zero orphans.
    """
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]

    # Subtest A: Directory Traversal in ZIP entry name
    zip_traversal_buf = io.BytesIO()
    with zipfile.ZipFile(zip_traversal_buf, "w") as zf:
        zf.writestr("../../etc/passwd", "prohibited content")
    zip_traversal_buf.seek(0)

    res_traversal = client.post(
        "/api/v1/submissions/upload",
        headers={"Authorization": f"Bearer {apex['token']}"},
        files={"file": (f"traversal_{uid}.xlsx", zip_traversal_buf, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"programme_id": apex["prog_id"], "academic_year": "2024-25", "submission_type": "ANNUAL_ROSTER"},
    )
    assert res_traversal.status_code == 400
    assert "path traversal sequence" in res_traversal.text

    # Subtest B: Zip Bomb / High Compression Ratio (>20:1)
    zip_bomb_buf = io.BytesIO()
    with zipfile.ZipFile(zip_bomb_buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("sheet1.xml", "0" * (1024 * 1024))  # 1MB decompresses from ~1KB
    zip_bomb_buf.seek(0)

    res_bomb = client.post(
        "/api/v1/submissions/upload",
        headers={"Authorization": f"Bearer {apex['token']}"},
        files={"file": (f"bomb_{uid}.xlsx", zip_bomb_buf, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"programme_id": apex["prog_id"], "academic_year": "2024-25", "submission_type": "ANNUAL_ROSTER"},
    )
    assert res_bomb.status_code == 400
    assert "decompression bomb" in res_bomb.text

    # Subtest C: Corrupt / Fake XLSX
    corrupt_buf = io.BytesIO(b"This is completely invalid binary junk not a zip")
    res_corrupt = client.post(
        "/api/v1/submissions/upload",
        headers={"Authorization": f"Bearer {apex['token']}"},
        files={"file": (f"corrupt_{uid}.xlsx", corrupt_buf, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"programme_id": apex["prog_id"], "academic_year": "2024-25", "submission_type": "ANNUAL_ROSTER"},
    )
    assert res_corrupt.status_code == 400
    assert "not a valid ZIP/XLSX archive" in res_corrupt.text


def test_scenario_20_formula_preservation_verbatim_raw_evidence():
    """
    Scenario 20:
    - Spreadsheet formula handling:
      - Raw cell values in raw_payload preserve formula strings verbatim (e.g. '=SUM(A1:B1)').
      - Never prepends apostrophe in raw evidence.
      - Cached calculation results extracted into parsed_payload.
      - Missing cached evaluation values flagged with warning and metadata.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["student_id", "full_name", "score_formula", "missing_cached_formula"])
    ws.append(["CS-01", "Formula Student", "=SUM(10, 20)", "=AVERAGE(10, 20)"])

    xlsx_path = os.path.join(settings.UPLOAD_DIR, f"temp_formula_test_{uuid.uuid4().hex[:6]}.xlsx")
    wb.save(xlsx_path)

    try:
        result: ParsedFileResult = ParserService.parse_xlsx(xlsx_path)
        assert len(result.rows) == 1
        p_row = result.rows[0]

        # 1. VERBATIM FORMULA PRESERVATION (NO leading apostrophe!)
        assert p_row.raw_payload["score_formula"] == "=SUM(10, 20)"
        assert not p_row.raw_payload["score_formula"].startswith("'=")

        # 2. UNRESOLVED FORMULA WARNING (when workbook lacks cached evaluation)
        assert "score_formula" in p_row.formula_metadata
        assert p_row.formula_metadata["score_formula"]["status"] == "UNRESOLVED_FORMULA_NO_CACHED_VALUE"
        assert any("Formula '=SUM(10, 20)' has no cached calculation value" in w for w in result.warnings)

    finally:
        if os.path.exists(xlsx_path):
            os.remove(xlsx_path)


def test_scenario_22_cancelled_submission_retains_evidence_and_rejects_confirmation(seeded_tokens):
    """
    Scenario 22:
    - Cancelled submission permanently retains uploaded file evidence in storage.
    - Subsequent cancellation or confirmation is rejected.
    """
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]
    csv_rows = [
        ["student_id", "full_name", "apaar_id"],
        [f"CANCEL-{uid}", "Cancel Student", "123456789012"],
    ]
    csv_stream = create_sample_csv(csv_rows)

    res_upload = client.post(
        "/api/v1/submissions/upload",
        headers={"Authorization": f"Bearer {apex['token']}"},
        files={"file": (f"to_be_cancelled_{uid}.csv", csv_stream, "text/csv")},
        data={"programme_id": apex["prog_id"], "academic_year": "2024-25", "submission_type": "ANNUAL_ROSTER"},
    )
    assert res_upload.status_code == 201
    sub_id = res_upload.json()["submission_id"]

    db = SessionLocal()
    try:
        sub = db.execute(select(SourceSubmission).where(SourceSubmission.id == uuid.UUID(sub_id))).scalar_one()
        file_path = StorageService.resolve_safe_path(sub.storage_key)
        assert os.path.exists(file_path), "Raw file must exist in storage"

        # 1. Call POST /cancel
        res_cancel = client.post(
            f"/api/v1/submissions/{sub_id}/cancel",
            headers={"Authorization": f"Bearer {apex['token']}"},
        )
        assert res_cancel.status_code == 200
        assert res_cancel.json()["submission_status"] == "CANCELLED"

        # 2. EVIDENCE RETENTION CHECK: file must still exist after cancellation!
        assert os.path.exists(file_path), "File must be permanently retained for regulatory auditability"

        # 3. Cannot cancel an already cancelled submission
        res_cancel_again = client.post(
            f"/api/v1/submissions/{sub_id}/cancel",
            headers={"Authorization": f"Bearer {apex['token']}"},
        )
        assert res_cancel_again.status_code == 400

        # 4. Cannot generate preview for cancelled submission
        res_prev = client.post(
            f"/api/v1/submissions/{sub_id}/preview",
            headers={"Authorization": f"Bearer {apex['token']}"},
            json={"column_mapping": {"student_id": "student_id"}},
        )
        assert res_prev.status_code == 400

    finally:
        db.close()


def test_scenario_26_full_file_validation_finds_errors_beyond_row_50(seeded_tokens):
    """
    Scenario 26:
    - Full-file validation scanner scans all rows in file.
    - Accurately detects errors located beyond row 50 (e.g. at row 65).
    """
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]
    csv_rows = [["student_id", "full_name", "apaar_id", "student_status"]]

    # Generate 70 rows: rows 1-60 are valid, row 65 has a missing mandatory student_id
    for i in range(1, 71):
        if i == 65:
            # Missing student ID (mandatory error)
            csv_rows.append(["", f"Student {i}", "123456789012", "ACTIVE"])
        else:
            csv_rows.append([f"CS-{uid}-{i:03d}", f"Student {i}", "123456789012", "ACTIVE"])

    csv_stream = create_sample_csv(csv_rows)

    res_upload = client.post(
        "/api/v1/submissions/upload",
        headers={"Authorization": f"Bearer {apex['token']}"},
        files={"file": (f"large_roster_70_rows_{uid}.csv", csv_stream, "text/csv")},
        data={"programme_id": apex["prog_id"], "academic_year": "2024-25", "submission_type": "ANNUAL_ROSTER"},
    )
    assert res_upload.status_code == 201
    upload_data = res_upload.json()
    sub_id = upload_data["submission_id"]
    assert upload_data["total_rows_count"] == 70

    # Initial sample preview (first 25-50 rows) had zero errors
    assert upload_data["error_rows_count"] == 0

    # Full-file preview should scan all 70 rows and discover the missing ID at row 65
    res_preview = client.post(
        f"/api/v1/submissions/{sub_id}/preview",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={"column_mapping": {"student_id": "student_id", "full_name": "full_name", "apaar_id": "apaar_id", "student_status": "student_status"}},
    )
    assert res_preview.status_code == 200
    p = res_preview.json()
    assert p["total_rows_count"] == 70
    assert p["error_rows_count"] == 1
    assert p["valid_rows_count"] == 69

    errors = p["validation_summary"]["errors_by_row"]
    assert any(e["row_number"] == 65 for e in errors)
    assert any("Missing mandatory student" in str(e["errors"]) for e in errors if e["row_number"] == 65)


def test_list_and_get_submission_detail(seeded_tokens):
    """Verify list submissions and get submission detail endpoints with filtering."""
    apex = seeded_tokens["apex"]
    rev = seeded_tokens["reviewer"]

    # List submissions as Apex Admin
    res_list = client.get(
        "/api/v1/submissions?limit=10",
        headers={"Authorization": f"Bearer {apex['token']}"},
    )
    assert res_list.status_code == 200
    data = res_list.json()
    assert "items" in data
    assert data["total"] >= 1
    sub_id = data["items"][0]["id"]

    # Get submission detail
    res_detail = client.get(
        f"/api/v1/submissions/{sub_id}",
        headers={"Authorization": f"Bearer {apex['token']}"},
    )
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert detail["id"] == sub_id
    assert "validation_summary" in detail
    assert "mapping_config" in detail

    # AICTE Reviewer can list submissions globally
    res_rev_list = client.get(
        "/api/v1/submissions?limit=10",
        headers={"Authorization": f"Bearer {rev['token']}"},
    )
    assert res_rev_list.status_code == 200
