"""Tests for Milestone 3 Phase 3A: Submission Ledger, Storage & Idempotency."""

import pytest
import uuid
import io
import os
import hashlib
from datetime import datetime, timezone
from sqlalchemy import select, and_, text
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.database import SessionLocal
from app.models import (
    Institution,
    Programme,
    User,
    Role,
    StudentIdentity,
    InstitutionStudentRecord,
    AnnualRosterObservation,
    SourceSubmission,
    SubmissionPreview,
    SourceSubmissionRecord,
    RosterSnapshot,
)
from app.services.storage_service import (
    StorageService,
    FileSizeExceededError,
    PathTraversalError,
)
from app.services.idempotency_service import (
    IdempotencyService,
    IdempotencyConflictError,
    ContextualDuplicateError,
)


@pytest.fixture(scope="module")
def setup_context():
    """Sets up an institution, programme, and admin user for Phase 3A tests."""
    db = SessionLocal()
    suffix = uuid.uuid4().hex[:6]
    try:
        # Create test institution
        inst = Institution(
            institution_code=f"INST_3A_{suffix}",
            name=f"Phase 3A Institute {suffix}",
            category="ENGINEERING",
            approval_status="APPROVED",
            state="Maharashtra",
            district="Pune",
            pincode="411001",
        )
        db.add(inst)
        db.flush()

        # Create programme
        prog = Programme(
            institution_id=inst.id,
            programme_code=f"CSE_{suffix}",
            programme_name="Computer Science Engineering",
            qualification_level="UG",
            duration_years=4,
            status="ACTIVE",
        )
        db.add(prog)
        db.flush()

        # Get or create admin role
        role = db.execute(select(Role).where(Role.role_name == "INSTITUTION_ADMIN")).scalars().first()
        if not role:
            role = Role(role_name="INSTITUTION_ADMIN", description="Admin", permissions={})
            db.add(role)
            db.flush()

        # Create user
        user = User(
            name=f"Admin {suffix}",
            email=f"admin_{suffix}@test.edu",
            password_hash="mock_hash",
            role_id=role.id,
            institution_id=inst.id,
            status="ACTIVE",
        )
        db.add(user)
        db.commit()

        yield {
            "institution_id": inst.id,
            "programme_id": prog.id,
            "user_id": user.id,
            "academic_year": "2024-25",
        }
    finally:
        db.close()


def test_storage_service_streaming_and_fingerprint():
    """Verify streaming file write, deterministic SHA-256, and cleanup."""
    sample_content = b"roll_no,name,apaar\nCSE-001,Student One,111122223333\nCSE-002,Student Two,222233334444\n"
    stream = io.BytesIO(sample_content)
    expected_hash = hashlib.sha256(sample_content).hexdigest()

    storage_key, fingerprint, size, mime = StorageService.save_upload_stream(
        stream=stream,
        original_filename="test_roster.csv",
    )

    try:
        assert fingerprint == expected_hash
        assert size == len(sample_content)
        assert mime == "text/csv"
        assert storage_key.startswith("uploads/")
        assert StorageService.verify_file_integrity(storage_key, expected_hash) is True
    finally:
        StorageService.delete_file(storage_key)


def test_storage_service_path_traversal_rejection():
    """Verify path traversal attempts are strictly blocked."""
    with pytest.raises(Exception):
        StorageService.resolve_safe_path("../../../etc/passwd")


def test_storage_service_size_limit_and_zero_orphaned_files(monkeypatch):
    """Verify exceeding size limits raises error and leaves zero orphaned disk files."""
    # Temporarily set max size to 100 bytes
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_BYTES", 100)
    oversized_content = b"A" * 500
    stream = io.BytesIO(oversized_content)

    with pytest.raises(FileSizeExceededError):
        StorageService.save_upload_stream(stream, "large_file.csv")

    # Verify no file of size 500 was left behind in upload dir
    upload_dir = settings.UPLOAD_DIR
    if os.path.exists(upload_dir):
        files = os.listdir(upload_dir)
        for f in files:
            path = os.path.join(upload_dir, f)
            if os.path.isfile(path):
                assert os.path.getsize(path) != 500


