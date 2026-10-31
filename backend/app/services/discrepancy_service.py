"""Discrepancy Service for Controlled Decision Transitions, Dossiers, and Immutable Audit Trails."""

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, desc
from fastapi import HTTPException, status

from app.models import (
    User,
    DiscrepancyCase,
    DiscrepancyCaseDecision,
    ReconciliationResultItem,
    StudentIdentity,
    AnnualRosterObservation,
    SourceSubmission,
    AuditEvent,
)
from app.services.snapshot_service import SnapshotService
from app.schemas.reconciliation import (
    CaseDecisionCreateRequest,
    DiscrepancyCaseDetail,
    DiscrepancyCaseDecisionItem,
)

logger = logging.getLogger("apaar_setu.discrepancies")

# Rigorous Status Transition Matrix
STATUS_TRANSITION_RULES = {
    "START_INVESTIGATION": {
        "from_states": ["OPEN"],
        "to_state": "UNDER_INVESTIGATION",
        "roles": ["REGULATORY_REVIEWER", "SYSTEM_ADMIN"],
    },
    "REQUEST_EVIDENCE": {
        "from_states": ["OPEN", "UNDER_INVESTIGATION", "EXPLANATION_SUBMITTED"],
        "to_state": "EVIDENCE_REQUESTED",
        "roles": ["REGULATORY_REVIEWER", "SYSTEM_ADMIN"],
    },
    "SUBMIT_EXPLANATION": {
        "from_states": ["EVIDENCE_REQUESTED", "OPEN", "UNDER_INVESTIGATION"],
        "to_state": "EXPLANATION_SUBMITTED",
        "roles": ["INSTITUTION_ADMIN"],
    },
    "CONFIRM_VALID": {
        "from_states": ["UNDER_INVESTIGATION", "EXPLANATION_SUBMITTED"],
        "to_state": "VERIFIED_VALID",
        "roles": ["REGULATORY_REVIEWER", "SYSTEM_ADMIN"],
    },
    "RECORD_CORRECTION": {
        "from_states": ["OPEN", "UNDER_INVESTIGATION", "EVIDENCE_REQUESTED", "EXPLANATION_SUBMITTED"],
        "to_state": "CORRECTION_SUBMITTED",
        "roles": ["INSTITUTION_ADMIN", "SYSTEM_ADMIN"],
    },
    "CLOSE_CASE": {
        "from_states": ["VERIFIED_VALID", "CORRECTION_SUBMITTED"],
        "to_state": "CLOSED",
        "roles": ["REGULATORY_REVIEWER", "SYSTEM_ADMIN"],
    },
    "REOPEN_CASE": {
        "from_states": ["CLOSED", "VERIFIED_VALID"],
        "to_state": "UNDER_INVESTIGATION",
        "roles": ["REGULATORY_REVIEWER", "SYSTEM_ADMIN"],
    },
}


