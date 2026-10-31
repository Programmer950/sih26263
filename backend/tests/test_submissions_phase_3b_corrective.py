"""Regression & Corrective Tests for Milestone 3 Phase 3B Findings 1, 2, and 3."""

import pytest
import uuid
import io
import os
import openpyxl
from unittest.mock import patch
from sqlalchemy import select
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.core.database import SessionLocal
from app.models import SourceSubmission, SubmissionPreview, Programme
from app.services.storage_service import StorageService
from app.services.parser_service import (
    ParserService,
    ParsedFileResult,
    InvalidArchiveError,
)

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


def create_sample_csv(rows_data: list, encoding: str = "utf-8") -> io.BytesIO:
    """Helper to create an in-memory CSV file with specific encoding."""
    import csv
    output = io.StringIO()
    writer = csv.writer(output)
    for r in rows_data:
        writer.writerow(r)
    return io.BytesIO(output.getvalue().encode(encoding))


# ============================================================================
# FINDING 1 REGRESSION TESTS: ParserService Signature Mismatch & Determinism
# ============================================================================

def test_finding_1_csv_upload_and_preview(seeded_tokens):
    """Verify parse_file accepts filename and correctly parses valid CSV."""
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]
    csv_bytes = create_sample_csv([
        ["student_id", "full_name", "apaar_id", "student_status"],
        [f"S-{uid}", "Test Student", "123456789012", "ACTIVE"],
    ])

    res = client.post(
        "/api/v1/submissions/upload",
        headers={"Authorization": f"Bearer {apex['token']}"},
        files={"file": (f"valid_{uid}.csv", csv_bytes, "text/csv")},
        data={"programme_id": apex["prog_id"], "academic_year": "2024-25", "submission_type": "ANNUAL_ROSTER"},
    )
    assert res.status_code == 201, res.text
    sub_id = res.json()["submission_id"]

    res_prev = client.post(
        f"/api/v1/submissions/{sub_id}/preview",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={"column_mapping": {"student_id": "student_id", "full_name": "full_name", "apaar_id": "apaar_id", "student_status": "student_status"}},
    )
    assert res_prev.status_code == 200, res_prev.text


def test_finding_1_xlsx_upload_and_preview(seeded_tokens):
    """Verify parse_file accepts filename and correctly parses valid XLSX."""
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["student_id", "full_name", "apaar_id", "student_status"])
    ws.append([f"X-{uid}", "Excel Student", "987654321098", "ACTIVE"])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    res = client.post(
        "/api/v1/submissions/upload",
        headers={"Authorization": f"Bearer {apex['token']}"},
        files={"file": (f"valid_{uid}.xlsx", buf, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"programme_id": apex["prog_id"], "academic_year": "2024-25", "submission_type": "ANNUAL_ROSTER"},
    )
    assert res.status_code == 201, res.text
    sub_id = res.json()["submission_id"]

    res_prev = client.post(
        f"/api/v1/submissions/{sub_id}/preview",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={"column_mapping": {"student_id": "student_id", "full_name": "full_name", "apaar_id": "apaar_id", "student_status": "student_status"}},
    )
    assert res_prev.status_code == 200, res_prev.text


def test_finding_1_unsupported_file_types(seeded_tokens):
    """Verify rejection of prohibited binary types (PDF, executable)."""
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]

    # 1. Fake PDF
    pdf_buf = io.BytesIO(b"%PDF-1.5 fake pdf content\n%%EOF")
    res_pdf = client.post(
        "/api/v1/submissions/upload",
        headers={"Authorization": f"Bearer {apex['token']}"},
        files={"file": (f"test_{uid}.pdf", pdf_buf, "application/pdf")},
        data={"programme_id": apex["prog_id"], "academic_year": "2024-25", "submission_type": "ANNUAL_ROSTER"},
    )
    assert res_pdf.status_code == 400
    assert "PDF documents are not supported" in res_pdf.text

    # 2. Fake Windows EXE (MZ header)
    exe_buf = io.BytesIO(b"MZ\x90\x00\x03\x00\x00\x00")
    res_exe = client.post(
        "/api/v1/submissions/upload",
        headers={"Authorization": f"Bearer {apex['token']}"},
        files={"file": (f"test_{uid}.exe", exe_buf, "application/octet-stream")},
        data={"programme_id": apex["prog_id"], "academic_year": "2024-25", "submission_type": "ANNUAL_ROSTER"},
    )
    assert res_exe.status_code == 400
    assert "Executable binary files are strictly prohibited" in res_exe.text or "binary control bytes" in res_exe.text

    # 3. Direct ParserService check for MZ header
    tmp_exe = os.path.join(settings.UPLOAD_DIR, f"temp_exe_{uid}.dat")
    with open(tmp_exe, "wb") as f:
        f.write(b"MZ\x90\x00executable")
    try:
        with pytest.raises(ValueError, match="Executable binary files are strictly prohibited"):
            ParserService.parse_file(tmp_exe)
    finally:
        if os.path.exists(tmp_exe):
            os.remove(tmp_exe)


