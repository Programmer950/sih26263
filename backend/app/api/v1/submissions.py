"""Submissions API Controller for Roster Upload, Safe Preview, and Lifecycle Control."""

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Form,
    Header,
    Query,
)
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc, and_
from typing import Optional, Dict, Any, List
import uuid
import math
from datetime import datetime, timezone
import logging

logger = logging.getLogger("apaar_setu.submissions")

from app.core.database import get_db
from app.core.permissions import get_current_user, TenantGuard
from app.models import (
    User,
    Programme,
    SourceSubmission,
    SubmissionPreview,
)
from app.services.storage_service import (
    StorageService,
    FileSizeExceededError,
)
from app.services.parser_service import (
    ParserService,
    ArchiveSecurityError,
    InvalidArchiveError,
    ParserLimitExceededError,
)
from app.services.preview_service import PreviewService
from app.services.idempotency_service import (
    IdempotencyService,
    IdempotencyConflictError,
    ContextualDuplicateError,
)
from app.schemas.submission import (
    PreviewRequest,
    UploadResponse,
    PreviewResponse,
    CancelResponse,
    SubmissionSummary,
    PaginatedSubmissionsResponse,
    SubmissionDetailResponse,
    ConfirmRequest,
    ConfirmResponse,
)
from app.services.ingestion_service import IngestionService

