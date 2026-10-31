"""Snapshot Service for Authoritative Promotion, Lifecycle Management, and Advisory Locking."""

import uuid
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, text
from fastapi import HTTPException, status

from app.models import (
    User,
    RosterSnapshot,
    SourceSubmission,
    AuditEvent,
)
from app.schemas.snapshot import SnapshotPromoteResponse

logger = logging.getLogger("apaar_setu.snapshots")


class SnapshotService:
    """
    Manages roster snapshot lifecycle, serialization via PostgreSQL advisory locks,
    authoritative transitions, and cryptographic audit chaining.
    """

    @classmethod
    def record_chained_audit_event(
        cls,
        db: Session,
        actor_id: uuid.UUID,
        action: str,
        entity_type: str,
        entity_id: uuid.UUID,
        metadata_payload: dict,
    ) -> AuditEvent:
        """Appends a cryptographically hash-chained AuditEvent in the active transaction."""
        prev_event = db.execute(
            select(AuditEvent).order_by(AuditEvent.timestamp.desc())
        ).scalars().first()
        prev_hash = prev_event.event_hash if prev_event else "0" * 64
        event_timestamp = datetime.now(timezone.utc)
        event_hash = hashlib.sha256(
            f"{prev_hash}:{action}:{entity_type}:{entity_id}:{event_timestamp.isoformat()}".encode("utf-8")
        ).hexdigest()

        audit_entry = AuditEvent(
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata_payload=metadata_payload,
            previous_event_hash=prev_hash,
            event_hash=event_hash,
            timestamp=event_timestamp,
        )
        db.add(audit_entry)
        db.flush()
        return audit_entry

    @classmethod
    def execute_authoritative_promotion_core(
        cls,
        db: Session,
        target_snapshot: RosterSnapshot,
        actor: User,
        reason: Optional[str] = None,
    ) -> Tuple[List[RosterSnapshot], AuditEvent]:
        """
        Shared authoritative snapshot promotion core.
        Enforces:
        1. Context-scoped PostgreSQL advisory lock:
           Key = 'snap_' || institution_id || '_' || programme_id || '_' || academic_year
        2. Acquisition of row locks on existing authoritative snapshots.
        3. Atomic supersession of existing authoritative snapshots with reverse-pointers.
        4. Promotion of target candidate snapshot.
        5. Hash-chained AuditEvent emission for both demotion and promotion inside the same transaction.
        """
        # Context-scoped transaction advisory lock:
        context_lock_key = f"snap_{target_snapshot.institution_id}_{target_snapshot.programme_id}_{target_snapshot.academic_year}"
        db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:context_key, 0))"),
            {"context_key": context_lock_key},
        )

        now_utc = datetime.now(timezone.utc)

        # Look up existing authoritative snapshot(s) for this context
        existing_auths = db.execute(
            select(RosterSnapshot).where(
                RosterSnapshot.institution_id == target_snapshot.institution_id,
                RosterSnapshot.programme_id == target_snapshot.programme_id,
                RosterSnapshot.academic_year == target_snapshot.academic_year,
                RosterSnapshot.is_authoritative == True,
                RosterSnapshot.id != target_snapshot.id,
            ).with_for_update()
        ).scalars().all()

        for auth in existing_auths:
            auth.is_authoritative = False
            auth.lifecycle_status = "SUPERSEDED"
            auth.superseded_at = now_utc
            auth.superseded_by_snapshot_id = target_snapshot.id
            db.flush()

            # Chained Audit Event for superseded snapshot
            cls.record_chained_audit_event(
                db=db,
                actor_id=actor.id,
                action="SUPERSEDE_SNAPSHOT",
                entity_type="ROSTER_SNAPSHOT",
                entity_id=auth.id,
                metadata_payload={
                    "superseded_by_snapshot_id": str(target_snapshot.id),
                    "context": context_lock_key,
                    "reason": reason or "Superseded by new authoritative promotion",
                },
            )

        # Promote target snapshot
        target_snapshot.is_authoritative = True
        target_snapshot.lifecycle_status = "ACTIVE"
        db.flush()

        # Chained Audit Event for promoted snapshot
        promote_audit = cls.record_chained_audit_event(
            db=db,
            actor_id=actor.id,
            action="PROMOTE_SNAPSHOT",
            entity_type="ROSTER_SNAPSHOT",
            entity_id=target_snapshot.id,
            metadata_payload={
                "previous_authoritative_snapshot_ids": [str(a.id) for a in existing_auths],
                "context": context_lock_key,
                "reason": reason or "Promoted to authoritative",
            },
        )

        return existing_auths, promote_audit

    @classmethod
    def promote_snapshot(
        cls,
        db: Session,
        snapshot_id: uuid.UUID,
        actor: User,
        reason: Optional[str] = None,
    ) -> SnapshotPromoteResponse:
        """
        Operation: Standalone Authoritative Snapshot Promotion (POST /snapshots/{id}/promote).
        Enforces tenant authorization, eligibility checks, advisory locking, and atomic transition.
        """
        # 1. Acquire row lock on target snapshot
        snapshot = db.execute(
            select(RosterSnapshot).where(RosterSnapshot.id == snapshot_id).with_for_update()
        ).scalar_one_or_none()

        if not snapshot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Snapshot not found.",
            )

        # 2. Tenancy Isolation Enforcement
        actor_role = actor.role.role_name
        if actor_role == "INSTITUTION_ADMIN" and snapshot.institution_id != actor.institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenancy Violation: Access to snapshot for external institution forbidden.",
            )

        # 3. State & Eligibility Validation
        if snapshot.lifecycle_status == "SUPERSEDED":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot promote a superseded snapshot. Only active candidate snapshots may be promoted.",
            )
        if snapshot.is_authoritative is True:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Snapshot is already authoritative for this institution, programme, and academic year.",
            )

        # Verify source submission is committed
        submission = db.execute(
            select(SourceSubmission).where(SourceSubmission.id == snapshot.source_submission_id)
        ).scalar_one_or_none()

        if not submission or submission.submission_status != "COMMITTED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot promote snapshot: source submission {snapshot.source_submission_id} is not COMMITTED.",
            )

        # 4. Atomic Authoritative Transition with Advisory Locking
        existing_auths, audit_entry = cls.execute_authoritative_promotion_core(
            db=db,
            target_snapshot=snapshot,
            actor=actor,
            reason=reason,
        )

        db.commit()
        db.refresh(snapshot)

        superseded_id = existing_auths[0].id if existing_auths else None

        return SnapshotPromoteResponse(
            snapshot_id=snapshot.id,
            institution_id=snapshot.institution_id,
            programme_id=snapshot.programme_id,
            academic_year=snapshot.academic_year,
            is_authoritative=snapshot.is_authoritative,
            lifecycle_status=snapshot.lifecycle_status,
            superseded_snapshot_id=superseded_id,
            audit_event_id=audit_entry.id,
            promoted_at=datetime.now(timezone.utc),
        )