def test_finding_1_contradictory_filename_extension_and_content(seeded_tokens):
    """Verify rejection when filename claims one format but content is contradictory."""
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]

    # 1. File named .xlsx but content is plain text CSV
    fake_xlsx_buf = io.BytesIO(b"student_id,name\n1,Alice\n")
    res1 = client.post(
        "/api/v1/submissions/upload",
        headers={"Authorization": f"Bearer {apex['token']}"},
        files={"file": (f"fake_{uid}.xlsx", fake_xlsx_buf, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"programme_id": apex["prog_id"], "academic_year": "2024-25", "submission_type": "ANNUAL_ROSTER"},
    )
    assert res1.status_code == 400
    assert "Contradictory file format" in res1.text
    assert "has an XLSX extension but" in res1.text

    # 2. File named .csv but content is binary ZIP / XLSX
    wb = openpyxl.Workbook()
    wb.active.append(["student_id", "name"])
    fake_csv_buf = io.BytesIO()
    wb.save(fake_csv_buf)
    fake_csv_buf.seek(0)

    res2 = client.post(
        "/api/v1/submissions/upload",
        headers={"Authorization": f"Bearer {apex['token']}"},
        files={"file": (f"fake_{uid}.csv", fake_csv_buf, "text/csv")},
        data={"programme_id": apex["prog_id"], "academic_year": "2024-25", "submission_type": "ANNUAL_ROSTER"},
    )
    assert res2.status_code == 400
    assert "Contradictory file format" in res2.text
    assert "has a CSV extension but contains binary ZIP/XLSX" in res2.text


def test_finding_1_malformed_file_rejection(seeded_tokens):
    """Verify safe failure and cleanup when encountering malformed / truncated files."""
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]

    # Truncated ZIP archive
    truncated_buf = io.BytesIO(b"PK\x03\x04\x14\x00\x00\x00truncated content")
    res = client.post(
        "/api/v1/submissions/upload",
        headers={"Authorization": f"Bearer {apex['token']}"},
        files={"file": (f"truncated_{uid}.xlsx", truncated_buf, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"programme_id": apex["prog_id"], "academic_year": "2024-25", "submission_type": "ANNUAL_ROSTER"},
    )
    assert res.status_code == 400
    assert "Corrupt or invalid ZIP archive" in res.text or "not a valid ZIP/XLSX archive" in res.text


# ============================================================================
# FINDING 2 REGRESSION TESTS: Upload Storage/Database Consistency
# ============================================================================

def test_finding_2_database_commit_failure_cleans_up_file(seeded_tokens):
    """Verify that a database commit failure rolls back transaction and deletes uploaded file."""
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]
    csv_bytes = create_sample_csv([["student_id", "full_name"], [f"S-{uid}", "Name"]])

    saved_storage_keys = []
    orig_save = StorageService.save_upload_stream

    def spy_save(*args, **kwargs):
        res = orig_save(*args, **kwargs)
        saved_storage_keys.append(res[0])
        return res

    with patch.object(StorageService, "save_upload_stream", side_effect=spy_save):
        with patch("sqlalchemy.orm.Session.commit", side_effect=Exception("Simulated commit deadlock")):
            res = client.post(
                "/api/v1/submissions/upload",
                headers={"Authorization": f"Bearer {apex['token']}"},
                files={"file": (f"fail_commit_{uid}.csv", csv_bytes, "text/csv")},
                data={"programme_id": apex["prog_id"], "academic_year": "2024-25", "submission_type": "ANNUAL_ROSTER"},
            )

    assert res.status_code == 500
    assert "A database error occurred" in res.text
    # Verify the stored file was safely deleted (no orphan)
    assert len(saved_storage_keys) == 1
    file_path = StorageService.resolve_safe_path(saved_storage_keys[0])
    assert not os.path.exists(file_path), "File must be deleted after commit failure"


