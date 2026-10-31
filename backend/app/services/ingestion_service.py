"""Ingestion Service for Atomic Transactional Confirmation and Provenance Management."""

import os
import json
import uuid
import hashlib
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, func, text
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

from app.core.database import SessionLocal
from app.core.security import encrypt_sensitive_field
from app.models import (
    User,
    SourceSubmission,
    SubmissionPreview,
    SourceSubmissionRecord,
    StudentIdentity,
    InstitutionStudentRecord,
    AnnualRosterObservation,
    RosterSnapshot,
    AuditEvent,
)
from app.services.storage_service import StorageService
from app.services.parser_service import ParserService, ParsedFileResult
from app.services.preview_service import PreviewService
from app.services.identity_service import validate_apaar_format
from app.services.snapshot_service import SnapshotService
from app.schemas.submission import ConfirmRequest, ConfirmResponse

logger = logging.getLogger("apaar_setu.ingestion")


class IngestionService:
    """
    Executes atomic transactional ingestion of validated roster submissions into
    canonical student repository entities with dual-composite provenance and failure rollback.
    """

    ALLOWED_FAILURE_SOURCE_STATES = ("PREVIEW_READY", "INGESTING")

    @classmethod
    def confirm_and_ingest(
        cls,
        db: Session,
        submission_id: uuid.UUID,
        current_user: User,
        confirm_req: ConfirmRequest,
    ) -> ConfirmResponse:
        """
        Operation C: Atomic Ingestion Workflow.
        Enforces row-locking, preview version binding, revalidation,
        canonical identity resolution, and dual-transaction failure handling.
        """
        user_role = current_user.role.role_name

        # 1. Acquire Database Row Lock using SELECT ... FOR UPDATE
        submission = db.execute(
            select(SourceSubmission)
            .where(SourceSubmission.id == submission_id)
            .with_for_update()
        ).scalar_one_or_none()

        if not submission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Submission not found.",
            )

        # 2. Tenancy Isolation Check
        if user_role == "INSTITUTION_ADMIN" and submission.institution_id != current_user.institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenancy Violation: Access to submission for external institution forbidden.",
            )

        # 3. Verify Submission State Eligibility
        if submission.submission_status == "COMMITTED":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Submission has already been committed.",
            )
        if submission.submission_status == "CANCELLED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot confirm a cancelled submission.",
            )
        if submission.submission_status == "FAILED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot confirm a failed submission.",
            )
        if submission.submission_status != "PREVIEW_READY":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot confirm submission in status '{submission.submission_status}'. Expected 'PREVIEW_READY'.",
            )

        # 4. Preview Version Binding Validation
        preview = db.execute(
            select(SubmissionPreview).where(SubmissionPreview.id == confirm_req.preview_id)
        ).scalar_one_or_none()

        if not preview:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Requested preview version was not found.",
            )
        if preview.submission_id != submission.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Mismatched preview: requested preview does not belong to this submission.",
            )
        if not preview.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Stale preview: requested preview version is no longer active.",
            )
        if preview.file_fingerprint != submission.file_fingerprint:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Integrity violation: preview file fingerprint does not match parent submission.",
            )

        # 5. Engine Processing Versions & Historical Compatibility Verification
        if preview.parser_version not in ParserService.SUPPORTED_PARSER_VERSIONS:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Unsupported parser version '{preview.parser_version}'. "
                    f"Supported versions: {sorted(list(ParserService.SUPPORTED_PARSER_VERSIONS))}. "
                    "Original parser implementation is unavailable; preview must be regenerated."
                ),
            )

        if preview.validation_rules_version not in PreviewService.SUPPORTED_VALIDATION_RULES_VERSIONS:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Unsupported validation rules version '{preview.validation_rules_version}'. "
                    f"Supported versions: {sorted(list(PreviewService.SUPPORTED_VALIDATION_RULES_VERSIONS))}. "
                    "Original validation rules implementation is unavailable; preview must be regenerated."
                ),
            )

        if preview.normalization_version not in PreviewService.SUPPORTED_NORMALIZATION_VERSIONS:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Unsupported normalization version '{preview.normalization_version}'. "
                    f"Supported versions: {sorted(list(PreviewService.SUPPORTED_NORMALIZATION_VERSIONS))}. "
                    "Original normalization implementation is unavailable; preview must be regenerated."
                ),
            )

        if preview.mapping_version not in PreviewService.SUPPORTED_MAPPING_VERSIONS:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Unsupported mapping version '{preview.mapping_version}'. "
                    f"Supported versions: {sorted(list(PreviewService.SUPPORTED_MAPPING_VERSIONS))}. "
                    "Preview must be regenerated."
                ),
            )

        # 6. Authoritative Mapping Verification: Prevent frontend mapping substitution
        persisted_mapping = preview.column_mapping
        persisted_canonical = json.dumps(persisted_mapping, sort_keys=True)
        persisted_mapping_hash = hashlib.sha256(persisted_canonical.encode("utf-8")).hexdigest()

        if persisted_mapping_hash != preview.mapping_hash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Preview mapping integrity compromised: stored mapping hash mismatch.",
            )

        confirmed_canonical = json.dumps(confirm_req.column_mapping, sort_keys=True)
        if confirmed_canonical != persisted_canonical:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Stale or mismatched preview version. Attempted mapping substitution: confirmed mapping does not match authoritative preview mapping.",
            )

        authoritative_mapping = persisted_mapping

        # 7. Verify Original Stored File Evidence on Disk
        resolved_path = StorageService.resolve_safe_path(submission.storage_key)
        if not os.path.exists(resolved_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Raw submission evidence file is missing from storage.",
            )

        # Compute file fingerprint afresh to guarantee zero tampering
        file_hasher = hashlib.sha256()
        with open(resolved_path, "rb") as f:
            while chunk := f.read(65536):
                file_hasher.update(chunk)
        if file_hasher.hexdigest() != submission.file_fingerprint:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="File integrity compromised: stored file fingerprint does not match submission record.",
            )

        # 8. Revalidate Stored File Afresh
        try:
            parsed_result: ParsedFileResult = ParserService.parse_file(
                resolved_path,
                mime_type=submission.mime_type,
                filename=submission.original_filename,
            )
        except Exception as parse_err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Revalidation of original file failed: {str(parse_err)}",
            )

        # 9. Transaction A: Atomic Ingestion
        id_col = authoritative_mapping.get("student_id")
        name_col = authoritative_mapping.get("full_name")
        apaar_col = authoritative_mapping.get("apaar_id")
        status_col = authoritative_mapping.get("student_status")

        seen_student_ids = set()
        observed_student_uuids: List[uuid.UUID] = []
        records_processed = 0
        valid_records = 0
        warning_records = 0
        error_records = 0

        try:
            for row in parsed_result.rows:
                records_processed += 1
                row_status, row_errors, row_warnings = PreviewService.validate_row(
                    row_number=row.row_number,
                    raw_payload=row.raw_payload,
                    column_mapping=authoritative_mapping,
                    seen_student_ids=seen_student_ids,
                )

                if row_status == "VALID":
                    valid_records += 1
                elif row_status == "WARNING":
                    warning_records += 1
                elif row_status == "DUPLICATE":
                    warning_records += 1
                elif row_status == "INVALID":
                    error_records += 1

                # 8a. Create SourceSubmissionRecord (Raw payloads unmutated; formula metadata recorded)
                source_rec = SourceSubmissionRecord(
                    submission_id=submission.id,
                    row_number=row.row_number,
                    raw_payload=row.raw_payload,  # Verbatim cell values preserved without apostrophes
                    parsed_payload=row.parsed_payload,
                    formula_metadata=row.formula_metadata,
                    validation_status=row_status,
                    errors=row_errors,
                    warnings=row_warnings,
                    mapping_version=preview.mapping_version,
                )
                db.add(source_rec)
                db.flush()  # Assign source_rec.id

                # Extract field values safely
                raw_id = row.raw_payload.get(id_col) if id_col else None
                roll_no = str(raw_id).strip() if raw_id is not None else ""

                raw_nm = row.raw_payload.get(name_col) if name_col else None
                full_name = str(raw_nm).strip() if raw_nm is not None else ""

                raw_ap = row.raw_payload.get(apaar_col) if apaar_col else None
                raw_apaar = str(raw_ap).strip() if raw_ap is not None else ""

                raw_st = row.raw_payload.get(status_col) if status_col else None
                student_status = (str(raw_st).strip() if raw_st is not None else "") or "ACTIVE"

                # 8b. Identity Resolution
                apaar_status, clean_apaar, masked_apaar, blind_idx = validate_apaar_format(raw_apaar)
                identity: Optional[StudentIdentity] = None

                if apaar_status == "FORMAT_VALID" and blind_idx:
                    # Look up existing canonical identity by HMAC blind index
                    identity = db.execute(
                        select(StudentIdentity).where(StudentIdentity.apaar_blind_index == blind_idx)
                    ).scalar_one_or_none()

                    if identity is None:
                        # Attempt insert with savepoint to handle concurrent race on blind index safely
                        savepoint = db.begin_nested()
                        try:
                            encrypted_apaar = encrypt_sensitive_field(clean_apaar)
                            identity = StudentIdentity(
                                internal_student_uuid=uuid.uuid4(),
                                encrypted_apaar_reference=encrypted_apaar,
                                masked_apaar_reference=masked_apaar,
                                apaar_blind_index=blind_idx,
                                full_name=full_name or f"Student {roll_no}",
                                identity_status="FORMAT_VALID",
                            )
                            db.add(identity)
                            db.flush()
                            savepoint.commit()
                        except IntegrityError:
                            savepoint.rollback()
                            # Concurrent transaction inserted this identity: fetch the existing record
                            identity = db.execute(
                                select(StudentIdentity).where(StudentIdentity.apaar_blind_index == blind_idx)
                            ).scalar_one()
                else:
                    # MISSING_APAAR or INVALID_FORMAT: Weak attributes NEVER merge identities
                    # Create discrete provisional student identity
                    identity = StudentIdentity(
                        internal_student_uuid=uuid.uuid4(),
                        encrypted_apaar_reference=None,
                        masked_apaar_reference=masked_apaar,
                        apaar_blind_index=None,
                        full_name=full_name or f"Student {roll_no}",
                        identity_status=apaar_status,
                    )
                    db.add(identity)
                    db.flush()

                # Link resolved identity to source record
                source_rec.resolved_student_identity_id = identity.id
                observed_student_uuids.append(identity.internal_student_uuid)

                # 8c. Bind InstitutionStudentRecord
                inst_student_id = roll_no if roll_no else f"ROW-{row.row_number}"
                inst_record = db.execute(
                    select(InstitutionStudentRecord).where(
                        InstitutionStudentRecord.institution_id == submission.institution_id,
                        InstitutionStudentRecord.institution_student_id == inst_student_id,
                    )
                ).scalar_one_or_none()

                if inst_record is None:
                    savepoint_inst = db.begin_nested()
                    try:
                        inst_record = InstitutionStudentRecord(
                            student_identity_id=identity.id,
                            institution_id=submission.institution_id,
                            institution_student_id=inst_student_id,
                            programme_id=submission.programme_id,
                            status="ENROLLED",
                        )
                        db.add(inst_record)
                        db.flush()
                        savepoint_inst.commit()
                    except IntegrityError:
                        savepoint_inst.rollback()
                        inst_record = db.execute(
                            select(InstitutionStudentRecord).where(
                                InstitutionStudentRecord.institution_id == submission.institution_id,
                                InstitutionStudentRecord.institution_student_id == inst_student_id,
                            )
                        ).scalar_one()

                source_rec.resolved_institution_student_record_id = inst_record.id
                source_rec.processed_at = datetime.now(timezone.utc)

                # 8d. Append AnnualRosterObservation with Dual Composite Foreign Keys
                obs = AnnualRosterObservation(
                    student_identity_id=identity.id,
                    institution_id=submission.institution_id,
                    programme_id=submission.programme_id,
                    academic_year=submission.academic_year,
                    student_status=student_status,
                    source_submission_id=submission.id,
                    source_record_id=source_rec.id,
                    observation_metadata={
                        "source_row": row.row_number,
                        "mapping_version": preview.mapping_version,
                        "mapping_hash": preview.mapping_hash,
                        "raw_identifier": roll_no,
                        "apaar_status": apaar_status,
                        "formula_count": len(row.formula_metadata),
                    },
                )
                db.add(obs)
                db.flush()

            # 8e. Compute Canonical Snapshot Hash
            sorted_uuids = sorted(str(u) for u in observed_student_uuids)
            snapshot_hash = hashlib.sha256(",".join(sorted_uuids).encode("utf-8")).hexdigest()

            # 8f. Create Candidate Roster Snapshot
            snapshot = RosterSnapshot(
                institution_id=submission.institution_id,
                programme_id=submission.programme_id,
                academic_year=submission.academic_year,
                source_submission_id=submission.id,
                completeness_status=confirm_req.completeness_status,
                lifecycle_status="ACTIVE",
                is_authoritative=False,  # Initial state; promoted via SnapshotService if requested
                declared_headcount=records_processed,
                observed_headcount=len(observed_student_uuids),
                snapshot_canonicalization_version="v1-sha256-sorted-uuids",
                snapshot_hash=snapshot_hash,
                snapshot_metadata={
                    "confirmed_by_user_id": str(current_user.id),
                    "mapping_version": preview.mapping_version,
                    "mapping_hash": preview.mapping_hash,
                    "total_records_processed": records_processed,
                },
                created_by_user_id=current_user.id,
            )
            db.add(snapshot)
            db.flush()

            # Delegate authoritative promotion to shared SnapshotService
            if confirm_req.mark_as_authoritative:
                SnapshotService.execute_authoritative_promotion_core(
                    db=db,
                    target_snapshot=snapshot,
                    actor=current_user,
                    reason="Authoritative promotion upon ingestion confirmation",
                )

            # 8g. Chained SHA-256 Audit Event
            prev_event = db.execute(
                select(AuditEvent).order_by(AuditEvent.timestamp.desc())
            ).scalars().first()
            prev_hash = prev_event.event_hash if prev_event else "0" * 64
            event_timestamp = datetime.now(timezone.utc)
            event_hash = hashlib.sha256(
                f"{prev_hash}:CONFIRM_INGESTION:SOURCE_SUBMISSION:{submission.id}:{event_timestamp.isoformat()}".encode("utf-8")
            ).hexdigest()

            audit_entry = AuditEvent(
                actor_id=current_user.id,
                action="CONFIRM_INGESTION",
                entity_type="SOURCE_SUBMISSION",
                entity_id=submission.id,
                metadata_payload={
                    "preview_id": str(preview.id),
                    "snapshot_id": str(snapshot.id),
                    "records_processed": records_processed,
                    "valid_records": valid_records,
                    "warning_records": warning_records,
                    "error_records": error_records,
                    "is_authoritative": snapshot.is_authoritative,
                },
                previous_event_hash=prev_hash,
                event_hash=event_hash,
                timestamp=event_timestamp,
            )
            db.add(audit_entry)

            # 8h. Finalize Submission State
            committed_at = datetime.now(timezone.utc)
            submission.submission_status = "COMMITTED"
            submission.committed_at = committed_at
            submission.total_rows_count = records_processed
            submission.valid_rows_count = valid_records
            submission.warning_rows_count = warning_records
            submission.error_rows_count = error_records

            # Commit Transaction A atomically
            db.commit()
            db.refresh(submission)

            return ConfirmResponse(
                submission_id=submission.id,
                submission_status="COMMITTED",
                snapshot_id=snapshot.id,
                total_records_processed=records_processed,
                valid_records=valid_records,
                warning_records=warning_records,
                error_records=error_records,
                snapshot_status=snapshot.lifecycle_status,
                completeness_status=snapshot.completeness_status,
                is_authoritative=snapshot.is_authoritative,
                committed_at=committed_at,
            )

        except Exception as exc:
            # Dual-Transaction Failure Pattern: Roll back Transaction A
            logger.error(f"Ingestion transaction failed for submission {submission_id}: {exc}", exc_info=True)
            db.rollback()

            # Transaction B: Conditional database-level update in isolated session
            sanitized_reason = f"Ingestion error: {str(exc)[:500]}"
            try:
                with SessionLocal() as fail_session:
                    result = fail_session.execute(
                        text("""
                            UPDATE source_submissions
                            SET submission_status = 'FAILED',
                                failure_reason = :failure_reason,
                                updated_at = NOW()
                            WHERE id = :submission_id
                              AND submission_status IN ('PREVIEW_READY', 'INGESTING')
                        """),
                        {
                            "submission_id": submission_id,
                            "failure_reason": sanitized_reason,
                        },
                    )
                    fail_session.commit()
                    if result.rowcount == 0:
                        logger.warning(
                            f"Skipped FAILED transition for submission {submission_id}: "
                            f"State is not in allowed predecessor states {cls.ALLOWED_FAILURE_SOURCE_STATES}."
                        )
                    else:
                        logger.info(
                            f"Recorded FAILED status for submission {submission_id} (rows affected: {result.rowcount})"
                        )
            except Exception as fail_session_err:
                logger.error(f"Failed to record FAILED status in isolated session: {fail_session_err}")

            if isinstance(exc, HTTPException):
                raise exc

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Transactional ingestion failed: {str(exc)}",
            )