class DiscrepancyService:
    """
    Manages discrepancy case lifecycle, status transitions, role permissions,
    mandatory reason validation, and append-only decision logging.
    """

    @classmethod
    def record_decision(
        cls,
        db: Session,
        case_id: uuid.UUID,
        req: CaseDecisionCreateRequest,
        actor: User,
    ) -> DiscrepancyCaseDecision:
        """
        Executes a controlled decision on an active discrepancy case:
        1. Validates case exists and tenant authorization.
        2. Validates action against STATUS_TRANSITION_RULES and actor's role.
        3. Validates mandatory reason (min length 10).
        4. Updates case status transactionally.
        5. Inserts append-only decision record.
        6. Emits cryptographically chained AuditEvent.
        """
        # Acquire row lock to serialize concurrent decision determinations on the same case
        case = db.execute(
            select(DiscrepancyCase).where(DiscrepancyCase.id == case_id).with_for_update()
        ).scalar_one_or_none()
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Discrepancy case {case_id} not found.",
            )

        # 1. Tenant Isolation
        actor_role = actor.role.role_name
        if actor_role == "INSTITUTION_ADMIN" and case.institution_id != actor.institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenancy Violation: Access to discrepancy case for external institution forbidden.",
            )

        # 2. Transition Rule Lookup
        rule = STATUS_TRANSITION_RULES.get(req.action)
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action '{req.action}'. Allowed actions: {list(STATUS_TRANSITION_RULES.keys())}",
            )

        # Check role permission for this action
        if actor_role not in rule["roles"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Action '{req.action}' is restricted to roles: {', '.join(rule['roles'])}. Current role: {actor_role}",
            )

        # Check current status is in allowed from_states
        if case.case_status not in rule["from_states"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Illegal State Transition: Action '{req.action}' cannot be applied from current status '{case.case_status}'. Allowed from states: {rule['from_states']}",
            )

        # 3. Mandatory Reason Validation
        clean_reason = req.mandatory_reason.strip()
        if len(clean_reason) < 10:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Mandatory regulatory justification must be at least 10 non-whitespace characters.",
            )

        # 4. State Update
        prev_status = case.case_status
        new_status = rule["to_state"]
        now_utc = datetime.now(timezone.utc)

        case.case_status = new_status
        case.updated_at = now_utc
        db.flush()

        # 5. Chained AuditEvent
        audit_entry = SnapshotService.record_chained_audit_event(
            db=db,
            actor_id=actor.id,
            action="DISCREPANCY_DECISION_RECORDED",
            entity_type="DISCREPANCY_CASE",
            entity_id=case.id,
            metadata_payload={
                "action": req.action,
                "from_status": prev_status,
                "to_status": new_status,
                "reason_length": len(clean_reason),
                "case_number": case.case_number,
            },
        )

        # 6. Insert Append-Only Decision Record
        decision = DiscrepancyCaseDecision(
            discrepancy_case_id=case.id,
            from_status=prev_status,
            to_status=new_status,
            action=req.action,
            mandatory_reason=clean_reason,
            evidence_references=req.evidence_references or {},
            decided_by_user_id=actor.id,
            audit_event_id=audit_entry.id,
            created_at=now_utc,
        )
        db.add(decision)
        db.commit()
        db.refresh(decision)

        return decision

    @classmethod
    def get_case_detail(
        cls,
        db: Session,
        case_id: uuid.UUID,
        actor: User,
    ) -> DiscrepancyCaseDetail:
        """
        Retrieves detailed discrepancy dossier with field-level role disclosure,
        evidence observations, and complete decision history.
        """
        case = db.get(DiscrepancyCase, case_id)
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Discrepancy case {case_id} not found.",
            )

        if actor.role.role_name == "INSTITUTION_ADMIN" and case.institution_id != actor.institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenancy Violation: Access to discrepancy case for external institution forbidden.",
            )

        student = db.get(StudentIdentity, case.student_identity_id)

        # Query latest result item for this case to fetch observation evidence
        result_item = db.execute(
            select(ReconciliationResultItem).where(
                ReconciliationResultItem.discrepancy_case_id == case.id
            ).order_by(desc(ReconciliationResultItem.created_at))
        ).scalars().first()

        cand_obs_data = None
        base_obs_data = None
        system_explanation = ""

        if result_item:
            system_explanation = result_item.system_explanation
            if result_item.candidate_observation_id:
                c_obs = db.get(AnnualRosterObservation, result_item.candidate_observation_id)
                if c_obs:
                    cand_obs_data = {
                        "observation_id": str(c_obs.id),
                        "student_status": c_obs.student_status,
                        "academic_year": c_obs.academic_year,
                        "row_number": result_item.candidate_row_number,
                        "observation_timestamp": c_obs.observation_timestamp.isoformat() if c_obs.observation_timestamp else None,
                    }
            if result_item.baseline_observation_id:
                b_obs = db.get(AnnualRosterObservation, result_item.baseline_observation_id)
                if b_obs:
                    base_obs_data = {
                        "observation_id": str(b_obs.id),
                        "student_status": b_obs.student_status,
                        "academic_year": b_obs.academic_year,
                        "row_number": result_item.baseline_row_number,
                        "observation_timestamp": b_obs.observation_timestamp.isoformat() if b_obs.observation_timestamp else None,
                    }

        # Query decisions in chronological order
        decisions_rows = db.execute(
            select(DiscrepancyCaseDecision, User)
            .join(User, DiscrepancyCaseDecision.decided_by_user_id == User.id)
            .where(DiscrepancyCaseDecision.discrepancy_case_id == case.id)
            .order_by(DiscrepancyCaseDecision.created_at.asc())
        ).all()

        decision_items = [
            DiscrepancyCaseDecisionItem(
                id=d.id,
                from_status=d.from_status,
                to_status=d.to_status,
                action=d.action,
                mandatory_reason=d.mandatory_reason,
                evidence_references=d.evidence_references or {},
                decided_by_user_id=d.decided_by_user_id,
                decided_by_name=u.name,
                created_at=d.created_at,
            )
            for d, u in decisions_rows
        ]

        return DiscrepancyCaseDetail(
            id=case.id,
            case_number=case.case_number,
            institution_id=case.institution_id,
            programme_id=case.programme_id,
            academic_year=case.academic_year,
            student_identity_id=case.student_identity_id,
            student_name=student.full_name if student else "Unknown",
            masked_apaar=student.masked_apaar_reference if student else None,
            classification=case.classification,
            review_priority=case.review_priority,
            case_status=case.case_status,
            occurrence_count=case.occurrence_count,
            system_explanation=system_explanation,
            initial_reconciliation_run_id=case.initial_reconciliation_run_id,
            latest_reconciliation_run_id=case.latest_reconciliation_run_id,
            linked_prior_case_id=case.linked_prior_case_id,
            candidate_observation=cand_obs_data,
            baseline_observation=base_obs_data,
            created_at=case.created_at,
            updated_at=case.updated_at,
            decisions=decision_items,
        )

