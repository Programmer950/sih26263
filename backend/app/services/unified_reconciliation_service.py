"""Unified Multi-Engine Reconciliation Service.

Coordinates Longitudinal Cohort Reconciliation, Statutory Intake Matrix Verification,
and Cross-Institution Duplicate Detection under a unified context without merging
or muting independent findings.
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, or_
from fastapi import HTTPException, status

from app.models import (
    User,
    RosterSnapshot,
    ApprovalConfiguration,
    ReconciliationRun,
    DiscrepancyCase,
    AuditEvent,
)
from app.schemas.reconciliation import ReconciliationRunCreateRequest
from app.schemas.approval import IntakeReconciliationRequest
from app.schemas.unified_reconciliation import (
    UnifiedReconciliationRequest,
    UnifiedReconciliationResponse,
    UnifiedCohortSummary,
    UnifiedIntakeSummary,
    DuplicateConflictItem,
)
from app.services.reconciliation_service import ReconciliationService, ENGINE_VERSION, RULES_VERSION
from app.services.intake_service import IntakeService
from app.services.duplicate_service import DuplicateService
from app.services.snapshot_service import SnapshotService

logger = logging.getLogger("apaar_setu.unified_reconciliation")


class UnifiedReconciliationService:
    """
    Unified Orchestrator:
    1. Resolves and freezes shared source context (snapshot, institution, programme, academic year).
    2. Executes Longitudinal Cohort Reconciliation.
    3. Executes Statutory Intake Verification.
    4. Executes Cross-Institution Duplicate Detection.
    5. Preserves independent result sets, rule versions, and discrepancy cases.
    """

    @classmethod
    def execute_unified(
        cls,
        db: Session,
        req: UnifiedReconciliationRequest,
        actor: User,
    ) -> UnifiedReconciliationResponse:
        """
        Executes unified reconciliation pipeline.
        """
        # 1. Fetch Candidate Snapshot
        candidate = db.get(RosterSnapshot, req.snapshot_id)
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate snapshot {req.snapshot_id} not found.",
            )

        # 2. Tenancy Isolation
        if actor.role.role_name == "INSTITUTION_ADMIN" and candidate.institution_id != actor.institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenancy Violation: Access to candidate snapshot for external institution forbidden.",
            )

        # 3. Stage 1: Longitudinal Cohort Reconciliation
        recon_req = ReconciliationRunCreateRequest(
            candidate_snapshot_id=candidate.id,
            baseline_snapshot_id=req.baseline_snapshot_id,
            run_type="UNIFIED_CROSS_ENGINE",
        )
        recon_run = ReconciliationService.execute_run(
            db=db,
            req=recon_req,
            actor=actor,
        )

        counts = recon_run.summary_counts or {}
        # Candidate-side populations
        cand_continuing = counts.get("CONTINUING", 0)
        cand_added = counts.get("ADDED", 0)
        cand_transfer = counts.get("DOCUMENTED_TRANSFER", 0)
        cand_unexplained_app = counts.get("UNEXPLAINED_APPEARANCE", 0)
        cand_ambiguous = counts.get("AMBIGUOUS_IDENTITY", 0)
        cand_insufficient = counts.get("INSUFFICIENT_EVIDENCE", 0)
        total_cand = cand_continuing + cand_added + cand_transfer + cand_unexplained_app + cand_ambiguous + cand_insufficient

        # Baseline departures (reported separately)
        baseline_disappearances = {
            "WITHDRAWN": counts.get("WITHDRAWN", 0),
            "UNEXPLAINED_DISAPPEARANCE": counts.get("UNEXPLAINED_DISAPPEARANCE", 0),
        }

        cohort_summary = UnifiedCohortSummary(
            reconciliation_run_id=recon_run.id,
            candidate_snapshot_id=candidate.id,
            baseline_snapshot_id=recon_run.baseline_snapshot_id,
            total_candidate_observations=total_cand,
            continuing_count=cand_continuing,
            added_count=cand_added,
            documented_transfer_count=cand_transfer,
            unexplained_appearance_count=cand_unexplained_app,
            ambiguous_identity_count=cand_ambiguous,
            insufficient_evidence_count=cand_insufficient,
            baseline_disappearances=baseline_disappearances,
            engine_version=recon_run.engine_version or ENGINE_VERSION,
            rules_version=recon_run.rules_version or RULES_VERSION,
            run_status=recon_run.execution_status,
        )

        # 4. Stage 2: Statutory Intake Reconciliation
        intake_summary: Optional[UnifiedIntakeSummary] = None
        try:
            intake_req = IntakeReconciliationRequest(
                candidate_snapshot_id=candidate.id,
                approval_configuration_id=req.approval_config_id,
            )
            intake_res = IntakeService.verify_intake_for_snapshot(
                db=db,
                req=intake_req,
                actor=actor,
            )
            intake_summary = UnifiedIntakeSummary(
                intake_summary_id=intake_res.id,
                approval_configuration_id=intake_res.approval_configuration_id,
                approval_configuration_version=intake_res.approval_configuration_version,
                approved_intake=intake_res.regular_approved_intake,
                enrolled_count=intake_res.regular_enrolled_count,
                variance=intake_res.regular_variance,
                compliance_status=intake_res.compliance_status,
                category_results=[cat.model_dump() for cat in intake_res.category_breakdown],
                engine_version="v1-regulatory-intake-engine",
                rules_version="2024.1-aicte-aph",
            )
        except HTTPException as he:
            if he.status_code == status.HTTP_404_NOT_FOUND:
                logger.info(f"No active approval configuration for snapshot {candidate.id}; intake marked INSUFFICIENT_INFORMATION")
                intake_summary = UnifiedIntakeSummary(
                    approved_intake=0,
                    enrolled_count=candidate.observed_headcount,
                    variance=0,
                    compliance_status="INSUFFICIENT_INFORMATION",
                    category_results=[],
                    engine_version="v1-regulatory-intake-engine",
                    rules_version="2024.1-aicte-aph",
                )
            else:
                raise

        # 5. Stage 3: Cross-Institution Duplicate Detection
        duplicate_candidates = DuplicateService.detect_duplicates(
            db=db,
            actor=actor,
            candidate_snapshot_id=candidate.id,
            academic_year=candidate.academic_year,
            institution_id=candidate.institution_id,
        )

        # 6. Gather created discrepancy cases for this run
        cases = db.execute(
            select(DiscrepancyCase).where(
                or_(
                    DiscrepancyCase.initial_reconciliation_run_id == recon_run.id,
                    DiscrepancyCase.latest_reconciliation_run_id == recon_run.id,
                )
            )
        ).scalars().all()
        cases_data = [
            {
                "case_id": str(c.id),
                "case_number": c.case_number,
                "scope_type": c.scope_type,
                "classification": c.classification,
                "review_priority": c.review_priority,
                "status": c.case_status,
            }
            for c in cases
        ]

        now_utc = datetime.now(timezone.utc)
        return UnifiedReconciliationResponse(
            reconciliation_run_id=recon_run.id,
            snapshot_id=candidate.id,
            institution_id=candidate.institution_id,
            programme_id=candidate.programme_id,
            academic_year=candidate.academic_year,
            status="COMPLETED",
            cohort_summary=cohort_summary,
            intake_summary=intake_summary,
            duplicate_candidates=duplicate_candidates,
            discrepancy_cases_created=cases_data,
            executed_at=now_utc,
        )
