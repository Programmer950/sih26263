"""Reconciliation Service for Immutable Execution, Run Fingerprinting, and Discrepancy Case Lineage."""

import uuid
import json
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, desc, text
from fastapi import HTTPException, status

from app.models import (
    User,
    Institution,
    Programme,
    RosterSnapshot,
    StudentIdentity,
    AnnualRosterObservation,
    SourceSubmission,
    ReconciliationRun,
    ReconciliationResultItem,
    DiscrepancyCase,
    DiscrepancyCaseDecision,
    AuditEvent,
)
from app.services.comparison_service import ComparisonService
from app.services.snapshot_service import SnapshotService
from app.schemas.snapshot import SnapshotComparisonResponse
from app.schemas.reconciliation import (
    ReconciliationRunCreateRequest,
    ReconciliationRunResponse,
)

logger = logging.getLogger("apaar_setu.reconciliation")

ENGINE_VERSION = "v1.0"
RULES_VERSION = "v1.0-rules-apaar-setu"

# Case creation eligibility and severity mapping
CASE_POLICY = {
    "UNEXPLAINED_APPEARANCE": {"eligible": True, "priority": "HIGH"},
    "UNEXPLAINED_DISAPPEARANCE": {"eligible": True, "priority": "HIGH"},
    "AMBIGUOUS_IDENTITY": {"eligible": True, "priority": "MEDIUM"},
    "INSUFFICIENT_EVIDENCE": {"eligible": True, "priority": "LOW"},
    "CONTINUING": {"eligible": False, "priority": "NONE"},
    "ADDED": {"eligible": False, "priority": "NONE"},
    "WITHDRAWN": {"eligible": False, "priority": "NONE"},
    "DOCUMENTED_TRANSFER": {"eligible": False, "priority": "NONE"},
}