router = APIRouter(prefix="/submissions", tags=["Submissions & Roster Ingestion"])


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
def upload_roster_file(
    file: UploadFile = File(...),
    programme_id: uuid.UUID = Form(...),
    academic_year: str = Form(...),
    submission_type: str = Form("ANNUAL_ROSTER"),
    institution_id: Optional[uuid.UUID] = Form(None),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Operation A: Secure File Upload, Pre-Flight Inspection & Initial Header Preview.
    - Enforces tenant isolation.
    - Streams file to isolated storage with 10MB limit and SHA-256 fingerprinting.
    - Enforces idempotency key rules and contextual file deduplication.
    - Performs pre-flight ZIP archive security inspection for XLSX.
    - Extracts headers and generates suggested column mappings.
    - Zero student repository mutations.
    """
    user_role = current_user.role.role_name

    # 1. Tenancy Enforcement
    if user_role == "INSTITUTION_ADMIN":
        if institution_id is not None and institution_id != current_user.institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenancy Violation: Institution Administrators cannot upload for external institutions.",
            )
        target_institution_id = current_user.institution_id
    elif user_role in ["REGULATORY_REVIEWER", "SYSTEM_ADMIN"]:
        target_institution_id = institution_id or current_user.institution_id
        if not target_institution_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="institution_id is mandatory for regulatory reviewer uploads.",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{user_role}' is not authorized to upload student rosters.",
        )

    # 2. Verify Programme belongs to target institution
    programme = db.execute(
        select(Programme).where(
            Programme.id == programme_id,
            Programme.institution_id == target_institution_id,
        )
    ).scalar_one_or_none()

    if not programme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Programme '{programme_id}' not found for target institution.",
        )

    # 3. Stream Upload to Isolated Storage
    storage_key = None
    try:
        storage_key, file_fingerprint, file_size, detected_mime = StorageService.save_upload_stream(
            stream=file.file,
            original_filename=file.filename or "uploaded_roster.dat",
        )
    except FileSizeExceededError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to save upload: {str(e)}")

    # 4. Idempotency & Contextual Deduplication Check
    try:
        is_replay, cached_submission = IdempotencyService.evaluate_submission_request(
            db=db,
            institution_id=target_institution_id,
            programme_id=programme_id,
            academic_year=academic_year,
            submission_type=submission_type,
            file_fingerprint=file_fingerprint,
            client_idempotency_key=idempotency_key,
        )
    except (IdempotencyConflictError, ContextualDuplicateError) as e:
        # Clean up newly written file on rejection
        if storage_key:
            StorageService.delete_file(storage_key)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    # If this is an identical idempotent replay, return the cached submission
    if is_replay and cached_submission:
        if storage_key:
            StorageService.delete_file(storage_key)
        val_summary = cached_submission.validation_summary or {}
        return UploadResponse(
            submission_id=cached_submission.id,
            submission_status=cached_submission.submission_status,
            file_fingerprint=cached_submission.file_fingerprint,
            original_filename=cached_submission.original_filename,
            file_size_bytes=cached_submission.file_size_bytes,
            detected_encoding=val_summary.get("detected_encoding"),
            total_rows_count=cached_submission.total_rows_count or 0,
            valid_rows_count=cached_submission.valid_rows_count or 0,
            warning_rows_count=cached_submission.warning_rows_count or 0,
            error_rows_count=cached_submission.error_rows_count or 0,
            duplicate_rows_count=cached_submission.duplicate_rows_count or 0,
            detected_headers=val_summary.get("headers", []),
            suggested_mapping=cached_submission.mapping_config or {},
            sample_rows=val_summary.get("sample_rows", []),
        )

    # 5. Pre-flight Parsing & Header Detection
    try:
        resolved_path = StorageService.resolve_safe_path(storage_key)
        parsed_result = ParserService.parse_file(
            resolved_path,
            mime_type=detected_mime or file.content_type,
            filename=file.filename,
            max_rows=50,
        )
    except (ArchiveSecurityError, InvalidArchiveError, ParserLimitExceededError) as e:
        StorageService.delete_file(storage_key)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        StorageService.delete_file(storage_key)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to parse file: {str(e)}")

    if not parsed_result.headers:
        StorageService.delete_file(storage_key)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file contains no readable headers or data rows.",
        )

    # 6. Header Autodetection & Suggested Column Mapping
    suggested_mapping = PreviewService.suggest_column_mapping(parsed_result.headers)

    # 7. Validate Initial Sample Rows
    seen_ids = set()
    sample_rows = []
    sample_valid = 0
    sample_warnings = 0
    sample_errors = 0
    sample_duplicates = 0

    for r in parsed_result.rows[:25]:
        status_str, r_errors, r_warnings = PreviewService.validate_row(
            row_number=r.row_number,
            raw_payload=r.raw_payload,
            column_mapping=suggested_mapping,
            seen_student_ids=seen_ids,
        )
        if status_str == "VALID":
            sample_valid += 1
        elif status_str == "WARNING":
            sample_warnings += 1
        elif status_str == "DUPLICATE":
            sample_duplicates += 1
            sample_warnings += 1
        elif status_str == "INVALID":
            sample_errors += 1

        sample_rows.append({
            "row_number": r.row_number,
            "raw_payload": r.raw_payload,
            "parsed_payload": r.parsed_payload,
            "validation_status": status_str,
            "errors": r_errors,
            "warnings": r_warnings,
        })

    # 8. Record in Submission Ledger
    submission = SourceSubmission(
        institution_id=target_institution_id,
        programme_id=programme_id,
        academic_year=academic_year,
        submission_type=submission_type,
        storage_key=storage_key,
        file_fingerprint=file_fingerprint,
        original_filename=file.filename or "uploaded_roster.dat",
        file_size_bytes=file_size,
        mime_type=detected_mime or file.content_type or "application/octet-stream",
        client_idempotency_key=idempotency_key,
        uploaded_by_user_id=current_user.id,
        submission_status="PREVIEW_READY",
        total_rows_count=parsed_result.total_rows_detected,
        valid_rows_count=sample_valid,
        warning_rows_count=sample_warnings,
        error_rows_count=sample_errors,
        duplicate_rows_count=sample_duplicates,
        mapping_config=suggested_mapping,
        validation_summary={
            "headers": parsed_result.headers,
            "detected_encoding": parsed_result.encoding,
            "parser_warnings": parsed_result.warnings,
            "sample_rows": sample_rows,
            "sample_metrics": {
                "valid": sample_valid,
                "warnings": sample_warnings,
                "errors": sample_errors,
                "duplicates": sample_duplicates,
            },
        },
    )

    commit_succeeded = False
    try:
        db.add(submission)
        db.commit()
        commit_succeeded = True
        try:
            db.refresh(submission)
        except Exception as refresh_err:
            logger.warning(
                f"Refresh failed for submission {submission.id} after successful commit: {refresh_err}. "
                "Retaining committed ledger record and file evidence."
            )
    except Exception as db_err:
        logger.error(
            f"Database failure during submission persistence for tenant {target_institution_id}: {db_err}",
            exc_info=True,
        )
        try:
            db.rollback()
        except Exception as rb_err:
            logger.error(f"Rollback failed: {rb_err}")

        # Handle uncertain commit outcomes: verify if a committed submission references the file
        should_delete = False
        if not commit_succeeded:
            try:
                existing_ref = db.execute(
                    select(SourceSubmission.id).where(SourceSubmission.storage_key == storage_key)
                ).scalar_one_or_none()
                if not existing_ref:
                    should_delete = True
                else:
                    logger.warning(
                        f"Uncertain commit: submission {existing_ref} exists for storage_key {storage_key}; retaining file."
                    )
            except Exception as check_err:
                logger.error(f"Failed to verify submission existence after commit failure: {check_err}")
                should_delete = False

        if should_delete and storage_key:
            try:
                StorageService.delete_file(storage_key)
            except Exception as cleanup_err:
                logger.error(f"Cleanup failure for orphaned file {storage_key}: {cleanup_err}", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred while creating the submission record. The upload was rolled back.",
        )

    return UploadResponse(
        submission_id=submission.id,
        submission_status=submission.submission_status,
        file_fingerprint=submission.file_fingerprint,
        original_filename=submission.original_filename,
        file_size_bytes=submission.file_size_bytes,
        detected_encoding=parsed_result.encoding,
        total_rows_count=submission.total_rows_count,
        valid_rows_count=sample_valid,
        warning_rows_count=sample_warnings,
        error_rows_count=sample_errors,
        duplicate_rows_count=sample_duplicates,
        detected_headers=parsed_result.headers,
        suggested_mapping=suggested_mapping,
        sample_rows=sample_rows,
    )


@router.post("/{submission_id}/preview", response_model=PreviewResponse)
def generate_column_mapping_preview(
    submission_id: uuid.UUID,
    body: PreviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Operation B: Full-File Mapping Preview & Version Binding.
    - Scans entire file against the user-confirmed column mapping.
    - Flags all formatting errors, missing fields, and duplicates beyond row 50.
    - Generates an immutable, hash-bound SubmissionPreview record.
    - Zero student repository mutations.
    """
    submission = db.execute(
        select(SourceSubmission).where(SourceSubmission.id == submission_id)
    ).scalar_one_or_none()

    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found.",
        )

    # Tenancy check
    user_role = current_user.role.role_name
    if user_role == "INSTITUTION_ADMIN" and submission.institution_id != current_user.institution_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenancy Violation: Access to submission for external institution forbidden.",
        )

    # State check: Only uncommitted submissions may have previews generated
    if submission.submission_status not in ["PREVIEW_READY", "UPLOADED"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot generate preview for submission with status '{submission.submission_status}'.",
        )

    # Generate persistent full preview
    try:
        preview, preview_data = PreviewService.generate_full_preview(
            db=db,
            submission=submission,
            column_mapping=body.column_mapping,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to generate full preview: {str(e)}",
        )

    return PreviewResponse(
        preview_id=preview.id,
        submission_id=submission.id,
        file_fingerprint=preview.file_fingerprint,
        mapping_version=preview.mapping_version,
        mapping_hash=preview.mapping_hash,
        detected_encoding=preview_data.get("detected_encoding"),
        total_rows_count=submission.total_rows_count,
        valid_rows_count=submission.valid_rows_count,
        warning_rows_count=submission.warning_rows_count,
        error_rows_count=submission.error_rows_count,
        duplicate_rows_count=submission.duplicate_rows_count,
        column_mapping=preview.column_mapping,
        validation_summary=preview.validation_summary,
        sample_rows=preview_data.get("sample_rows"),
        created_at=preview.created_at,
    )