def test_finding_2_refresh_failure_retains_committed_file(seeded_tokens):
    """Verify that if refresh fails AFTER commit, file is NOT deleted (submission is committed)."""
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]
    csv_bytes = create_sample_csv([["student_id", "full_name"], [f"S-{uid}", "Name"]])

    saved_storage_keys = []
    orig_save = StorageService.save_upload_stream

    def spy_save(*args, **kwargs):
        res = orig_save(*args, **kwargs)
        saved_storage_keys.append(res[0])
        return res

    with patch.object(StorageService, "save_upload_stream", side_effect=spy_save):
        with patch("sqlalchemy.orm.Session.refresh", side_effect=Exception("Simulated transient timeout on refresh")):
            res = client.post(
                "/api/v1/submissions/upload",
                headers={"Authorization": f"Bearer {apex['token']}"},
                files={"file": (f"fail_refresh_{uid}.csv", csv_bytes, "text/csv")},
                data={"programme_id": apex["prog_id"], "academic_year": "2024-25", "submission_type": "ANNUAL_ROSTER"},
            )

    # Commit succeeded, so 201 is returned (refresh failure was gracefully logged)
    assert res.status_code == 201
    assert len(saved_storage_keys) == 1
    file_path = StorageService.resolve_safe_path(saved_storage_keys[0])
    assert os.path.exists(file_path), "Committed file must NOT be deleted"


def test_finding_2_cleanup_failure_does_not_crash_server(seeded_tokens):
    """Verify that if delete_file fails during failure cleanup, it logs error without crashing."""
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]
    csv_bytes = create_sample_csv([["student_id", "full_name"], [f"S-{uid}", "Name"]])

    with patch("sqlalchemy.orm.Session.commit", side_effect=Exception("Simulated DB failure")):
        with patch.object(StorageService, "delete_file", side_effect=OSError("Simulated file lock permission error")):
            res = client.post(
                "/api/v1/submissions/upload",
                headers={"Authorization": f"Bearer {apex['token']}"},
                files={"file": (f"fail_cleanup_{uid}.csv", csv_bytes, "text/csv")},
                data={"programme_id": apex["prog_id"], "academic_year": "2024-25", "submission_type": "ANNUAL_ROSTER"},
            )

    assert res.status_code == 500
    assert "A database error occurred" in res.text


def test_finding_2_retry_after_failed_upload(seeded_tokens):
    """Verify that retrying after a failed commit upload succeeds cleanly."""
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]
    csv_content = [["student_id", "full_name"], [f"RETRY-{uid}", "Retry Student"]]

    # Attempt 1: Fails during commit
    with patch("sqlalchemy.orm.Session.commit", side_effect=Exception("First attempt fails")):
        res1 = client.post(
            "/api/v1/submissions/upload",
            headers={"Authorization": f"Bearer {apex['token']}"},
            files={"file": (f"retry_{uid}.csv", create_sample_csv(csv_content), "text/csv")},
            data={"programme_id": apex["prog_id"], "academic_year": "2024-25", "submission_type": "ANNUAL_ROSTER"},
        )
    assert res1.status_code == 500

    # Attempt 2: Without mock, retry succeeds
    res2 = client.post(
        "/api/v1/submissions/upload",
        headers={"Authorization": f"Bearer {apex['token']}"},
        files={"file": (f"retry_{uid}.csv", create_sample_csv(csv_content), "text/csv")},
        data={"programme_id": apex["prog_id"], "academic_year": "2024-25", "submission_type": "ANNUAL_ROSTER"},
    )
    assert res2.status_code == 201


def test_finding_2_no_deletion_of_file_referenced_by_committed_submission(seeded_tokens):
    """Verify that a storage_key referenced by an existing database submission is never deleted."""
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]
    csv_bytes = create_sample_csv([["student_id", "full_name"], [f"NODELETE-{uid}", "Safe Student"]])

    res = client.post(
        "/api/v1/submissions/upload",
        headers={"Authorization": f"Bearer {apex['token']}"},
        files={"file": (f"committed_{uid}.csv", csv_bytes, "text/csv")},
        data={"programme_id": apex["prog_id"], "academic_year": "2024-25", "submission_type": "ANNUAL_ROSTER"},
    )
    assert res.status_code == 201
    sub_id = res.json()["submission_id"]

    db = SessionLocal()
    try:
        sub = db.execute(select(SourceSubmission).where(SourceSubmission.id == uuid.UUID(sub_id))).scalar_one()
        file_path = StorageService.resolve_safe_path(sub.storage_key)
        assert os.path.exists(file_path), "Committed file must exist"

        # Verify that an active/committed reference check returns the ID
        ref = db.execute(select(SourceSubmission.id).where(SourceSubmission.storage_key == sub.storage_key)).scalar_one_or_none()
        assert ref == sub.id
    finally:
        db.close()


# ============================================================================
# FINDING 3 REGRESSION TESTS: CSV Encoding Provenance & Fallback Metadata
# ============================================================================