class ReconciliationService:
    """
    Manages immutable reconciliation runs, student-level result persistence,
    case creation policies, equivalence linking, and request idempotency.
    """

    @classmethod
    def execute_run(
        cls,
        db: Session,
        req: ReconciliationRunCreateRequest,
        actor: User,
        idempotency_key: Optional[str] = None,
    ) -> ReconciliationRun:
        """
        Executes a formal reconciliation run:
        1. Validates candidate snapshot and permissions.
        2. Enforces request idempotency if Idempotency-Key header is provided.
        3. Executes deterministic comparison via ComparisonService.
        4. Computes immutable run fingerprint.
        5. Persists all 8 result classifications.
        6. Links or creates discrepancy cases according to case-creation policy.
        7. Logs cryptographically chained AuditEvent.
        """
        # 1. Fetch and validate candidate snapshot
        candidate = db.get(RosterSnapshot, req.candidate_snapshot_id)
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate snapshot {req.candidate_snapshot_id} not found.",
            )

        # Tenant isolation
        if actor.role.role_name == "INSTITUTION_ADMIN" and candidate.institution_id != actor.institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenancy Violation: Access to candidate snapshot for external institution forbidden.",
            )

        # 2. Idempotency Check with transaction-scoped serialization
        if idempotency_key:
            # Advisory lock serializes concurrent execution on the same idempotency key for this institution
            lock_key = f"recon_run_idem:{candidate.institution_id}:{idempotency_key}"
            db.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
                {"lock_key": lock_key},
            )
            existing_run = db.execute(
                select(ReconciliationRun).where(
                    ReconciliationRun.institution_id == candidate.institution_id,
                    ReconciliationRun.idempotency_key == idempotency_key,
                )
            ).scalar_one_or_none()

            if existing_run:
                # Compare parameters
                stored_params = existing_run.parameters_json or {}
                incoming_cand = str(req.candidate_snapshot_id)
                incoming_base = str(req.baseline_snapshot_id) if req.baseline_snapshot_id else None
                incoming_type = req.run_type

                stored_cand = stored_params.get("candidate_snapshot_id")
                stored_req_base = stored_params.get("requested_baseline_snapshot_id")
                stored_base = stored_params.get("baseline_snapshot_id")
                stored_type = stored_params.get("run_type")

                cand_match = stored_cand == incoming_cand
                type_match = stored_type == incoming_type
                base_match = (
                    (stored_req_base == incoming_base)
                    or (stored_base == incoming_base)
                    or (incoming_base is None and stored_req_base is None)
                )

                if cand_match and type_match and base_match:
                    logger.info(f"Idempotent replay detected for key {idempotency_key}. Returning existing run {existing_run.id}")
                    return existing_run
                else:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Idempotency Conflict: A reconciliation run already exists with this Idempotency-Key but different parameters.",
                    )

        # 3. Execute comparison engine
        comparison: SnapshotComparisonResponse = ComparisonService.compare_snapshots(
            db=db,
            candidate_id=candidate.id,
            current_user=actor,
            baseline_id=req.baseline_snapshot_id,
        )

        baseline = None
        if comparison.baseline_snapshot_id:
            baseline = db.get(RosterSnapshot, comparison.baseline_snapshot_id)

        # 4. Compute deterministic result fingerprint
        fingerprint_tokens = []
        for r in comparison.records:
            c_obs = r.provenance.get("candidate_observation_id") or ""
            b_obs = r.provenance.get("baseline_observation_id") or ""
            fingerprint_tokens.append(f"{r.internal_student_uuid}:{r.classification}:{c_obs}:{b_obs}")
        fingerprint_str = ";".join(sorted(fingerprint_tokens))
        result_fingerprint = hashlib.sha256(fingerprint_str.encode("utf-8")).hexdigest()

        # 5. Create immutable ReconciliationRun record
        params_payload = {
            "candidate_snapshot_id": str(candidate.id),
            "requested_baseline_snapshot_id": str(req.baseline_snapshot_id) if req.baseline_snapshot_id else None,
            "baseline_snapshot_id": str(baseline.id) if baseline else None,
            "run_type": req.run_type,
            "parameters": req.parameters or {},
        }

        now_utc = datetime.now(timezone.utc)
        run = ReconciliationRun(
            institution_id=candidate.institution_id,
            programme_id=candidate.programme_id,
            academic_year=candidate.academic_year,
            candidate_snapshot_id=candidate.id,
            candidate_snapshot_hash=candidate.snapshot_hash,
            baseline_snapshot_id=baseline.id if baseline else None,
            baseline_snapshot_hash=baseline.snapshot_hash if baseline else None,
            run_type=req.run_type,
            execution_status="COMPLETED",
            engine_version=ENGINE_VERSION,
            rules_version=RULES_VERSION,
            result_fingerprint=result_fingerprint,
            summary_counts=comparison.summary_metrics,
            parameters_json=params_payload,
            idempotency_key=idempotency_key,
            initiated_by_user_id=actor.id,
            created_at=now_utc,
        )
        db.add(run)
        db.flush()

        # 6. Persist individual student result items and manage case lineage
        cases_created_count = 0

        for rec in comparison.records:
            policy = CASE_POLICY.get(rec.classification, {"eligible": False, "priority": "NONE"})
            is_case_eligible = policy["eligible"]
            priority = policy["priority"]

            cand_obs_id = uuid.UUID(rec.provenance["candidate_observation_id"]) if rec.provenance.get("candidate_observation_id") else None
            base_obs_id = uuid.UUID(rec.provenance["baseline_observation_id"]) if rec.provenance.get("baseline_observation_id") else None
            cand_sub_id = uuid.UUID(rec.provenance["candidate_submission_id"]) if rec.provenance.get("candidate_submission_id") else None
            base_sub_id = uuid.UUID(rec.provenance["baseline_submission_id"]) if rec.provenance.get("baseline_submission_id") else None

            # Create Result Item
            item = ReconciliationResultItem(
                reconciliation_run_id=run.id,
                institution_id=candidate.institution_id,
                programme_id=candidate.programme_id,
                academic_year=candidate.academic_year,
                student_identity_id=rec.student_identity_id,
                candidate_observation_id=cand_obs_id,
                candidate_submission_id=cand_sub_id,
                candidate_row_number=rec.source_row_candidate,
                baseline_observation_id=base_obs_id,
                baseline_submission_id=base_sub_id,
                baseline_row_number=rec.source_row_baseline,
                classification=rec.classification,
                review_priority=priority,
                system_explanation=rec.explanation,
                rules_version=RULES_VERSION,
                is_case_eligible=is_case_eligible,
                created_at=now_utc,
            )
            db.add(item)
            db.flush()

            # Case Lineage: Only create or link cases for eligible categories
            if is_case_eligible:
                case = cls._link_or_create_discrepancy_case(
                    db=db,
                    run=run,
                    result_item=item,
                    candidate=candidate,
                    now_utc=now_utc,
                )
                item.discrepancy_case_id = case.id
                if case.occurrence_count == 1:
                    cases_created_count += 1

        # Update run summary counts with cases created
        run.summary_counts["CASES_CREATED"] = cases_created_count
        db.flush()

        # 7. Hash-chained AuditEvent
        SnapshotService.record_chained_audit_event(
            db=db,
            actor_id=actor.id,
            action="RECONCILIATION_RUN_EXECUTED",
            entity_type="RECONCILIATION_RUN",
            entity_id=run.id,
            metadata_payload={
                "candidate_snapshot_id": str(candidate.id),
                "baseline_snapshot_id": str(baseline.id) if baseline else None,
                "result_fingerprint": result_fingerprint,
                "total_records": comparison.summary_metrics.get("TOTAL_RECORDS", len(comparison.records)),
                "cases_created": cases_created_count,
            },
        )

        db.commit()
        db.refresh(run)
        return run

    @classmethod
    def _link_or_create_discrepancy_case(
        cls,
        db: Session,
        run: ReconciliationRun,
        result_item: ReconciliationResultItem,
        candidate: RosterSnapshot,
        now_utc: datetime,
    ) -> DiscrepancyCase:
        """
        Manages case lineage:
        - If an active open case exists for this student and classification, links to it.
        - If no open case exists, opens a new case and links to any prior resolved case.
        """
        active_case = db.execute(
            select(DiscrepancyCase).where(
                DiscrepancyCase.institution_id == candidate.institution_id,
                DiscrepancyCase.programme_id == candidate.programme_id,
                DiscrepancyCase.student_identity_id == result_item.student_identity_id,
                DiscrepancyCase.classification == result_item.classification,
                DiscrepancyCase.case_status.not_in(["CLOSED", "VERIFIED_VALID"]),
            ).with_for_update()
        ).scalars().first()

        if active_case:
            active_case.latest_reconciliation_run_id = run.id
            active_case.occurrence_count += 1
            active_case.updated_at = now_utc
            db.flush()
            return active_case

        # Find prior closed case if any (for lineage link)
        prior_closed_case = db.execute(
            select(DiscrepancyCase).where(
                DiscrepancyCase.institution_id == candidate.institution_id,
                DiscrepancyCase.programme_id == candidate.programme_id,
                DiscrepancyCase.student_identity_id == result_item.student_identity_id,
                DiscrepancyCase.classification == result_item.classification,
                DiscrepancyCase.case_status.in_(["CLOSED", "VERIFIED_VALID"]),
            ).order_by(desc(DiscrepancyCase.created_at))
        ).scalars().first()

        # Generate unique case number
        case_uid = uuid.uuid4().hex[:8].upper()
        case_num = f"CASE-{candidate.academic_year}-{case_uid}"

        new_case = DiscrepancyCase(
            case_number=case_num,
            institution_id=candidate.institution_id,
            programme_id=candidate.programme_id,
            academic_year=candidate.academic_year,
            student_identity_id=result_item.student_identity_id,
            initial_reconciliation_run_id=run.id,
            latest_reconciliation_run_id=run.id,
            linked_prior_case_id=prior_closed_case.id if prior_closed_case else None,
            classification=result_item.classification,
            review_priority=result_item.review_priority,
            case_status="OPEN",
            occurrence_count=1,
            created_at=now_utc,
            updated_at=now_utc,
        )
        db.add(new_case)
        db.flush()
        return new_case