@router.post("/{submission_id}/cancel", response_model=CancelResponse)
def cancel_submission(
    submission_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Cancels an uncommitted submission.
    - Evidence Retention: The uploaded raw file in storage is retained in accordance
      with the configured cancellation evidence retention policy (RETENTION_DAYS_CANCELLED).
    - Transitions submission state to CANCELLED.
    - Prevents any future confirmation.
    """
    submission = db.execute(
        select(SourceSubmission).where(SourceSubmission.id == submission_id)
    ).scalar_one_or_none()

    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found.",
        )

    # Tenancy check
    user_role = current_user.role.role_name
    if user_role == "INSTITUTION_ADMIN" and submission.institution_id != current_user.institution_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenancy Violation: Access to submission for external institution forbidden.",
        )

    if submission.submission_status in ["COMMITTED", "PROCESSING", "CANCELLED"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel submission in status '{submission.submission_status}'.",
        )

    submission.submission_status = "CANCELLED"
    submission.cancelled_at = datetime.now(timezone.utc)
    submission.cancelled_by_user_id = current_user.id
    db.commit()
    db.refresh(submission)

    return CancelResponse(
        submission_id=submission.id,
        submission_status="CANCELLED",
    )


@router.post("/{submission_id}/confirm", response_model=ConfirmResponse)
def confirm_submission(
    submission_id: uuid.UUID,
    body: ConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Operation C: Atomic Ingestion & Concurrency-Safe Provenance.
    - Locks row using SELECT ... FOR UPDATE.
    - Validates preview version binding and disk integrity.
    - Ingests raw source records and resolves identities.
    - Establishes annual observations with dual composite FKs.
    - Computes snapshot hash and handles authoritative transition.
    - Emits chained audit log and commits transaction atomically.
    """
    return IngestionService.confirm_and_ingest(
        db=db,
        submission_id=submission_id,
        current_user=current_user,
        confirm_req=body,
    )



@router.get("", response_model=PaginatedSubmissionsResponse)
def list_submissions(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    institution_id: Optional[uuid.UUID] = None,
    programme_id: Optional[uuid.UUID] = None,
    academic_year: Optional[str] = None,
    submission_type: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    tenant: TenantGuard = Depends(TenantGuard),
    db: Session = Depends(get_db),
):
    """
    Lists submissions with multi-tenant scoping and filters.
    """
    scoped_inst_id = tenant.scope_institution_id(institution_id)

    query = select(SourceSubmission)
    count_query = select(func.count()).select_from(SourceSubmission)

    conditions = []
    if scoped_inst_id:
        conditions.append(SourceSubmission.institution_id == scoped_inst_id)
    if programme_id:
        conditions.append(SourceSubmission.programme_id == programme_id)
    if academic_year:
        conditions.append(SourceSubmission.academic_year == academic_year)
    if submission_type:
        conditions.append(SourceSubmission.submission_type == submission_type)
    if status_filter:
        conditions.append(SourceSubmission.submission_status == status_filter)

    if conditions:
        query = query.where(and_(*conditions))
        count_query = count_query.where(and_(*conditions))

    total = db.execute(count_query).scalar() or 0
    pages = math.ceil(total / limit) if total > 0 else 1
    offset = (page - 1) * limit

    submissions = db.execute(
        query.order_by(desc(SourceSubmission.created_at)).offset(offset).limit(limit)
    ).scalars().all()

    items = [
        SubmissionSummary(
            id=s.id,
            institution_id=s.institution_id,
            programme_id=s.programme_id,
            academic_year=s.academic_year,
            submission_type=s.submission_type,
            original_filename=s.original_filename,
            file_fingerprint=s.file_fingerprint,
            file_size_bytes=s.file_size_bytes,
            submission_status=s.submission_status,
            total_rows_count=s.total_rows_count,
            valid_rows_count=s.valid_rows_count,
            warning_rows_count=s.warning_rows_count,
            error_rows_count=s.error_rows_count,
            duplicate_rows_count=s.duplicate_rows_count,
            created_at=s.created_at,
            committed_at=s.committed_at,
        )
        for s in submissions
    ]

    return PaginatedSubmissionsResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


@router.get("/{submission_id}", response_model=SubmissionDetailResponse)
def get_submission_detail(
    submission_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieves full details for a submission including mapping config,
    validation summary, and active preview version reference.
    """
    submission = db.execute(
        select(SourceSubmission).where(SourceSubmission.id == submission_id)
    ).scalar_one_or_none()

    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found.",
        )

    # Tenancy check
    user_role = current_user.role.role_name
    if user_role == "INSTITUTION_ADMIN" and submission.institution_id != current_user.institution_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenancy Violation: Access to submission for external institution forbidden.",
        )

    active_preview = db.execute(
        select(SubmissionPreview).where(
            SubmissionPreview.submission_id == submission.id,
            SubmissionPreview.is_active == True,
        )
    ).scalars().first()

    return SubmissionDetailResponse(
        id=submission.id,
        institution_id=submission.institution_id,
        programme_id=submission.programme_id,
        academic_year=submission.academic_year,
        submission_type=submission.submission_type,
        original_filename=submission.original_filename,
        file_fingerprint=submission.file_fingerprint,
        file_size_bytes=submission.file_size_bytes,
        submission_status=submission.submission_status,
        total_rows_count=submission.total_rows_count,
        valid_rows_count=submission.valid_rows_count,
        warning_rows_count=submission.warning_rows_count,
        error_rows_count=submission.error_rows_count,
        duplicate_rows_count=submission.duplicate_rows_count,
        mapping_config=submission.mapping_config,
        validation_summary=submission.validation_summary,
        failure_reason=submission.failure_reason,
        active_preview_id=active_preview.id if active_preview else None,
        created_at=submission.created_at,
        committed_at=submission.committed_at,
        cancelled_at=submission.cancelled_at,
    )