def test_idempotency_same_key_same_request(setup_context):
    """Same key + same request returns the original submission (replay)."""
    db = SessionLocal()
    try:
        key = f"key_{uuid.uuid4().hex}"
        fingerprint = hashlib.sha256(b"content_1").hexdigest()

        # 1. Create first submission
        sub = SourceSubmission(
            institution_id=setup_context["institution_id"],
            programme_id=setup_context["programme_id"],
            academic_year=setup_context["academic_year"],
            submission_type="ANNUAL_ROSTER",
            submission_status="UPLOADED",
            original_filename="file1.csv",
            storage_key="uploads/mock1.dat",
            file_fingerprint=fingerprint,
            file_size_bytes=100,
            client_idempotency_key=key,
            uploaded_by_user_id=setup_context["user_id"],
        )
        db.add(sub)
        db.commit()

        # 2. Replay with identical key and parameters
        is_replay, existing = IdempotencyService.evaluate_submission_request(
            db=db,
            institution_id=setup_context["institution_id"],
            programme_id=setup_context["programme_id"],
            academic_year=setup_context["academic_year"],
            submission_type="ANNUAL_ROSTER",
            file_fingerprint=fingerprint,
            client_idempotency_key=key,
        )

        assert is_replay is True
        assert existing is not None
        assert existing.id == sub.id
    finally:
        db.close()


def test_idempotency_same_key_different_content_raises_409(setup_context):
    """Same key + different content or context returns 409 Conflict."""
    db = SessionLocal()
    try:
        key = f"key_{uuid.uuid4().hex}"
        fp1 = hashlib.sha256(b"content_original").hexdigest()
        fp2 = hashlib.sha256(b"content_different").hexdigest()

        sub = SourceSubmission(
            institution_id=setup_context["institution_id"],
            programme_id=setup_context["programme_id"],
            academic_year=setup_context["academic_year"],
            submission_type="ANNUAL_ROSTER",
            submission_status="UPLOADED",
            original_filename="file1.csv",
            storage_key="uploads/mock2.dat",
            file_fingerprint=fp1,
            file_size_bytes=100,
            client_idempotency_key=key,
            uploaded_by_user_id=setup_context["user_id"],
        )
        db.add(sub)
        db.commit()

        # Evaluate with same key but different fingerprint
        with pytest.raises(IdempotencyConflictError):
            IdempotencyService.evaluate_submission_request(
                db=db,
                institution_id=setup_context["institution_id"],
                programme_id=setup_context["programme_id"],
                academic_year=setup_context["academic_year"],
                submission_type="ANNUAL_ROSTER",
                file_fingerprint=fp2,
                client_idempotency_key=key,
            )
    finally:
        db.close()


def test_idempotency_replay_failed_or_cancelled_submission(setup_context):
    """A failed or cancelled submission replayed with original key returns original result."""
    db = SessionLocal()
    try:
        key = f"key_{uuid.uuid4().hex}"
        fp = hashlib.sha256(b"failed_content").hexdigest()

        sub = SourceSubmission(
            institution_id=setup_context["institution_id"],
            programme_id=setup_context["programme_id"],
            academic_year=setup_context["academic_year"],
            submission_type="ANNUAL_ROSTER",
            submission_status="FAILED",
            failure_reason="Simulated parser failure",
            original_filename="failed.csv",
            storage_key="uploads/mock_failed.dat",
            file_fingerprint=fp,
            file_size_bytes=100,
            client_idempotency_key=key,
            uploaded_by_user_id=setup_context["user_id"],
        )
        db.add(sub)
        db.commit()

        is_replay, existing = IdempotencyService.evaluate_submission_request(
            db=db,
            institution_id=setup_context["institution_id"],
            programme_id=setup_context["programme_id"],
            academic_year=setup_context["academic_year"],
            submission_type="ANNUAL_ROSTER",
            file_fingerprint=fp,
            client_idempotency_key=key,
        )

        assert is_replay is True
        assert existing.submission_status == "FAILED"
    finally:
        db.close()


def test_retry_after_failure_with_new_key_succeeds(setup_context):
    """Retrying after failure with a new Idempotency-Key is permitted."""
    db = SessionLocal()
    try:
        old_key = f"key_{uuid.uuid4().hex}"
        new_key = f"key_{uuid.uuid4().hex}"
        fp = hashlib.sha256(b"retry_content").hexdigest()

        # Failed submission
        sub_failed = SourceSubmission(
            institution_id=setup_context["institution_id"],
            programme_id=setup_context["programme_id"],
            academic_year=setup_context["academic_year"],
            submission_type="ANNUAL_ROSTER",
            submission_status="FAILED",
            failure_reason="Corrupt header",
            original_filename="retry.csv",
            storage_key="uploads/mock_retry.dat",
            file_fingerprint=fp,
            file_size_bytes=100,
            client_idempotency_key=old_key,
            uploaded_by_user_id=setup_context["user_id"],
        )
        db.add(sub_failed)
        db.commit()

        # Retry with new key evaluates cleanly
        is_replay, existing = IdempotencyService.evaluate_submission_request(
            db=db,
            institution_id=setup_context["institution_id"],
            programme_id=setup_context["programme_id"],
            academic_year=setup_context["academic_year"],
            submission_type="ANNUAL_ROSTER",
            file_fingerprint=fp,
            client_idempotency_key=new_key,
        )

        assert is_replay is False
        assert existing is None

        # Insert new retry submission
        sub_retry = SourceSubmission(
            institution_id=setup_context["institution_id"],
            programme_id=setup_context["programme_id"],
            academic_year=setup_context["academic_year"],
            submission_type="ANNUAL_ROSTER",
            submission_status="UPLOADED",
            original_filename="retry.csv",
            storage_key="uploads/mock_retry_new.dat",
            file_fingerprint=fp,
            file_size_bytes=100,
            client_idempotency_key=new_key,
            uploaded_by_user_id=setup_context["user_id"],
        )
        db.add(sub_retry)
        db.commit()
        assert sub_retry.id != sub_failed.id
    finally:
        db.close()


