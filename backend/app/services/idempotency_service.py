"""Idempotency Service for Safe Tenant-Scoped Submission Deduplication."""

import uuid
from typing import Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from app.models.source_submission import SourceSubmission


class IdempotencyConflictError(Exception):
    """Raised when an Idempotency-Key is reused with conflicting parameters or file content."""
    pass


class ContextualDuplicateError(Exception):
    """Raised when an identical file is submitted for an active or committed context."""
    pass


class IdempotencyService:
    """
    Implements tenant-scoped request idempotency and contextual file deduplication.
    Enforces atomic database-backed replay rules and duplicate prevention.
    """

    @classmethod
    def evaluate_submission_request(
        cls,
        db: Session,
        institution_id: uuid.UUID,
        programme_id: uuid.UUID,
        academic_year: str,
        submission_type: str,
        file_fingerprint: str,
        client_idempotency_key: Optional[str] = None,
    ) -> Tuple[bool, Optional[SourceSubmission]]:
        """
        Evaluates incoming request parameters and file fingerprint against database records.

        Returns:
            Tuple of (is_replay: bool, existing_submission: Optional[SourceSubmission])
            - If (True, existing_sub): Caller should return existing result (idempotent replay).
            - If (False, None): Caller proceeds to persist new submission.

        Raises:
            IdempotencyConflictError: If same key was used with different payload/context (HTTP 409).
            ContextualDuplicateError: If duplicate file is submitted in an active/committed context (HTTP 409).
        """
        # 1. Evaluate Client Idempotency Key
        if client_idempotency_key:
            existing = db.execute(
                select(SourceSubmission).where(
                    and_(
                        SourceSubmission.institution_id == institution_id,
                        SourceSubmission.client_idempotency_key == client_idempotency_key,
                    )
                )
            ).scalars().first()

            if existing:
                # Check for identical replay
                is_identical = (
                    existing.programme_id == programme_id
                    and existing.academic_year == academic_year
                    and existing.submission_type == submission_type
                    and existing.file_fingerprint == file_fingerprint
                )

                if is_identical:
                    # Same key + same request: return original submission (even if FAILED or CANCELLED)
                    return True, existing
                else:
                    # Same key + different request: strict 409 Conflict
                    raise IdempotencyConflictError(
                        "Idempotency key has already been used with differing submission parameters or file content."
                    )

        # 2. Evaluate Active/Committed Contextual Deduplication
        active_duplicate = db.execute(
            select(SourceSubmission).where(
                and_(
                    SourceSubmission.institution_id == institution_id,
                    SourceSubmission.programme_id == programme_id,
                    SourceSubmission.academic_year == academic_year,
                    SourceSubmission.submission_type == submission_type,
                    SourceSubmission.file_fingerprint == file_fingerprint,
                    SourceSubmission.submission_status.notin_(["FAILED", "CANCELLED"]),
                )
            )
        ).scalars().first()

        if active_duplicate:
            raise ContextualDuplicateError(
                f"An active or committed submission ({active_duplicate.submission_status}) with identical "
                "file fingerprint already exists for this institution, programme, and academic year."
            )

        # Retrying after FAILED or CANCELLED with a new or omitted key is permitted
        return False, None

