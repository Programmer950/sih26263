"""Intake Reconciliation Verification Service.

Verifies reported student enrolment against institution- and programme-specific
AICTE approval configurations, category allocation matrices, and rounding policies.
"""

import uuid
import math
import logging
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, text
from fastapi import HTTPException, status

from app.models import (
    User,
    RosterSnapshot,
    AnnualRosterObservation,
    AdmissionEpisode,
    ApprovalConfiguration,
    ApprovalCategoryAllocation,
    ReconciliationRun,
    IntakeReconciliationSummary,
    DiscrepancyCase,
)
from app.schemas.approval import (
    IntakeReconciliationRequest,
    IntakeReconciliationSummaryResponse,
    CategoryComplianceResult,
)
from app.services.approval_service import ApprovalService, compute_seat_cap
from app.services.snapshot_service import SnapshotService

logger = logging.getLogger("apaar_setu.intake")

ENGINE_VERSION = "v1-regulatory-intake-engine"
RULES_VERSION = "2024.1-aicte-aph"


class IntakeService:
    """
    Intake Verification and Regulatory Approval Engine.
    Enforces multi-dimensional student classification, versioned rounding policies,
    segregated lateral entry accounting, anti-double-counting, and programme-level discrepancy tracking.
    """

    @classmethod
    def verify_intake_for_snapshot(
        cls,
        db: Session,
        req: IntakeReconciliationRequest,
        actor: User,
        idempotency_key: Optional[str] = None,
    ) -> IntakeReconciliationSummaryResponse:
        """
        Executes formal regulatory intake verification against statutory approval configuration:
        1. Validates candidate snapshot and institution tenancy.
        2. Retrieves active ApprovalConfiguration for programme and academic year.
        3. Classifies student cohort across distinct dimensions with anti-double-counting.
        4. Calculates regular intake, additive supernumerary, within-sanctioned, and lateral quotas.
        5. Evaluates compliance status according to strict precedence:
           EXCEPTION_FOUND > INSUFFICIENT_INFORMATION > PARTIALLY_EVALUATED > COMPLIANT.
        6. Spawns programme-level DiscrepancyCase records (nullable student_identity_id) for collective findings.
        7. Persists immutable IntakeReconciliationSummary and hash-chained AuditEvent.
        """
        # 1. Fetch Candidate Snapshot
        candidate = db.get(RosterSnapshot, req.candidate_snapshot_id)
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate snapshot {req.candidate_snapshot_id} not found.",
            )

        if actor.role.role_name == "INSTITUTION_ADMIN" and candidate.institution_id != actor.institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenancy Violation: Access to candidate snapshot for external institution forbidden.",
            )

        now_utc = datetime.now(timezone.utc)

        # 2. Fetch observations for candidate snapshot
        observations = db.execute(
            select(AnnualRosterObservation).where(
                AnnualRosterObservation.source_submission_id == candidate.source_submission_id
            )
        ).scalars().all()

        total_observed_headcount = len(observations)

        # Fetch AdmissionEpisode records for multi-dimensional classification
        student_ids = [obs.student_identity_id for obs in observations]
        episodes_map: Dict[uuid.UUID, AdmissionEpisode] = {}
        if student_ids:
            episodes = db.execute(
                select(AdmissionEpisode).where(
                    AdmissionEpisode.student_identity_id.in_(student_ids),
                    AdmissionEpisode.programme_id == candidate.programme_id,
                    AdmissionEpisode.academic_year == candidate.academic_year,
                )
            ).scalars().all()
            episodes_map = {ep.student_identity_id: ep for ep in episodes}

        # 3. Retrieve Active ApprovalConfiguration
        approval_config = ApprovalService.get_active_configuration(
            db=db,
            institution_id=candidate.institution_id,
            programme_id=candidate.programme_id,
            academic_year=candidate.academic_year,
        )

        # Scenario 7: Missing Approval Configuration
        if not approval_config:
            return cls._handle_missing_approval_configuration(
                db=db,
                candidate=candidate,
                observations=observations,
                actor=actor,
                now_utc=now_utc,
                idempotency_key=idempotency_key,
            )

        # 4. Multi-Dimensional Student Accounting & Anti-Double-Counting
        # Distinct Dimensions:
        # - nationality_category
        # - admission_channel
        # - seat_accounting_category
        # - entry_level
        # - applicable_approval_rule_id
        regular_students: List[uuid.UUID] = []
        within_sanctioned_students: Dict[str, List[uuid.UUID]] = {}
        supernumerary_students: Dict[str, List[uuid.UUID]] = {}
        lateral_entry_students: List[uuid.UUID] = []
        unclassified_students: List[uuid.UUID] = []

        seen_student_ids: set[uuid.UUID] = set()
        duplicate_records_count = 0

        for obs in observations:
            sid = obs.student_identity_id
            if sid in seen_student_ids:
                duplicate_records_count += 1
                continue
            seen_student_ids.add(sid)

            ep = episodes_map.get(sid)

            if ep:
                seat_cat = ep.seat_accounting_category
                entry_lvl = ep.entry_level
                rule_id = ep.applicable_approval_rule_id or "GENERAL"
            else:
                # Check metadata hints
                meta = obs.observation_metadata or {}
                seat_cat = meta.get("seat_accounting_category")
                entry_lvl = meta.get("entry_level", "FIRST_YEAR")
                rule_id = meta.get("applicable_approval_rule_id") or "GENERAL"

            # Anti-double-counting deterministic segregation:
            if entry_lvl == "LATERAL_ENTRY_SECOND_YEAR" or seat_cat == "LATERAL_ENTRY":
                lateral_entry_students.append(sid)
            elif seat_cat == "SUPERNUMERARY":
                supernumerary_students.setdefault(rule_id, []).append(sid)
            elif seat_cat == "WITHIN_SANCTIONED_SUB_QUOTA":
                within_sanctioned_students.setdefault(rule_id, []).append(sid)
            elif seat_cat == "REGULAR":
                regular_students.append(sid)
            else:
                # Indeterminate category: do not silently assign to REGULAR
                unclassified_students.append(sid)

        # Verify Summation Invariant:
        total_sub_quota = sum(len(ids) for ids in within_sanctioned_students.values())
        total_supernumerary = sum(len(ids) for ids in supernumerary_students.values())
        total_accounted = (
            len(regular_students)
            + total_sub_quota
            + total_supernumerary
            + len(lateral_entry_students)
            + len(unclassified_students)
        )
        assert total_accounted == len(seen_student_ids), "Cohort double-counting violation detected!"

        # 5. Evaluate Allocations and Compute Quotas
        regular_approved = approval_config.approved_intake
        # Total regular includes general merit + within-sanctioned carved-out sub-quotas
        total_regular_enrolled = len(regular_students) + total_sub_quota
        regular_variance = total_regular_enrolled - regular_approved

        exceptions_found = False
        insufficient_info = False
        partially_evaluated = False

        category_compliance_list: List[CategoryComplianceResult] = []
        discrepancy_cases_to_create: List[Dict[str, Any]] = []

        # 5a. Regular Sanctioned Intake Check
        if regular_variance > 0:
            exceptions_found = True
            category_compliance_list.append(
                CategoryComplianceResult(
                    category_code="REGULAR_INTAKE",
                    entry_level="FIRST_YEAR",
                    allocation_type="SANCTIONED_INTAKE",
                    approved_limit=regular_approved,
                    observed_count=total_regular_enrolled,
                    variance=regular_variance,
                    status="EXCEPTION_FOUND",
                    notes=f"Reported regular enrolment exceeds AICTE approved intake by {regular_variance} seats.",
                )
            )
            discrepancy_cases_to_create.append({
                "classification": "INTAKE_EXCESS_REGULAR",
                "priority": "HIGH",
                "approved_limit": regular_approved,
                "observed_count": total_regular_enrolled,
                "excess_count": regular_variance,
                "evidence": {
                    "category_code": "REGULAR_INTAKE",
                    "approved_intake": regular_approved,
                    "enrolled_count": total_regular_enrolled,
                    "excess_count": regular_variance,
                    "regular_general_count": len(regular_students),
                    "sub_quota_count": total_sub_quota,
                },
            })
        else:
            category_compliance_list.append(
                CategoryComplianceResult(
                    category_code="REGULAR_INTAKE",
                    entry_level="FIRST_YEAR",
                    allocation_type="SANCTIONED_INTAKE",
                    approved_limit=regular_approved,
                    observed_count=total_regular_enrolled,
                    variance=regular_variance,
                    status="COMPLIANT",
                )
            )

        # 5b. Evaluate Category Allocations (Sub-quotas & Supernumeraries)
        allocations: List[ApprovalCategoryAllocation] = approval_config.category_allocations or []
        supernumerary_total_cap = 0
        lateral_entry_cap: Optional[int] = None
        has_lateral_allocation = False

        for alloc in allocations:
            cat_code = alloc.category_code
            entry_lvl = alloc.entry_level
            alloc_type = alloc.allocation_type

            # Check denominator
            denom = None
            if alloc.denominator_basis == "SANCTIONED_INTAKE":
                denom = regular_approved
            elif alloc.denominator_basis == "ACTUAL_ENROLMENT":
                denom = total_regular_enrolled

            cap, calc_err = compute_seat_cap(
                basis=alloc.allocation_basis,
                allocated_value=float(alloc.allocated_value),
                rounding_method=alloc.rounding_method,
                denominator=denom,
            )

            # Scenario 4: Missing rounding policy or denominator unestablished
            if cap is None:
                insufficient_info = True
                category_compliance_list.append(
                    CategoryComplianceResult(
                        category_code=cat_code,
                        entry_level=entry_lvl,
                        allocation_type=alloc_type,
                        approved_limit=None,
                        observed_count=0,
                        variance=None,
                        status="INSUFFICIENT_INFORMATION",
                        notes=calc_err or "Calculation method or rounding policy incomplete.",
                    )
                )
                discrepancy_cases_to_create.append({
                    "classification": "INDETERMINATE_POLICY_CONFIGURATION",
                    "priority": "LOW",
                    "approved_limit": None,
                    "observed_count": 0,
                    "excess_count": None,
                    "evidence": {
                        "category_code": cat_code,
                        "allocated_value": float(alloc.allocated_value),
                        "rounding_method": alloc.rounding_method,
                        "reason": calc_err,
                    },
                })
                continue

            if entry_lvl == "LATERAL_ENTRY_SECOND_YEAR" or cat_code == "LATERAL_ENTRY":
                has_lateral_allocation = True
                lateral_entry_cap = cap
                continue

            if alloc_type == "ADDITIONAL_SUPERNUMERARY":
                supernumerary_total_cap += cap
                observed_in_cat = len(supernumerary_students.get(cat_code, []))
                var = observed_in_cat - cap
                if var > 0:
                    exceptions_found = True
                    status_str = "EXCEPTION_FOUND"
                    discrepancy_cases_to_create.append({
                        "classification": "SUPERNUMERARY_QUOTA_BREACH",
                        "priority": "HIGH",
                        "approved_limit": cap,
                        "observed_count": observed_in_cat,
                        "excess_count": var,
                        "evidence": {
                            "category_code": cat_code,
                            "allocation_type": alloc_type,
                            "cap": cap,
                            "observed": observed_in_cat,
                            "excess": var,
                        },
                    })
                else:
                    status_str = "COMPLIANT"

                category_compliance_list.append(
                    CategoryComplianceResult(
                        category_code=cat_code,
                        entry_level=entry_lvl,
                        allocation_type=alloc_type,
                        approved_limit=cap,
                        observed_count=observed_in_cat,
                        variance=var,
                        status=status_str,
                    )
                )

            elif alloc_type == "WITHIN_SANCTIONED_INTAKE":
                observed_in_cat = len(within_sanctioned_students.get(cat_code, []))
                var = observed_in_cat - cap
                if var > 0:
                    exceptions_found = True
                    status_str = "EXCEPTION_FOUND"
                    discrepancy_cases_to_create.append({
                        "classification": "CATEGORY_ALLOCATION_BREACH",
                        "priority": "MEDIUM",
                        "approved_limit": cap,
                        "observed_count": observed_in_cat,
                        "excess_count": var,
                        "evidence": {
                            "category_code": cat_code,
                            "allocation_type": alloc_type,
                            "cap": cap,
                            "observed": observed_in_cat,
                            "excess": var,
                        },
                    })
                else:
                    status_str = "COMPLIANT"

                category_compliance_list.append(
                    CategoryComplianceResult(
                        category_code=cat_code,
                        entry_level=entry_lvl,
                        allocation_type=alloc_type,
                        approved_limit=cap,
                        observed_count=observed_in_cat,
                        variance=var,
                        status=status_str,
                    )
                )

            elif alloc_type in ("INDEPENDENT_CAP", "INFORMATIONAL_ONLY"):
                observed_in_cat = len(supernumerary_students.get(cat_code, []))
                var = observed_in_cat - cap if alloc_type == "INDEPENDENT_CAP" else 0
                if alloc_type == "INDEPENDENT_CAP" and var > 0:
                    exceptions_found = True
                    status_str = "EXCEPTION_FOUND"
                    discrepancy_cases_to_create.append({
                        "classification": "INDEPENDENT_CAP_BREACH",
                        "priority": "HIGH",
                        "approved_limit": cap,
                        "observed_count": observed_in_cat,
                        "excess_count": var,
                        "evidence": {
                            "category_code": cat_code,
                            "cap": cap,
                            "observed": observed_in_cat,
                            "excess": var,
                        },
                    })
                else:
                    status_str = "COMPLIANT"

                category_compliance_list.append(
                    CategoryComplianceResult(
                        category_code=cat_code,
                        entry_level=entry_lvl,
                        allocation_type=alloc_type,
                        approved_limit=cap,
                        observed_count=observed_in_cat,
                        variance=var,
                        status=status_str,
                    )
                )

        # 5c. Lateral Entry Segregated Evaluation (Scenario 6)
        observed_lateral = len(lateral_entry_students)
        if not has_lateral_allocation:
            # Fallback to configuration default if specified
            if approval_config.lateral_entry_quota_percentage > 0:
                lateral_entry_cap = math.floor(
                    regular_approved * (float(approval_config.lateral_entry_quota_percentage) / 100.0)
                )
            else:
                lateral_entry_cap = 0

        lateral_variance = observed_lateral - lateral_entry_cap if lateral_entry_cap is not None else None
        if lateral_entry_cap is not None and lateral_variance is not None and lateral_variance > 0:
            exceptions_found = True
            category_compliance_list.append(
                CategoryComplianceResult(
                    category_code="LATERAL_ENTRY",
                    entry_level="LATERAL_ENTRY_SECOND_YEAR",
                    allocation_type="INDEPENDENT_CAP",
                    approved_limit=lateral_entry_cap,
                    observed_count=observed_lateral,
                    variance=lateral_variance,
                    status="EXCEPTION_FOUND",
                    notes=f"Reported lateral entry enrolment exceeds approved ceiling by {lateral_variance} seats.",
                )
            )
            discrepancy_cases_to_create.append({
                "classification": "LATERAL_ENTRY_INTAKE_EXCESS",
                "priority": "HIGH",
                "approved_limit": lateral_entry_cap,
                "observed_count": observed_lateral,
                "excess_count": lateral_variance,
                "evidence": {
                    "entry_level": "LATERAL_ENTRY_SECOND_YEAR",
                    "approved_cap": lateral_entry_cap,
                    "observed_lateral": observed_lateral,
                    "excess": lateral_variance,
                },
            })
        else:
            category_compliance_list.append(
                CategoryComplianceResult(
                    category_code="LATERAL_ENTRY",
                    entry_level="LATERAL_ENTRY_SECOND_YEAR",
                    allocation_type="INDEPENDENT_CAP",
                    approved_limit=lateral_entry_cap,
                    observed_count=observed_lateral,
                    variance=lateral_variance,
                    status="COMPLIANT",
                )
            )

        # 5d. Unclassified records (Scenario 5 & Scenario 8)
        if len(unclassified_students) > 0:
            partially_evaluated = True
            category_compliance_list.append(
                CategoryComplianceResult(
                    category_code="UNCLASSIFIED_SEAT_CATEGORY",
                    entry_level="FIRST_YEAR",
                    allocation_type="INFORMATIONAL_ONLY",
                    approved_limit=None,
                    observed_count=len(unclassified_students),
                    variance=None,
                    status="PARTIALLY_EVALUATED",
                    notes=f"{len(unclassified_students)} student records lack deterministic seat accounting evidence.",
                )
            )
            discrepancy_cases_to_create.append({
                "classification": "UNCLASSIFIED_SEAT_CATEGORY",
                "priority": "LOW",
                "approved_limit": None,
                "observed_count": len(unclassified_students),
                "excess_count": None,
                "evidence": {
                    "unclassified_student_ids": [str(sid) for sid in unclassified_students],
                    "count": len(unclassified_students),
                },
            })

        # 6. Compliance Status Aggregation Precedence (User Mandate)
        # Precedence: EXCEPTION_FOUND > INSUFFICIENT_INFORMATION > PARTIALLY_EVALUATED > COMPLIANT
        if exceptions_found:
            final_status = "EXCEPTION_FOUND"
        elif insufficient_info:
            final_status = "INSUFFICIENT_INFORMATION"
        elif partially_evaluated:
            final_status = "PARTIALLY_EVALUATED"
        else:
            final_status = "COMPLIANT"

        # 7. Create ReconciliationRun record
        run = ReconciliationRun(
            institution_id=candidate.institution_id,
            programme_id=candidate.programme_id,
            academic_year=candidate.academic_year,
            candidate_snapshot_id=candidate.id,
            candidate_snapshot_hash=candidate.snapshot_hash,
            baseline_snapshot_id=req.baseline_snapshot_id,
            run_type="INTAKE_VERIFICATION",
            execution_status="COMPLETED",
            engine_version=ENGINE_VERSION,
            rules_version=RULES_VERSION,
            result_fingerprint=uuid.uuid4().hex,
            summary_counts={
                "COMPLIANCE_STATUS": final_status,
                "REGULAR_ENROLLED": total_regular_enrolled,
                "REGULAR_APPROVED": regular_approved,
                "REGULAR_VARIANCE": regular_variance,
                "SUPERNUMERARY_TOTAL": total_supernumerary,
                "LATERAL_ENTRY_TOTAL": observed_lateral,
                "UNCLASSIFIED_TOTAL": len(unclassified_students),
                "CASES_CREATED": len(discrepancy_cases_to_create),
            },
            parameters_json=req.parameters or {},
            idempotency_key=idempotency_key,
            initiated_by_user_id=actor.id,
            created_at=now_utc,
        )
        db.add(run)
        db.flush()

        # 8. Create Programme-Level Discrepancy Cases (Decision 1)
        created_case_dicts = []
        for case_info in discrepancy_cases_to_create:
            case_num = f"CASE-{candidate.academic_year[:4]}-INTAKE-{uuid.uuid4().hex[:8].upper()}"
            d_case = DiscrepancyCase(
                case_number=case_num,
                scope_type="PROGRAMME",
                institution_id=candidate.institution_id,
                programme_id=candidate.programme_id,
                academic_year=candidate.academic_year,
                student_identity_id=None,  # Nullable for collective programme-level findings
                observed_count=case_info.get("observed_count"),
                approved_limit=case_info.get("approved_limit"),
                excess_count=case_info.get("excess_count"),
                approval_configuration_id=approval_config.id,
                approval_configuration_version=approval_config.configuration_version,
                source_submission_id=candidate.source_submission_id,
                evidence_context_json=case_info.get("evidence", {}),
                initial_reconciliation_run_id=run.id,
                latest_reconciliation_run_id=run.id,
                classification=case_info["classification"],
                review_priority=case_info["priority"],
                case_status="OPEN",
                occurrence_count=1,
                created_at=now_utc,
            )
            db.add(d_case)
            db.flush()
            created_case_dicts.append({
                "case_id": str(d_case.id),
                "case_number": d_case.case_number,
                "classification": d_case.classification,
                "review_priority": d_case.review_priority,
                "scope_type": d_case.scope_type,
            })

        # 9. Persist IntakeReconciliationSummary
        summary_record = IntakeReconciliationSummary(
            reconciliation_run_id=run.id,
            approval_configuration_id=approval_config.id,
            approval_configuration_version=approval_config.configuration_version,
            compliance_status=final_status,
            regular_approved_intake=regular_approved,
            regular_enrolled_count=total_regular_enrolled,
            regular_variance=regular_variance,
            supernumerary_total_cap=supernumerary_total_cap,
            supernumerary_enrolled_count=total_supernumerary,
            supernumerary_variance=total_supernumerary - supernumerary_total_cap,
            lateral_entry_approved_cap=lateral_entry_cap,
            lateral_entry_enrolled_count=observed_lateral,
            lateral_entry_variance=lateral_variance,
            category_breakdown_json={
                "categories": [c.model_dump() for c in category_compliance_list],
                "unclassified_count": len(unclassified_students),
            },
            created_at=now_utc,
        )
        db.add(summary_record)
        db.flush()

        # 10. Chained Audit Event
        SnapshotService.record_chained_audit_event(
            db=db,
            actor_id=actor.id,
            action="INTAKE_RECONCILIATION_EXECUTED",
            entity_type="IntakeReconciliationSummary",
            entity_id=summary_record.id,
            metadata_payload={
                "reconciliation_run_id": str(run.id),
                "candidate_snapshot_id": str(candidate.id),
                "compliance_status": final_status,
                "regular_variance": regular_variance,
                "cases_created": len(created_case_dicts),
            },
        )

        db.commit()

        return IntakeReconciliationSummaryResponse(
            id=summary_record.id,
            reconciliation_run_id=run.id,
            approval_configuration_id=approval_config.id,
            approval_configuration_version=approval_config.configuration_version,
            compliance_status=final_status,
            regular_approved_intake=regular_approved,
            regular_enrolled_count=total_regular_enrolled,
            regular_variance=regular_variance,
            supernumerary_total_cap=supernumerary_total_cap,
            supernumerary_enrolled_count=total_supernumerary,
            supernumerary_variance=total_supernumerary - supernumerary_total_cap,
            lateral_entry_approved_cap=lateral_entry_cap,
            lateral_entry_enrolled_count=observed_lateral,
            lateral_entry_variance=lateral_variance,
            unclassified_count=len(unclassified_students),
            category_breakdown=category_compliance_list,
            category_breakdown_json=summary_record.category_breakdown_json,
            discrepancy_cases_created=created_case_dicts,
            created_at=summary_record.created_at,
        )

    @classmethod
    def _handle_missing_approval_configuration(
        cls,
        db: Session,
        candidate: RosterSnapshot,
        observations: List[AnnualRosterObservation],
        actor: User,
        now_utc: datetime,
        idempotency_key: Optional[str] = None,
    ) -> IntakeReconciliationSummaryResponse:
        """
        Gracefully handles Scenario 7: When no active statutory approval configuration exists.
        Evaluates strictly as INSUFFICIENT_INFORMATION. Never presumes zero-intake statutory fraud.
        """
        observed_count = len(observations)

        run = ReconciliationRun(
            institution_id=candidate.institution_id,
            programme_id=candidate.programme_id,
            academic_year=candidate.academic_year,
            candidate_snapshot_id=candidate.id,
            candidate_snapshot_hash=candidate.snapshot_hash,
            baseline_snapshot_id=None,
            run_type="INTAKE_VERIFICATION",
            execution_status="COMPLETED",
            engine_version=ENGINE_VERSION,
            rules_version=RULES_VERSION,
            result_fingerprint=uuid.uuid4().hex,
            summary_counts={
                "COMPLIANCE_STATUS": "INSUFFICIENT_INFORMATION",
                "REASON": "MISSING_APPROVAL_CONFIGURATION",
                "OBSERVED_COUNT": observed_count,
            },
            parameters_json={},
            idempotency_key=idempotency_key,
            initiated_by_user_id=actor.id,
            created_at=now_utc,
        )
        db.add(run)
        db.flush()

        case_num = f"CASE-{candidate.academic_year[:4]}-NO-CONFIG-{uuid.uuid4().hex[:8].upper()}"
        d_case = DiscrepancyCase(
            case_number=case_num,
            scope_type="PROGRAMME",
            institution_id=candidate.institution_id,
            programme_id=candidate.programme_id,
            academic_year=candidate.academic_year,
            student_identity_id=None,
            observed_count=observed_count,
            approved_limit=None,
            excess_count=None,
            approval_configuration_id=None,
            approval_configuration_version=None,
            source_submission_id=candidate.source_submission_id,
            evidence_context_json={
                "notes": "Official regulatory approval letter (AICTE EoA) not registered for this academic year.",
                "candidate_snapshot_id": str(candidate.id),
            },
            initial_reconciliation_run_id=run.id,
            latest_reconciliation_run_id=run.id,
            classification="MISSING_APPROVAL_CONFIGURATION",
            review_priority="LOW",
            case_status="OPEN",
            occurrence_count=1,
            created_at=now_utc,
        )
        db.add(d_case)
        db.flush()

        summary = IntakeReconciliationSummary(
            reconciliation_run_id=run.id,
            approval_configuration_id=None,
            approval_configuration_version=None,
            compliance_status="INSUFFICIENT_INFORMATION",
            regular_approved_intake=0,
            regular_enrolled_count=observed_count,
            regular_variance=observed_count,
            supernumerary_total_cap=0,
            supernumerary_enrolled_count=0,
            supernumerary_variance=0,
            lateral_entry_approved_cap=None,
            lateral_entry_enrolled_count=0,
            lateral_entry_variance=None,
            category_breakdown_json={
                "notes": "Statutory approval configuration missing. Cannot compute category limits.",
            },
            created_at=now_utc,
        )
        db.add(summary)
        db.flush()

        SnapshotService.record_chained_audit_event(
            db=db,
            actor_id=actor.id,
            action="INTAKE_RECONCILIATION_EXECUTED",
            entity_type="IntakeReconciliationSummary",
            entity_id=summary.id,
            metadata_payload={
                "reconciliation_run_id": str(run.id),
                "compliance_status": "INSUFFICIENT_INFORMATION",
                "reason": "MISSING_APPROVAL_CONFIGURATION",
            },
        )

        db.commit()

        return IntakeReconciliationSummaryResponse(
            id=summary.id,
            reconciliation_run_id=run.id,
            approval_configuration_id=None,
            approval_configuration_version=None,
            compliance_status="INSUFFICIENT_INFORMATION",
            regular_approved_intake=0,
            regular_enrolled_count=observed_count,
            regular_variance=observed_count,
            supernumerary_total_cap=0,
            supernumerary_enrolled_count=0,
            supernumerary_variance=0,
            lateral_entry_approved_cap=None,
            lateral_entry_enrolled_count=0,
            lateral_entry_variance=None,
            unclassified_count=observed_count,
            category_breakdown=[
                CategoryComplianceResult(
                    category_code="REGULATORY_APPROVAL",
                    entry_level="ALL",
                    allocation_type="SANCTIONED_INTAKE",
                    approved_limit=None,
                    observed_count=observed_count,
                    variance=None,
                    status="INSUFFICIENT_INFORMATION",
                    notes="Statutory approval configuration missing. Please register official AICTE EoA letter.",
                )
            ],
            category_breakdown_json=summary.category_breakdown_json,
            discrepancy_cases_created=[{
                "case_id": str(d_case.id),
                "case_number": d_case.case_number,
                "classification": d_case.classification,
                "review_priority": d_case.review_priority,
                "scope_type": d_case.scope_type,
            }],
            created_at=summary.created_at,
        )