def test_contextual_deduplication_active_or_committed(setup_context):
    """Active/committed duplicates in same context rejected; different context permitted."""
    db = SessionLocal()
    try:
        fp = hashlib.sha256(b"committed_content").hexdigest()
        sub = SourceSubmission(
            institution_id=setup_context["institution_id"],
            programme_id=setup_context["programme_id"],
            academic_year=setup_context["academic_year"],
            submission_type="ANNUAL_ROSTER",
            submission_status="COMMITTED",
            original_filename="committed.csv",
            storage_key="uploads/mock_comm.dat",
            file_fingerprint=fp,
            file_size_bytes=100,
            uploaded_by_user_id=setup_context["user_id"],
        )
        db.add(sub)
        db.commit()

        # 1. Same context rejected
        with pytest.raises(ContextualDuplicateError):
            IdempotencyService.evaluate_submission_request(
                db=db,
                institution_id=setup_context["institution_id"],
                programme_id=setup_context["programme_id"],
                academic_year=setup_context["academic_year"],
                submission_type="ANNUAL_ROSTER",
                file_fingerprint=fp,
            )

        # 2. Different academic year permitted
        is_replay, existing = IdempotencyService.evaluate_submission_request(
            db=db,
            institution_id=setup_context["institution_id"],
            programme_id=setup_context["programme_id"],
            academic_year="2025-26",
            submission_type="ANNUAL_ROSTER",
            file_fingerprint=fp,
        )
        assert is_replay is False
    finally:
        db.close()


def test_preview_integrity_and_partial_unique_index(setup_context):
    """Safeguard 1: At most one active preview per submission, versions preserved."""
    db = SessionLocal()
    try:
        fp = hashlib.sha256(b"preview_file").hexdigest()
        sub = SourceSubmission(
            institution_id=setup_context["institution_id"],
            programme_id=setup_context["programme_id"],
            academic_year=setup_context["academic_year"],
            submission_type="ANNUAL_ROSTER",
            submission_status="PREVIEW_READY",
            original_filename="preview.csv",
            storage_key="uploads/mock_prev.dat",
            file_fingerprint=fp,
            file_size_bytes=100,
            uploaded_by_user_id=setup_context["user_id"],
        )
        db.add(sub)
        db.commit()

        # 1. Create Preview 1
        prev1 = SubmissionPreview(
            submission_id=sub.id,
            file_fingerprint=fp,
            column_mapping={"roll": "student_id"},
            mapping_version="v1.0",
            mapping_hash="hash_1",
            parser_version="openpyxl-v3.1.2/csv-std",
            validation_rules_version="rules-v2026.1",
            normalization_version="norm-v1.0",
            is_active=True,
        )
        db.add(prev1)
        db.commit()

        # 2. Attempting second active preview violates partial unique index
        prev2_bad = SubmissionPreview(
            submission_id=sub.id,
            file_fingerprint=fp,
            column_mapping={"roll": "student_id", "name": "full_name"},
            mapping_version="v1.1",
            mapping_hash="hash_2",
            is_active=True,
        )
        db.add(prev2_bad)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

        # 3. Deactivating Preview 1 allows Preview 2 to be active (preserving version history)
        db.execute(
            text("UPDATE submission_previews SET is_active = FALSE WHERE id = :id"),
            {"id": prev1.id},
        )
        db.commit()

        prev2_good = SubmissionPreview(
            submission_id=sub.id,
            file_fingerprint=fp,
            column_mapping={"roll": "student_id", "name": "full_name"},
            mapping_version="v1.1",
            mapping_hash="hash_2",
            is_active=True,
        )
        db.add(prev2_good)
        db.commit()

        # Both previews exist in ledger
        total_previews = db.execute(
            select(SubmissionPreview).where(SubmissionPreview.submission_id == sub.id)
        ).scalars().all()
        assert len(total_previews) == 2
    finally:
        db.close()