def test_finding_3_utf8_with_bom():
    """Verify utf-8-sig encoded CSV correctly records encoding and strips BOM."""
    raw_bytes = b"\xef\xbb\xbfstudent_id,full_name\nBOM-01,Aditi Sharma\n"
    tmp_path = os.path.join(settings.UPLOAD_DIR, f"temp_bom_{uuid.uuid4().hex[:6]}.csv")
    with open(tmp_path, "wb") as f:
        f.write(raw_bytes)

    try:
        res: ParsedFileResult = ParserService.parse_csv(tmp_path)
        assert res.encoding == "utf-8-sig"
        assert res.headers == ["student_id", "full_name"]
        assert res.rows[0].parsed_payload["student_id"] == "BOM-01"
        assert not any("latin-1" in w for w in res.warnings)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_finding_3_plain_utf8():
    """Verify standard UTF-8 encoded CSV records utf-8 without warnings."""
    raw_bytes = "student_id,full_name\nPLAIN-01,Rajesh Kumar\n".encode("utf-8")
    tmp_path = os.path.join(settings.UPLOAD_DIR, f"temp_plain_{uuid.uuid4().hex[:6]}.csv")
    with open(tmp_path, "wb") as f:
        f.write(raw_bytes)

    try:
        res: ParsedFileResult = ParserService.parse_csv(tmp_path)
        assert res.encoding == "utf-8"
        assert res.headers == ["student_id", "full_name"]
        assert res.rows[0].parsed_payload["student_id"] == "PLAIN-01"
        assert not any("latin-1" in w for w in res.warnings)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_finding_3_latin1_fallback_and_warning():
    """Verify Latin-1 fallback is recorded and review warning is emitted."""
    # 0xE9 is 'é' in Latin-1, which is invalid UTF-8 without multibyte prefix
    raw_bytes = b"student_id,full_name\nLATIN-01,Ren\xe9e Dupont\n"
    tmp_path = os.path.join(settings.UPLOAD_DIR, f"temp_latin_{uuid.uuid4().hex[:6]}.csv")
    with open(tmp_path, "wb") as f:
        f.write(raw_bytes)

    try:
        res: ParsedFileResult = ParserService.parse_csv(tmp_path)
        assert res.encoding == "latin-1"
        assert res.rows[0].raw_payload["full_name"] == "Renée Dupont"
        # Must emit review warning for Latin-1 fallback
        assert any("File decoded using fallback encoding 'latin-1'" in w for w in res.warnings)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_finding_3_invalid_or_malformed_csv_null_bytes():
    """Verify CSV containing binary null bytes is rejected safely."""
    raw_bytes = b"student_id,full_name\x00\x00binary junk\n"
    tmp_path = os.path.join(settings.UPLOAD_DIR, f"temp_null_{uuid.uuid4().hex[:6]}.csv")
    with open(tmp_path, "wb") as f:
        f.write(raw_bytes)

    try:
        with pytest.raises(ValueError, match="null bytes detected"):
            ParserService.parse_csv(tmp_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_finding_3_encoding_metadata_in_preview_and_submission(seeded_tokens):
    """Verify detected_encoding is present in upload and preview API responses and validation summary."""
    apex = seeded_tokens["apex"]
    uid = uuid.uuid4().hex[:6]
    csv_bytes = create_sample_csv([["student_id", "full_name", "apaar_id"], [f"ENC-{uid}", "Student", "123456789012"]])

    # 1. Upload response includes detected_encoding
    res_upload = client.post(
        "/api/v1/submissions/upload",
        headers={"Authorization": f"Bearer {apex['token']}"},
        files={"file": (f"enc_{uid}.csv", csv_bytes, "text/csv")},
        data={"programme_id": apex["prog_id"], "academic_year": "2024-25", "submission_type": "ANNUAL_ROSTER"},
    )
    assert res_upload.status_code == 201
    upload_data = res_upload.json()
    assert upload_data["detected_encoding"] in ["utf-8", "utf-8-sig"]
    sub_id = upload_data["submission_id"]

    # 2. Preview response includes detected_encoding
    res_prev = client.post(
        f"/api/v1/submissions/{sub_id}/preview",
        headers={"Authorization": f"Bearer {apex['token']}"},
        json={"column_mapping": {"student_id": "student_id", "full_name": "full_name", "apaar_id": "apaar_id"}},
    )
    assert res_prev.status_code == 200
    prev_data = res_prev.json()
    assert prev_data["detected_encoding"] in ["utf-8", "utf-8-sig"]
    assert prev_data["validation_summary"]["detected_encoding"] in ["utf-8", "utf-8-sig"]