def test_snapshot_lifecycle_and_authoritative_constraints(setup_context):
    """Verify chk_authoritative_lifecycle and idx_uq_authoritative_snapshot."""
    db = SessionLocal()
    try:
        fp = hashlib.sha256(b"snap_file").hexdigest()
        sub = SourceSubmission(
            institution_id=setup_context["institution_id"],
            programme_id=setup_context["programme_id"],
            academic_year=setup_context["academic_year"],
            submission_type="ANNUAL_ROSTER",
            submission_status="COMMITTED",
            original_filename="snap.csv",
            storage_key="uploads/mock_snap.dat",
            file_fingerprint=fp,
            file_size_bytes=100,
            uploaded_by_user_id=setup_context["user_id"],
        )
        db.add(sub)
        db.commit()

        # 1. Inconsistent state: authoritative=TRUE and lifecycle='SUPERSEDED' rejected by CHECK constraint
        snap_bad = RosterSnapshot(
            institution_id=setup_context["institution_id"],
            programme_id=setup_context["programme_id"],
            academic_year=setup_context["academic_year"],
            source_submission_id=sub.id,
            is_authoritative=True,
            lifecycle_status="SUPERSEDED",
            snapshot_hash="hash_bad",
            created_by_user_id=setup_context["user_id"],
        )
        db.add(snap_bad)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

        # 2. Authoritative snapshot 1
        snap1 = RosterSnapshot(
            institution_id=setup_context["institution_id"],
            programme_id=setup_context["programme_id"],
            academic_year=setup_context["academic_year"],
            source_submission_id=sub.id,
            is_authoritative=True,
            lifecycle_status="ACTIVE",
            snapshot_hash="hash_snap1",
            created_by_user_id=setup_context["user_id"],
        )
        db.add(snap1)
        db.commit()

        # 3. Two authoritative snapshots for same context rejected by partial unique index
        snap2_bad = RosterSnapshot(
            institution_id=setup_context["institution_id"],
            programme_id=setup_context["programme_id"],
            academic_year=setup_context["academic_year"],
            source_submission_id=sub.id,
            is_authoritative=True,
            lifecycle_status="ACTIVE",
            snapshot_hash="hash_snap2",
            created_by_user_id=setup_context["user_id"],
        )
        db.add(snap2_bad)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
    finally:
        db.close()


def test_annual_observation_composite_context_integrity(setup_context):
    """Verify observation cannot reference submission from another context or invalid record."""
    db = SessionLocal()
    try:
        # Create student identity
        ident = StudentIdentity(
            full_name="Context Test Student",
            identity_status="FORMAT_VALID",
        )
        db.add(ident)
        db.commit()

        # Create valid submission for 2024-25
        fp = hashlib.sha256(b"context_file").hexdigest()
        sub = SourceSubmission(
            institution_id=setup_context["institution_id"],
            programme_id=setup_context["programme_id"],
            academic_year="2024-25",
            submission_type="ANNUAL_ROSTER",
            submission_status="COMMITTED",
            original_filename="context.csv",
            storage_key="uploads/mock_context.dat",
            file_fingerprint=fp,
            file_size_bytes=100,
            uploaded_by_user_id=setup_context["user_id"],
        )
        db.add(sub)
        db.commit()

        # Create record in sub
        rec = SourceSubmissionRecord(
            submission_id=sub.id,
            row_number=1,
            raw_payload={"roll": "CSE-1"},
            parsed_payload={"student_id": "CSE-1"},
            validation_status="VALID",
        )
        db.add(rec)
        db.commit()

        # Valid observation: matches context and record
        obs_good = AnnualRosterObservation(
            student_identity_id=ident.id,
            institution_id=setup_context["institution_id"],
            programme_id=setup_context["programme_id"],
            academic_year="2024-25",
            student_status="ACTIVE",
            source_submission_id=sub.id,
            source_record_id=rec.id,
        )
        db.add(obs_good)
        db.commit()

        # Invalid observation: academic_year "2025-26" does not match submission's "2024-25"
        obs_bad_year = AnnualRosterObservation(
            student_identity_id=ident.id,
            institution_id=setup_context["institution_id"],
            programme_id=setup_context["programme_id"],
            academic_year="2025-26",
            student_status="ACTIVE",
            source_submission_id=sub.id,
            source_record_id=rec.id,
        )
        db.add(obs_bad_year)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
    finally:
        db.close()

